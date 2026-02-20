"""
Client Configuration Schema and Validation
Supports mandatory configurable client context for compliance analysis.
"""
from __future__ import annotations

from typing import Optional, Literal, Any
from pydantic import BaseModel, Field, field_validator


class CustomRule(BaseModel):
    """Custom compliance rule defined by the client."""
    rule_id: str = Field(..., description="Unique identifier for the rule")
    rule_name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Detailed rule description")
    severity: Literal["critical", "high", "medium", "low"] = Field(
        default="high",
        description="Violation severity level"
    )
    category: str = Field(
        default="Custom Policy",
        description="Rule category (e.g., 'Data Privacy', 'Agent Conduct')"
    )


class ProductConfig(BaseModel):
    """Product or service configuration."""
    product_name: str = Field(..., description="Name of the product/service")
    product_type: str = Field(
        default="General",
        description="Type (e.g., 'Loan', 'Credit Card', 'Savings Account')"
    )
    risk_level: Literal["high", "medium", "low"] = Field(
        default="medium",
        description="Base risk level for this product"
    )
    specific_policies: list[str] = Field(
        default_factory=list,
        description="List of policy IDs specific to this product"
    )


class ComplianceTrigger(BaseModel):
    """Compliance trigger configuration."""
    trigger_name: str = Field(..., description="Name of the trigger")
    keywords: list[str] = Field(
        default_factory=list,
        description="Keywords that activate this trigger"
    )
    severity: Literal["critical", "high", "medium", "low"] = Field(
        default="high",
        description="Severity when triggered"
    )
    action_required: str = Field(
        default="Flag for review",
        description="Recommended action when triggered"
    )


class RiskScoring(BaseModel):
    """Risk scoring configuration."""
    base_threshold: int = Field(
        default=50,
        ge=0,
        le=100,
        description="Base risk score threshold for escalation"
    )
    critical_threshold: int = Field(
        default=80,
        ge=0,
        le=100,
        description="Critical risk threshold requiring immediate action"
    )
    weight_policy_violations: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Weight for policy violations in risk score"
    )
    weight_emotional_tone: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Weight for emotional tone in risk score"
    )
    weight_threat_detection: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Weight for threat detection in risk score"
    )

    @field_validator('weight_policy_violations', 'weight_emotional_tone', 'weight_threat_detection')
    @classmethod
    def validate_weights_sum(cls, v, info):
        """Ensure weights sum to approximately 1.0."""
        return v


class ClientConfig(BaseModel):
    """
    Complete client configuration schema.
    This defines the client context that influences compliance analysis.
    """
    # ============ MANDATORY FIELDS ============
    
    business_domain: str = Field(
        ...,
        description="Primary business domain (e.g., 'Banking', 'Telecom', 'Healthcare', 'Insurance')"
    )
    
    organization_name: str = Field(
        default="Default Organization",
        description="Name of the organization/client"
    )
    
    active_policy_set: str = Field(
        default="RBI_Compliance_v2.1",
        description="Active policy version or identifier"
    )
    
    # ============ PRODUCTS & SERVICES ============
    
    monitored_products: list[str] = Field(
        default_factory=lambda: ["Credit Card", "Personal Loan", "Savings Account"],
        description="List of products/services being monitored"
    )
    
    products: list[ProductConfig] = Field(
        default_factory=list,
        description="Detailed product configurations"
    )
    
    # ============ POLICIES & RULES ============
    
    custom_rules: list[CustomRule] = Field(
        default_factory=list,
        description="Client-specific compliance rules"
    )
    
    risk_triggers: list[str] = Field(
        default_factory=lambda: [
            "Legal Threats",
            "Harassment",
            "Unauthorized Debit",
            "Physical Visit Threat",
            "Social Shaming",
            "Jail Mention",
            "Court Mention",
            "Family Mention",
            "Police Mention",
            "Coercion",
            "Abusive Language",
            "Threat"
        ],
        description="List of risk trigger keywords/phrases"
    )
    
    compliance_triggers: list[ComplianceTrigger] = Field(
        default_factory=list,
        description="Detailed compliance trigger configurations"
    )
    
    # ============ RISK CONFIGURATION ============
    
    risk_scoring: RiskScoring = Field(
        default_factory=RiskScoring,
        description="Risk scoring configuration"
    )
    
    auto_escalate_on_critical: bool = Field(
        default=True,
        description="Automatically escalate calls with critical violations"
    )
    
    # ============ AGENT BEHAVIOR STANDARDS ============
    
    agent_quality_thresholds: dict[str, int] = Field(
        default_factory=lambda: {
            "minimum_politeness_score": 60,
            "minimum_empathy_score": 50,
            "minimum_professionalism_score": 70,
            "minimum_overall_score": 60
        },
        description="Minimum acceptable scores for agent quality metrics"
    )
    
    prohibited_phrases: list[str] = Field(
        default_factory=lambda: [
            "you will go to jail",
            "we will send someone to your house",
            "we will tell your family",
            "we will tell your employer",
            "you are a criminal",
            "you are a fraud"
        ],
        description="Phrases that should never be used by agents"
    )
    
    # ============ TIME & CONTACT RESTRICTIONS ============
    
    allowed_call_hours: dict[str, str] = Field(
        default_factory=lambda: {
            "start": "08:00",
            "end": "19:00",
            "timezone": "Asia/Kolkata"
        },
        description="Permitted calling hours"
    )
    
    max_call_attempts_per_day: int = Field(
        default=3,
        ge=1,
        description="Maximum permitted call attempts per customer per day"
    )
    
    # ============ REPORTING & NOTIFICATIONS ============
    
    notification_settings: dict[str, bool] = Field(
        default_factory=lambda: {
            "email_on_critical_violation": True,
            "email_on_high_risk_score": True,
            "webhook_enabled": False
        },
        description="Notification preferences"
    )
    
    report_recipients: list[str] = Field(
        default_factory=list,
        description="Email addresses for compliance reports"
    )
    
    # ============ METADATA ============
    
    config_version: str = Field(
        default="1.0.0",
        description="Configuration schema version"
    )
    
    last_updated: Optional[str] = Field(
        default=None,
        description="ISO timestamp of last configuration update"
    )
    
    notes: Optional[str] = Field(
        default=None,
        description="Additional notes or context"
    )
    
    # ============ EXTENSIBILITY ============
    
    custom_insights: dict[str, dict] = Field(
        default_factory=dict,
        description="Custom insight configurations for extensible analysis types. "
                    "Keys are insight type names, values are config dicts with 'enabled', 'config' fields. "
                    "Example: {'sentiment_by_speaker': {'enabled': True, 'config': {'threshold': 0.7}}, "
                    "'topic_clustering': {'enabled': True, 'config': {'min_clusters': 3}}}"
    )
    
    extensions: dict[str, Any] = Field(
        default_factory=dict,
        description="Free-form extensions field for custom metadata, plugin data, or future features. "
                    "Allows clients to attach arbitrary structured data without schema changes."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "business_domain": "Banking / Debt Recovery",
                "organization_name": "Example Bank Ltd",
                "active_policy_set": "RBI_Compliance_v2.1",
                "monitored_products": ["Credit Card", "Personal Loan", "Home Loan"],
                "risk_triggers": ["Legal Threats", "Harassment", "Abuse"],
                "custom_rules": [
                    {
                        "rule_id": "CUST-001",
                        "rule_name": "No Family Contact",
                        "description": "Agents must not contact family members without explicit consent",
                        "severity": "critical",
                        "category": "Privacy Protection"
                    }
                ]
            }
        }


