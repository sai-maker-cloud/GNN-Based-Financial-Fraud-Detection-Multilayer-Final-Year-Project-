"""
Threat Intelligence Service for PhishTank & OpenPhish.
Provides real-time blacklist lookups and in-memory caching for known active scam domains.
"""

import os
import re
import time
from urllib.parse import urlparse
import urllib.request
import json

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE_DIR = os.path.join(ROOT_DIR, "data", "threat_intel")
CACHE_FILE = os.path.join(CACHE_DIR, "threat_blacklist.json")

# Authoritative trusted domains that must NEVER be blacklisted
TRUSTED_EXEMPT_DOMAINS = {
    "google.com", "google.co.in", "youtube.com", "youtu.be", "gmail.com", "android.com",
    "gstatic.com", "googleapis.com", "googlevideo.com", "ytimg.com",
    "microsoft.com", "github.com", "github.io", "apple.com", "wikipedia.org", "wikimedia.org",
    "cloudflare.com", "linkedin.com", "twitter.com", "x.com", "reddit.com", "stackoverflow.com",
    "amazon.com", "amazon.in",
    "onlinesbi.sbi", "sbi.co.in", "hdfcbank.com", "icicibank.com", "axisbank.com", "kotak.com",
    "paytm.com", "phonepe.com", "bhimupi.org.in", "npci.org.in", "rbi.org.in", "cred.club"
}

# Seed list of known high-risk phishing domains and patterns (curated from PhishTank & OpenPhish)
SEED_BLACKLIST = {
    # Impersonation & Quishing Phishing Domains
    "sbi-kyc-verification.portal-update.xyz",
    "paytmm-service-reward.xyz",
    "phonepe-cashback-claim.site",
    "electricity-bill-discount.top",
    "bescom-bill-pay-update.ru",
    "gpay-refund-support.in.net",
    "apple-id-verify-customer.eu-id3.net",
    "drive-google-com.fanalav.com",
    "secure-banking-update.servehttp.com",
    "paypal-resolution-center-update.biz",
    "login-westpac-au.icomtec.com.my",
    "itunes-login-connect.hippapi.org",
    "skat-dk-personlige.pepespizza.com",
    "creditmaster-update.eu",
    "free-mobile-recharge-bonus.tk"
}


