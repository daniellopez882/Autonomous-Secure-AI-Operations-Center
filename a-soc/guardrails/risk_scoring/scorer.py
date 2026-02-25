from typing import Dict, Any
from enum import Enum

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RiskScorer:
    """
    Calculate risk scores for security actions based on multiple factors.
    """
    
    @staticmethod
    def score_action(action_type: str, context: Dict[str, Any]) -> float:
        """
        Calculate risk score (0.0 - 1.0) for a given action.
        
        Args:
            action_type: Type of action (IAM_REVOKE, K8S_ISOLATE, etc.)
            context: Additional context (affected resources, user, etc.)
            
        Returns:
            float: Risk score between 0.0 and 1.0
        """
        base_scores = {
            "IAM_REVOKE": 0.8,
            "IAM_CREATE": 0.6,
            "K8S_ISOLATE": 0.7,
            "K8S_TERMINATE": 0.9,
            "NETWORK_BLOCK": 0.5,
            "LOG_QUERY": 0.1,
            "ALERT_CREATE": 0.2,
        }
        
        base_score = base_scores.get(action_type, 0.5)
        
        # Adjust based on context
        if context.get("production_environment"):
            base_score += 0.1
        
        if context.get("affects_multiple_resources"):
            base_score += 0.15
        
        if context.get("irreversible"):
            base_score += 0.2
        
        # Cap at 1.0
        return min(base_score, 1.0)
    
    @staticmethod
    def get_risk_level(score: float) -> RiskLevel:
        """Convert numeric score to risk level."""
        if score < 0.3:
            return RiskLevel.LOW
        elif score < 0.6:
            return RiskLevel.MEDIUM
        elif score < 0.8:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL
    
    @staticmethod
    def requires_approval(score: float) -> bool:
        """Determine if action requires human approval."""
        return score >= 0.5
