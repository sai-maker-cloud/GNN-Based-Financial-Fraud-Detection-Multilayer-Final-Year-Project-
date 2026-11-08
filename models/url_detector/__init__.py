"""
URL Detector Package for Phishing and Quishing Prevention.
"""

from models.url_detector.feature_extractor import (
    extract_url_features,
    extract_features_vector,
    calculate_shannon_entropy,
    FEATURE_NAMES,
)
from models.url_detector.threat_intelligence import ThreatIntelligenceService

__all__ = [
    "extract_url_features",
    "extract_features_vector",
    "calculate_shannon_entropy",
    "FEATURE_NAMES",
    "ThreatIntelligenceService",
]