class ThreatIntelligenceService:
    """
    Threat Intelligence Service querying OpenPhish, PhishTank, and local reputation feeds.
    Provides sub-millisecond in-memory lookups.
    """

    def __init__(self, auto_sync: bool = False):
        os.makedirs(CACHE_DIR, exist_ok=True)
        self.blacklisted_urls = set()
        self.blacklisted_domains = set(SEED_BLACKLIST)
        self.last_sync_time = 0
        self.load_local_cache()
        if not self.blacklisted_urls:
            self.load_phishtank_database()
            self.save_local_cache()

        if auto_sync:
            self.sync_openphish_feed()

    def load_phishtank_database(self, max_entries: int = 50000):
        """
        Loads verified community phishing URLs and domains from PhishTank database
        located in data/raw/phishing_urls.csv into memory for O(1) instant lookup.
        """
        phishtank_csv = os.path.join(ROOT_DIR, "data", "raw", "phishing_urls.csv")
        if os.path.exists(phishtank_csv):
            try:
                import pandas as pd
                df = pd.read_csv(phishtank_csv, usecols=["url"], nrows=max_entries)
                for u in df["url"].dropna():
                    u_clean = str(u).strip().lower()
                    domain = self.normalize_domain(u_clean)
                    if domain:
                        # Exclude authoritative trusted domains from being poisoned into the blacklist
                        if not any(domain == td or domain.endswith("." + td) for td in TRUSTED_EXEMPT_DOMAINS):
                            self.blacklisted_urls.add(u_clean)
                            self.blacklisted_domains.add(domain)
                print(f"[ThreatIntel] Loaded {len(self.blacklisted_urls):,} verified PhishTank entries into fast RAM cache.")
            except Exception as e:
                print(f"[ThreatIntel] Note: Could not load PhishTank CSV: {e}")

    def normalize_domain(self, url: str) -> str:
        """Extracts and normalizes the host domain from a URL."""
        clean = url.strip()
        if not clean.startswith(("http://", "https://")):
            clean = "http://" + clean
        parsed = urlparse(clean)
        return parsed.netloc.lower().split(":")[0]

    def load_local_cache(self):
        """Loads cached threat blacklist from disk if available."""
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.blacklisted_domains.update(data.get("domains", []))
                    self.blacklisted_urls.update(data.get("urls", []))
                    self.last_sync_time = data.get("last_sync", 0)
            except Exception as e:
                print(f"[Warning] Could not read threat cache: {e}")

    def save_local_cache(self):
        """Persists threat blacklist to disk."""
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "domains": list(self.blacklisted_domains),
                    "urls": list(self.blacklisted_urls),
                    "last_sync": self.last_sync_time,
                    "count": len(self.blacklisted_domains) + len(self.blacklisted_urls)
                }, f, indent=2)
        except Exception as e:
            print(f"[Warning] Could not save threat cache: {e}")

    def sync_openphish_feed(self, timeout_sec: int = 5) -> int:
        """
        Pulls active community phishing feeds from OpenPhish public repository.
        Falls back smoothly if offline.
        """
        openphish_url = "https://openphish.com/feed.txt"
        print("[ThreatIntel] Syncing live OpenPhish feed...")
        try:
            req = urllib.request.Request(
                openphish_url,
                headers={"User-Agent": "SecurityGatekeeper/1.0 (Threat-Checker)"}
            )
            with urllib.request.urlopen(req, timeout=timeout_sec) as response:
                content = response.read().decode("utf-8", errors="ignore")
                new_urls = [line.strip() for line in content.splitlines() if line.strip()]
                for u in new_urls:
                    self.blacklisted_urls.add(u.lower())
                    domain = self.normalize_domain(u)
                    if domain:
                        self.blacklisted_domains.add(domain)

                self.last_sync_time = time.time()
                self.save_local_cache()
                print(f"[ThreatIntel] Successfully synced {len(new_urls):,} active phishing URLs from OpenPhish.")
                return len(new_urls)
        except Exception as e:
            print(f"[ThreatIntel] Live sync unavailable ({e}). Using cached threat database.")
            return 0

    def check_url(self, url: str) -> dict:
        """
        Evaluates a URL against PhishTank, OpenPhish, and local blacklist feeds.
        Returns:
            dict with { 'is_blacklisted': bool, 'threat_score': float, 'source': str }
        """
        clean_url = url.strip().lower()
        domain = self.normalize_domain(clean_url)

        # Exemption check: Authoritative global domains are never treated as threat intel matches
        if any(domain == td or domain.endswith("." + td) for td in TRUSTED_EXEMPT_DOMAINS):
            return {
                "is_blacklisted": False,
                "threat_score": 0.0,
                "source": "Authoritative Registry",
                "matched_entry": domain
            }

        # Check exact full URL
        if clean_url in self.blacklisted_urls:
            return {
                "is_blacklisted": True,
                "threat_score": 1.0,
                "source": "OpenPhish / PhishTank Feed",
                "matched_entry": clean_url
            }

        # Check domain or parent domain
        if domain in self.blacklisted_domains:
            return {
                "is_blacklisted": True,
                "threat_score": 1.0,
                "source": "Threat Intelligence Blacklist",
                "matched_entry": domain
            }

        # Subdomain match (e.g. *.xyz matching high-risk parent)
        domain_parts = domain.split(".")
        if len(domain_parts) > 2:
            parent_domain = ".".join(domain_parts[-2:])
            if parent_domain in self.blacklisted_domains:
                return {
                    "is_blacklisted": True,
                    "threat_score": 0.95,
                    "source": "Parent Domain Blacklist",
                    "matched_entry": parent_domain
                }

        return {
            "is_blacklisted": False,
            "threat_score": 0.0,
            "source": "Clean",
            "matched_entry": None
        }

    def calculate_threat_risk(self, url: str) -> float:
        """Convenience method returning float threat risk score in [0.0, 1.0]."""
        result = self.check_url(url)
        return float(result["threat_score"])
