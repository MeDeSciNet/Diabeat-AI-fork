"""Four-stage swallow detection pipeline."""

from .base import DERIVED_FS, Candidate, Derived, DetectedEvent, SwallowDetector
from .rule_based import DETECTOR_VERSION, RuleBasedDetector, build_detector

__all__ = [
    "DERIVED_FS",
    "DETECTOR_VERSION",
    "Candidate",
    "Derived",
    "DetectedEvent",
    "RuleBasedDetector",
    "SwallowDetector",
    "build_detector",
]
