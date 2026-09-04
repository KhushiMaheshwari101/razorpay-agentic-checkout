"""
Risk Vector – calculates a multi-dimensional threat score for agent actions 
based on spend magnitude, volatility, frequency, and historical anomaly indicators.
"""

from typing import Dict, Any

class RiskVectorEngine:
    def __init__(self, high_spend_threshold: float = 10000.0):
        self.high_spend_threshold = high_spend_threshold

    def compute_risk(self, cart_total: float, intent_spend: float, discrepancies_count: int, loop_detected: bool) -> Dict[str, Any]:
        """
        Evaluates risk dimensions and returns a composite risk score (0.0 to 100.0) 
        along with a risk classification tier.
        """
        score = 0.0
        factors = []

        # Factor 1: Spend magnitude risk
        if cart_total >= self.high_spend_threshold:
            score += 30.0
            factors.append("High monetary transaction value.")

        # Factor 2: Intent vs Actual Spend divergence
        if intent_spend > 0 and (cart_total / intent_spend) > 1.5:
            score += 25.0
            factors.append("Significant divergence between stated intent spend and cart total.")

        # Factor 3: Grounding discrepancies/hallucinations detected
        if discrepancies_count > 0:
            score += float(min(40.0, discrepancies_count * 20.0))
            factors.append(f"Detected {discrepancies_count} catalog/pricing discrepancy anomalies.")

        # Factor 4: Loop detection trigger
        if loop_detected:
            score += 35.0
            factors.append("Agent recursion loop or stasis detected.")

        # Cap score at 100.0
        final_score = min(100.0, score)

        # Classify risk tier
        if final_score >= 70.0:
            tier = "CRITICAL"
        elif final_score >= 40.0:
            tier = "HIGH"
        elif final_score >= 20.0:
            tier = "MEDIUM"
        else:
            tier = "LOW"

        return {
            "risk_score": final_score,
            "risk_tier": tier,
            "risk_factors": factors
        }


if __name__ == "__main__":
    engine = RiskVectorEngine()
    print("--- Testing Risk Vector Engine ---")
    assessment = engine.compute_risk(cart_total=12000.0, intent_spend=5000.0, discrepancies_count=1, loop_detected=False)
    print(assessment)