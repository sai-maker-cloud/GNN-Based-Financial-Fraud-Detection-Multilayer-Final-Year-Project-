"""
Database Persistence & Audit Logging Layer.
Provides asynchronous, non-blocking storage of scan history, fraud records,
and persistent device & system-wide hard blocklists.
Uses built-in SQLite (data/fraud_audit.db) for zero-setup local dev, 
ready for PostgreSQL in production.
"""

import os
import re
import sqlite3
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from typing import List, Dict, Any

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(ROOT_DIR, "data")
DB_PATH = os.path.join(DB_DIR, "fraud_audit.db")


class AuditDatabase:
    """Manages scan audit logs and confirmed fraud registries."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_tables()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

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
            conn.commit()

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
        summary_reason: str
    ):
        """Asynchronously called in background without blocking user response."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO scan_audit_logs (
                        user_id, device_fingerprint, raw_qr, target_entity,
                        payload_type, risk_score, decision, action, summary_reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, device_fingerprint, raw_qr, target_entity,
                    payload_type, risk_score, decision, action, summary_reason
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