class ConfigManager:
    """Manager for loading, validating, and merging client configurations."""
    
    @staticmethod
    def validate_config(config_dict: dict) -> ClientConfig:
        """
        Validate a configuration dictionary against the schema.
        
        Args:
            config_dict: Raw configuration dictionary
            
        Returns:
            Validated ClientConfig object
            
        Raises:
            ValidationError: If configuration is invalid
        """
        return ClientConfig(**config_dict)
    
    @staticmethod
    def merge_configs(base: dict, override: dict) -> dict:
        """
        Merge two configuration dictionaries.
        Override values take precedence over base values.
        Lists are replaced, not merged.
        
        Args:
            base: Base configuration dictionary
            override: Override configuration dictionary
            
        Returns:
            Merged configuration dictionary
        """
        merged = base.copy()
        
        for key, value in override.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                # Recursively merge nested dicts
                merged[key] = ConfigManager.merge_configs(merged[key], value)
            else:
                # Replace value (including lists)
                merged[key] = value
        
        return merged
    
    @staticmethod
    def get_risk_level_for_product(config: ClientConfig, product_name: str) -> str:
        """Get risk level for a specific product."""
        for product in config.products:
            if product.product_name.lower() == product_name.lower():
                return product.risk_level
        return "medium"  # default
    
    @staticmethod
    def get_active_triggers(config: ClientConfig) -> list[str]:
        """Get all active risk triggers (legacy + new format)."""
        triggers = config.risk_triggers.copy()
        triggers.extend([t.trigger_name for t in config.compliance_triggers])
        return list(set(triggers))  # deduplicate
    
    @staticmethod
    def is_prohibited_phrase_detected(config: ClientConfig, text: str) -> list[str]:
        """Check if any prohibited phrases appear in text."""
        detected = []
        text_lower = text.lower()
        for phrase in config.prohibited_phrases:
            if phrase.lower() in text_lower:
                detected.append(phrase)
        return detected
    
    @staticmethod
    def calculate_weighted_risk_score(
        config: ClientConfig,
        policy_violation_score: float,
        emotional_tone_score: float,
        threat_detection_score: float
    ) -> float:
        """Calculate weighted risk score based on config weights."""
        weights = config.risk_scoring
        total_score = (
            policy_violation_score * weights.weight_policy_violations +
            emotional_tone_score * weights.weight_emotional_tone +
            threat_detection_score * weights.weight_threat_detection
        )
        return min(100.0, max(0.0, total_score))  # clamp to 0-100
