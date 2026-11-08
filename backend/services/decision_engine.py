"""
Decision Engine applying mathematically calibrated thresholds.
Threshold T1 = 0.40 (Safe boundary)
Threshold T2 = 0.74 (Fraud boundary proven at 86.15% Precision and 96.68% ROC-AUC)
"""

from backend.schemas import DecisionType, ClientAction


class DecisionEngine:
    """Classifies continuous risk probabilities into tri-state client actions."""

    T1_SAFE_THRESHOLD = 0.40
    T2_FRAUD_THRESHOLD = 0.74

    @classmethod
    def evaluate(cls, risk_score: float) -> tuple[DecisionType, ClientAction]:
        """
        Maps a continuous risk score to a tri-state Decision and Client Action.
        """
        score = float(risk_score)

        if score >= cls.T2_FRAUD_THRESHOLD:
            return DecisionType.FRAUD, ClientAction.HARD_BLOCK_PAYMENT
        elif score >= cls.T1_SAFE_THRESHOLD:
            return DecisionType.SUSPICIOUS, ClientAction.SHOW_WARNING_MODAL
        else:
            return DecisionType.SAFE, ClientAction.AUTO_REDIRECT_PAYMENT
