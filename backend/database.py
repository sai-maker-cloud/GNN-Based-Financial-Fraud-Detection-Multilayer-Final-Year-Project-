"""
Database Persistence & Audit Logging Layer.
Provides asynchronous, non-blocking storage of scan history, fraud records,
and persistent device & system-wide hard blocklists.
Uses built-in SQLite (data/fraud_audit.db) for zero-setup local dev, 
ready for PostgreSQL in production.
"""

import os
import re
import math
import sqlite3
from contextlib import contextmanager
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from typing import List, Dict, Any, Optional

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(ROOT_DIR, "data")
DB_PATH = os.path.join(DB_DIR, "fraud_audit.db")


class AuditDatabase:
    """Manages scan audit logs and confirmed fraud registries."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_tables()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def init_tables(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 1. Scan Audit Logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scan_audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    device_fingerprint TEXT,
                    raw_qr TEXT,
                    target_entity TEXT,
                    payload_type TEXT,
                    risk_score REAL,
                    decision TEXT,
                    action TEXT,
                    summary_reason TEXT,
                    latitude REAL,
                    longitude REAL,
                    geo_cell TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Backward-compatible schema migration for existing SQLite databases
            cursor.execute("PRAGMA table_info(scan_audit_logs)")
            existing_cols = {row[1] for row in cursor.fetchall()}
            for col_name, col_type in [("latitude", "REAL"), ("longitude", "REAL"), ("geo_cell", "TEXT")]:
                if col_name not in existing_cols:
                    cursor.execute(f"ALTER TABLE scan_audit_logs ADD COLUMN {col_name} {col_type}")

            # 2. Blocked Fraud Entities (Permanent Hard Blacklist)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blocked_entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_id TEXT UNIQUE,
                    entity_type TEXT,
                    risk_score REAL,
                    reason TEXT,
                    blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 3. Registered Merchant Store Counter Bindings (Anti-Sticker-Tampering Registry)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS registered_merchants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    shop_name TEXT NOT NULL,
                    official_vpa TEXT NOT NULL,
                    mcc TEXT,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    radius_m REAL DEFAULT 40.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(shop_name, official_vpa)
                );
            """)
            conn.commit()

    @staticmethod
    def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Great-circle distance in meters between two WGS84 coordinates."""
        r = 6371000.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
        return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))

    @staticmethod
    def _to_geo_cell(latitude: Optional[float], longitude: Optional[float]) -> Optional[str]:
        if latitude is None or longitude is None:
            return None
        return f"{round(float(latitude), 4):.4f},{round(float(longitude), 4):.4f}"

    def log_scan(
        self,
        user_id: str,
        device_fingerprint: str,
        raw_qr: str,
        target_entity: str,
        payload_type: str,
        risk_score: float,
        decision: str,
        action: str,
        summary_reason: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ):
        """Asynchronously called in background without blocking user response."""
        try:
            geo_cell = self._to_geo_cell(latitude, longitude)
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO scan_audit_logs (
                        user_id, device_fingerprint, raw_qr, target_entity,
                        payload_type, risk_score, decision, action, summary_reason,
                        latitude, longitude, geo_cell
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, device_fingerprint, raw_qr, target_entity,
                    payload_type, risk_score, decision, action, summary_reason,
                    latitude, longitude, geo_cell
                ))

                # If FRAUD / BLOCK, automatically record entity into permanent blacklist
                if decision in ["FRAUD", "BLOCK"]:
                    if target_entity:
                        cursor.execute("""
                            INSERT OR REPLACE INTO blocked_entities (
                                entity_id, entity_type, risk_score, reason, blocked_at
                            ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """, (target_entity.strip().lower(), payload_type, risk_score, summary_reason))
                    if raw_qr:
                        cursor.execute("""
                            INSERT OR REPLACE INTO blocked_entities (
                                entity_id, entity_type, risk_score, reason, blocked_at
                            ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """, (raw_qr.strip().lower(), payload_type, risk_score, summary_reason))

                conn.commit()
        except Exception as e:
            print(f"[Database Error] Could not write audit log: {e}")

    def register_merchant(
        self,
        shop_name: str,
        official_vpa: str,
        latitude: float,
        longitude: float,
        mcc: Optional[str] = None,
        radius_m: float = 40.0,
    ) -> Dict[str, Any]:
        """Registers an authentic merchant QR VPA to its physical store GPS coordinates."""
        clean_name = shop_name.strip()
        clean_vpa = official_vpa.strip().lower()
        clean_mcc = (mcc or "").strip() or None
        radius = max(10.0, min(float(radius_m), 500.0))

        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO registered_merchants (
                    shop_name, official_vpa, mcc, latitude, longitude, radius_m
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(shop_name, official_vpa) DO UPDATE SET
                    mcc = COALESCE(excluded.mcc, registered_merchants.mcc),
                    latitude = excluded.latitude,
                    longitude = excluded.longitude,
                    radius_m = excluded.radius_m
            """, (clean_name, clean_vpa, clean_mcc, float(latitude), float(longitude), radius))
            conn.commit()
            cursor.execute(
                "SELECT * FROM registered_merchants WHERE shop_name = ? AND official_vpa = ?",
                (clean_name, clean_vpa),
            )
            row = cursor.fetchone()
            return dict(row) if row else {
                "shop_name": clean_name,
                "official_vpa": clean_vpa,
                "mcc": clean_mcc,
                "latitude": float(latitude),
                "longitude": float(longitude),
                "radius_m": radius,
            }

    def get_merchants_near(
        self,
        latitude: Optional[float],
        longitude: Optional[float],
    ) -> List[Dict[str, Any]]:
        """Returns registered stores whose geo-fence covers the given coordinates."""
        if latitude is None or longitude is None:
            return []
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM registered_merchants")
                rows = cursor.fetchall()

            matches = []
            for r in rows:
                merchant = dict(r)
                dist = self._haversine_meters(
                    float(latitude), float(longitude),
                    float(merchant["latitude"]), float(merchant["longitude"])
                )
                fence = max(float(merchant.get("radius_m") or 40.0), 40.0)
                if dist <= fence:
                    merchant["distance_m"] = round(dist, 1)
                    matches.append(merchant)
            matches.sort(key=lambda m: m["distance_m"])
            return matches
        except Exception as e:
            print(f"[Database Error] get_merchants_near failed: {e}")
            return []

    def get_all_merchants(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Lists all registered store counter QR bindings."""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM registered_merchants ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                )
                return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            print(f"[Database Error] get_all_merchants failed: {e}")
            return []

    def delete_merchant(self, merchant_id: int) -> bool:
        """Removes a registered store counter binding by ID."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM registered_merchants WHERE id = ?", (int(merchant_id),))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"[Database Error] delete_merchant failed: {e}")
            return False

    def analyze_location_vpa_history(
        self,
        latitude: Optional[float],
        longitude: Optional[float],
        current_vpa: str,
    ) -> Dict[str, Any]:
        """
        Crowdsourced graph check: inspects safe historical UPI scans near these coordinates (~35m)
        to detect when an established counter QR suddenly switches to an unseen personal VPA.
        """
        if latitude is None or longitude is None or not current_vpa:
            return {"total_safe_scans": 0}
        clean_current = current_vpa.strip().lower()
        try:
            lat_f, lon_f = float(latitude), float(longitude)
            # ~0.00035 deg is roughly 35-38 meters
            delta = 0.00035
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT LOWER(target_entity), COUNT(*) as cnt
                    FROM scan_audit_logs
                    WHERE latitude BETWEEN ? AND ?
                      AND longitude BETWEEN ? AND ?
                      AND decision IN ('SAFE', 'ALLOW')
                      AND payload_type IN ('UPI', 'PAYMENT_URL')
                      AND target_entity LIKE '%@%'
                    GROUP BY LOWER(target_entity)
                    ORDER BY cnt DESC
                """, (lat_f - delta, lat_f + delta, lon_f - delta, lon_f + delta))
                rows = cursor.fetchall()

            if not rows:
                return {"total_safe_scans": 0}

            counts = {row[0]: int(row[1]) for row in rows if row[0]}
            total = sum(counts.values())
            dominant_vpa, dominant_count = rows[0][0], int(rows[0][1])
            return {
                "total_safe_scans": total,
                "dominant_vpa": dominant_vpa,
                "dominant_count": dominant_count,
                "dominant_share": round(dominant_count / max(total, 1), 4),
                "current_vpa_count": counts.get(clean_current, 0),
            }
        except Exception as e:
            print(f"[Database Error] analyze_location_vpa_history failed: {e}")
            return {"total_safe_scans": 0}

    def block_entity(self, entity_id: str, entity_type: str = "UNKNOWN", risk_score: float = 1.0, reason: str = ""):
        """Explicitly records an entity into the permanent system hard blocklist."""
        clean_id = entity_id.strip().lower()
        if not clean_id:
            return
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO blocked_entities (
                        entity_id, entity_type, risk_score, reason, blocked_at
                    ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (clean_id, entity_type, risk_score, reason))

                # If it's a URL, also extract domain and block the domain
                if clean_id.startswith(("http://", "https://")):
                    parsed = urlparse(clean_id)
                    domain = parsed.netloc.lower().split(":")[0]
                    if domain:
                        cursor.execute("""
                            INSERT OR REPLACE INTO blocked_entities (
                                entity_id, entity_type, risk_score, reason, blocked_at
                            ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """, (domain, "DOMAIN", risk_score, f"Host domain of blocked URL: {reason}"))

                    # If URL contains pa= (UPI VPA), also block VPA
                    query_dict = parse_qs(parsed.query)
                    if "pa" in query_dict:
                        vpa = query_dict["pa"][0].strip().lower()
                        if vpa:
                            cursor.execute("""
                                INSERT OR REPLACE INTO blocked_entities (
                                    entity_id, entity_type, risk_score, reason, blocked_at
                                ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                            """, (vpa, "UPI", risk_score, f"Payee in blocked payment URL: {reason}"))

                # If it's a UPI string, also block VPA
                elif clean_id.startswith("upi://"):
                    parsed = urlparse(clean_id)
                    query_dict = parse_qs(parsed.query)
                    if "pa" in query_dict:
                        vpa = query_dict["pa"][0].strip().lower()
                        if vpa:
                            cursor.execute("""
                                INSERT OR REPLACE INTO blocked_entities (
                                    entity_id, entity_type, risk_score, reason, blocked_at
                                ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                            """, (vpa, "UPI", risk_score, reason))

                conn.commit()
        except Exception as e:
            print(f"[Database Error] block_entity failed: {e}")

    def is_entity_blocked(self, entity_or_url: str) -> bool:
        """
        Fast lookup: Checks if an exact string, domain, or payee VPA is in the permanent hard blacklist.
        Returns True if strictly blocked.
        """
        if not entity_or_url:
            return False
        clean = entity_or_url.strip().lower()

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # 1. Exact match
                cursor.execute("SELECT 1 FROM blocked_entities WHERE entity_id = ? LIMIT 1", (clean,))
                if cursor.fetchone():
                    return True

                # 2. Domain check if URL
                if clean.startswith(("http://", "https://")) or ("." in clean and not "@" in clean):
                    parsed = urlparse(clean if clean.startswith("http") else f"https://{clean}")
                    domain = parsed.netloc.lower().split(":")[0]
                    if domain:
                        cursor.execute("SELECT 1 FROM blocked_entities WHERE entity_id = ? LIMIT 1", (domain,))
                        if cursor.fetchone():
                            return True

                    # 3. Payee VPA check inside URL
                    query_dict = parse_qs(parsed.query)
                    if "pa" in query_dict:
                        vpa = query_dict["pa"][0].strip().lower()
                        cursor.execute("SELECT 1 FROM blocked_entities WHERE entity_id = ? LIMIT 1", (vpa,))
                        if cursor.fetchone():
                            return True

                # 4. Payee check if UPI
                elif clean.startswith("upi://"):
                    parsed = urlparse(clean)
                    query_dict = parse_qs(parsed.query)
                    if "pa" in query_dict:
                        vpa = query_dict["pa"][0].strip().lower()
                        cursor.execute("SELECT 1 FROM blocked_entities WHERE entity_id = ? LIMIT 1", (vpa,))
                        if cursor.fetchone():
                            return True

                # 5. Direct VPA
                elif "@" in clean:
                    cursor.execute("SELECT 1 FROM blocked_entities WHERE entity_id = ? LIMIT 1", (clean,))
                    if cursor.fetchone():
                        return True

        except Exception as e:
            print(f"[Database Error] is_entity_blocked check: {e}")
        return False

    def get_recent_scans(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves recent audit logs for administrative inspection."""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM scan_audit_logs ORDER BY created_at DESC LIMIT ?
                """, (limit,))
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            print(f"[Database Error] Could not fetch logs: {e}")
            return []

    def get_blocked_entities(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves list of permanently blocked fraud entities."""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM blocked_entities ORDER BY blocked_at DESC LIMIT ?
                """, (limit,))
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            print(f"[Database Error] Could not fetch blocked entities: {e}")
            return []


# Global database singleton
db = AuditDatabase()
