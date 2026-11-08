"""
URL Feature Extractor for Quishing & Phishing Detection.
Extracts fast lexical, structural, statistical, and domain-level indicators in < 1ms.
"""

import math
import re
from urllib.parse import urlparse
import numpy as np

# Top abused TLDs commonly seen in phishing and QR scam campaigns
SUSPICIOUS_TLDS = {
    "xyz", "top", "ru", "work", "club", "biz", "cn", "vn", "cc", "tk", "ml", "ga", "cf", "gq", "info", "loan", "site", "online"
}

# Sensitive tokens commonly targeted in phishing credential theft
SENSITIVE_KEYWORDS = [
    "login", "verify", "update", "bank", "account", "secure", "webscr", 
    "confirm", "password", "credential", "otp", "wallet", "kyc", "refund", 
    "support", "service", "billing", "signin", "admin", "invoice"
]

# Major brands frequently impersonated in payment and quishing fraud
TARGET_BRANDS = [
    "paypal", "apple", "google", "paytm", "sbi", "hdfc", "icici", 
    "phonepe", "amazon", "microsoft", "netflix", "facebook"
]

# IPv4 regex pattern
IPV4_PATTERN = re.compile(r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$")


def calculate_shannon_entropy(text: str) -> float:
    """Calculates the Shannon character entropy to detect algorithmic randomness."""
    if not text:
        return 0.0
    entropy = 0.0
    text_len = len(text)
    char_counts = {}
    for char in text:
        char_counts[char] = char_counts.get(char, 0) + 1
    for count in char_counts.values():
        p = count / text_len
        entropy -= p * math.log2(p)
    return float(entropy)


def extract_url_features(url_str: str) -> dict:
    """
    Extracts 17 distinct numerical/categorical features from a single raw URL string.
    Returns a dictionary of feature names mapped to numerical values.
    """
    url_clean = str(url_str).strip()
    if not url_clean.startswith(("http://", "https://")):
        url_clean = "http://" + url_clean

    parsed = urlparse(url_clean)
    domain = parsed.netloc.lower().split(":")[0]  # strip port if present
    path = parsed.path.lower()
    full_url = url_clean.lower()

    # Extract TLD
    domain_parts = domain.split(".")
    tld = domain_parts[-1] if len(domain_parts) > 1 else ""

    # Feature Computations
    url_len = len(full_url)
    domain_len = len(domain)
    path_len = len(path)

    count_dots = full_url.count(".")
    count_hyphens = full_url.count("-")
    count_at = 1 if "@" in full_url else 0
    count_question = full_url.count("?")
    count_equal = full_url.count("=")
    count_slash = full_url.count("/")
    count_subdomains = max(0, len(domain_parts) - 2)

    digits = sum(c.isdigit() for c in full_url)
    digit_ratio = (digits / url_len) if url_len > 0 else 0.0

    is_https = 1 if parsed.scheme.lower() == "https" else 0
    has_ip = 1 if IPV4_PATTERN.match(domain) else 0
    is_suspicious_tld = 1 if tld in SUSPICIOUS_TLDS else 0

    entropy = calculate_shannon_entropy(domain)

    # Keyword presence
    has_sensitive_keyword = 1 if any(kw in full_url for kw in SENSITIVE_KEYWORDS) else 0

    # Brand typosquatting / presence
    has_brand = 1 if any(brand in full_url for brand in TARGET_BRANDS) else 0

    return {
        "url_length": float(url_len),
        "domain_length": float(domain_len),
        "path_length": float(path_len),
        "count_dots": float(count_dots),
        "count_hyphens": float(count_hyphens),
        "count_at": float(count_at),
        "count_question": float(count_question),
        "count_equal": float(count_equal),
        "count_slash": float(count_slash),
        "count_subdomains": float(count_subdomains),
        "count_digits": float(digits),
        "digit_ratio": float(digit_ratio),
        "is_https": float(is_https),
        "has_ip": float(has_ip),
        "is_suspicious_tld": float(is_suspicious_tld),
        "shannon_entropy": float(entropy),
        "has_sensitive_keyword": float(has_sensitive_keyword),
        "has_brand": float(has_brand),
    }


FEATURE_NAMES = [
    "url_length",
    "domain_length",
    "path_length",
    "count_dots",
    "count_hyphens",
    "count_at",
    "count_question",
    "count_equal",
    "count_slash",
    "count_subdomains",
    "count_digits",
    "digit_ratio",
    "is_https",
    "has_ip",
    "is_suspicious_tld",
    "shannon_entropy",
    "has_sensitive_keyword",
    "has_brand",
]


def extract_features_vector(url_str: str) -> np.ndarray:
    """Extracts features as a 1D NumPy array directly compatible with scikit-learn models."""
    feats = extract_url_features(url_str)
    return np.array([feats[col] for col in FEATURE_NAMES], dtype=np.float32)
