"""
Risk Scoring and Call Outcome Classification System
Provides comprehensive, multi-factor risk assessment and outcome prediction.
"""
from __future__ import annotations

from typing import Literal
from enum import Enum


# ---------------------------------------------------------------------------
# Enums for Classification
# ---------------------------------------------------------------------------

class CallOutcome(str, Enum):
    """Possible call outcome classifications."""
    RESOLVED = "Resolved"
    ESCALATED = "Escalated"
    DROPPED = "Dropped"
    PENDING = "Pending"
    TRANSFERRED = "Transferred"
    CALLBACK_REQUIRED = "Callback Required"
    LEGAL_DISPUTE = "Legal Dispute"
    UNRESOLVED_COMPLAINT = "Unresolved Complaint"
    CUSTOMER_SATISFIED = "Customer Satisfied"
    CUSTOMER_DISSATISFIED = "Customer Dissatisfied"
    FOLLOW_UP_NEEDED = "Follow-up Needed"
    NO_RESOLUTION = "No Resolution"


class RiskLevel(str, Enum):
    """Risk level categorization."""
    MINIMAL = "minimal"      # 0-20
    LOW = "low"              # 21-40
    MODERATE = "moderate"    # 41-60
    HIGH = "high"            # 61-80
    CRITICAL = "critical"    # 81-100


class EscalationAction(str, Enum):
    """Recommended escalation actions."""
    NONE = "No escalation required"
    SUPERVISOR_REVIEW = "Supervisor review recommended"
    MANAGER_REVIEW = "Manager review required"
    COMPLIANCE_TEAM = "Escalate to compliance team"
    LEGAL_REVIEW = "Legal team review required"
    IMMEDIATE_INTERVENTION = "Immediate intervention required"
    EXECUTIVE_ATTENTION = "Executive level attention needed"


# ---------------------------------------------------------------------------
# Risk Component Weights
# ---------------------------------------------------------------------------

class RiskComponents:
    """Default risk scoring weights for different factors."""
    
    # Policy violation scoring
    CRITICAL_VIOLATION = 30
    HIGH_VIOLATION = 20
    MEDIUM_VIOLATION = 10
    LOW_VIOLATION = 5
    
    # Emotional tone scoring
    AGGRESSIVE_TONE = 20
    THREATENING_TONE = 25
    DISTRESSED_TONE = 15
    ANGRY_TONE = 15
    FRUSTRATED_TONE = 10
    ANXIOUS_TONE = 8
    
    # Threat detection scoring
    EXPLICIT_THREAT = 25
    IMPLIED_THREAT = 15
    INTIMIDATION = 10
    
    # Agent conduct scoring (negative scores)
    POOR_CONDUCT = 15
    UNACCEPTABLE_CONDUCT = 25
    UNPROFESSIONAL = 10
    
    # Time violation
    TIME_VIOLATION = 15
    
    # Prohibited phrase detection
    PROHIBITED_PHRASE = 30


# ---------------------------------------------------------------------------
# Risk Score Calculator
# ---------------------------------------------------------------------------

class RiskScoreCalculator:
    """
    Multi-factor risk score calculator.
    Generates comprehensive risk assessment based on multiple factors.
    """
    
    @staticmethod
    def calculate_comprehensive_score(
        policy_violations: list[dict],
        emotional_tone: str,
        detected_threats: list[str],
        agent_conduct: dict,
        time_violation: bool,
        prohibited_phrases_detected: int,
        acoustic_arousal_high_count: int = 0,
        client_config: dict = None,
    ) -> dict:
        """
        Calculate comprehensive risk score with breakdown.
        
        Returns:
            dict with:
                - total_score (0-100)
                - risk_level (minimal/low/moderate/high/critical)
                - breakdown (component scores)
                - escalation_action
                - justification
        """
        breakdown = {}
        score = 0
        
        # 1. Policy Violations Score (max 40 points)
        violation_score = RiskScoreCalculator._calculate_violation_score(policy_violations)
        breakdown["policy_violations"] = violation_score
        score += violation_score
        
        # 2. Emotional Tone Score (max 25 points)
        emotion_score = RiskScoreCalculator._calculate_emotion_score(
            emotional_tone, 
            acoustic_arousal_high_count
        )
        breakdown["emotional_intensity"] = emotion_score
        score += emotion_score
        
        # 3. Threat Detection Score (max 25 points)
        threat_score = RiskScoreCalculator._calculate_threat_score(detected_threats)
        breakdown["threat_level"] = threat_score
        score += threat_score
        
        # 4. Agent Conduct Score (max 25 points negative impact)
        conduct_score = RiskScoreCalculator._calculate_conduct_score(agent_conduct)
        breakdown["agent_conduct"] = conduct_score
        score += conduct_score
        
        # 5. Time Violation (15 points)
        if time_violation:
            breakdown["time_violation"] = 15
            score += 15
        else:
            breakdown["time_violation"] = 0
        
        # 6. Prohibited Phrases (30 points each, capped at 60)
        prohibited_score = min(prohibited_phrases_detected * 30, 60)
        breakdown["prohibited_phrases"] = prohibited_score
        score += prohibited_score
        
        # Cap at 100
        score = min(100, max(0, score))
        
        # Determine risk level
        risk_level = RiskScoreCalculator._determine_risk_level(score)
        
        # Determine escalation action
        escalation_action = RiskScoreCalculator._determine_escalation_action(
            score, 
            policy_violations,
            prohibited_phrases_detected,
            client_config
        )
        
        # Generate justification
        justification = RiskScoreCalculator._generate_justification(
            score,
            breakdown,
            policy_violations,
            detected_threats,
            prohibited_phrases_detected
        )
        
        return {
            "total_score": round(score, 1),
            "risk_level": risk_level.value,
            "risk_category": risk_level.name,
            "breakdown": breakdown,
            "escalation_action": escalation_action.value,
            "justification": justification,
            "requires_immediate_action": score >= 80,
            "auto_escalate": RiskScoreCalculator._should_auto_escalate(
                score, 
                prohibited_phrases_detected, 
                client_config
            )
        }
    
    @staticmethod
    def _calculate_violation_score(violations: list[dict]) -> int:
        """Calculate score from policy violations."""
        score = 0
        for violation in violations:
            severity = violation.get("severity", "medium").lower()
            if severity == "critical":
                score += RiskComponents.CRITICAL_VIOLATION
            elif severity == "high":
                score += RiskComponents.HIGH_VIOLATION
            elif severity == "medium":
                score += RiskComponents.MEDIUM_VIOLATION
            else:
                score += RiskComponents.LOW_VIOLATION
        return min(score, 40)  # Cap at 40
    
    @staticmethod
    def _calculate_emotion_score(emotional_tone: str, arousal_high_count: int) -> int:
        """Calculate score from emotional tone."""
        tone_lower = emotional_tone.lower()
        base_score = 0
        
        if "threatening" in tone_lower:
            base_score = RiskComponents.THREATENING_TONE
        elif "aggressive" in tone_lower:
            base_score = RiskComponents.AGGRESSIVE_TONE
        elif "distressed" in tone_lower:
            base_score = RiskComponents.DISTRESSED_TONE
        elif "angry" in tone_lower:
            base_score = RiskComponents.ANGRY_TONE
        elif "frustrated" in tone_lower:
            base_score = RiskComponents.FRUSTRATED_TONE
        elif "anxious" in tone_lower or "panicked" in tone_lower:
            base_score = RiskComponents.ANXIOUS_TONE
        
        # Add bonus for high acoustic arousal
        arousal_bonus = min(arousal_high_count * 2, 10)
        
        return min(base_score + arousal_bonus, 25)
    
    @staticmethod
    def _calculate_threat_score(threats: list[str]) -> int:
        """Calculate score from detected threats."""
        if not threats:
            return 0
        
        score = 0
        for threat in threats:
            threat_lower = threat.lower()
            if any(word in threat_lower for word in ["will", "going to", "must", "force"]):
                score += RiskComponents.EXPLICIT_THREAT
            elif any(word in threat_lower for word in ["might", "could", "may"]):
                score += RiskComponents.IMPLIED_THREAT
            else:
                score += RiskComponents.INTIMIDATION
        
        return min(score, 25)
    
    @staticmethod
    def _calculate_conduct_score(agent_conduct: dict) -> int:
        """Calculate negative score from poor agent conduct."""
        score = 0
        
        politeness = agent_conduct.get("politeness", "fair")
        professionalism = agent_conduct.get("professionalism", "fair")
        
        if politeness in ["unacceptable", "poor"]:
            score += RiskComponents.UNACCEPTABLE_CONDUCT if politeness == "unacceptable" else RiskComponents.POOR_CONDUCT
        
        if professionalism in ["unacceptable", "poor"]:
            score += RiskComponents.UNACCEPTABLE_CONDUCT if professionalism == "unacceptable" else RiskComponents.UNPROFESSIONAL
        
        return min(score, 25)
    
    @staticmethod
    def _determine_risk_level(score: float) -> RiskLevel:
        """Determine risk level category from score."""
        if score >= 81:
            return RiskLevel.CRITICAL
        elif score >= 61:
            return RiskLevel.HIGH
        elif score >= 41:
            return RiskLevel.MODERATE
        elif score >= 21:
            return RiskLevel.LOW
        else:
            return RiskLevel.MINIMAL
    
    @staticmethod
    def _determine_escalation_action(
        score: float, 
        violations: list[dict],
        prohibited_phrases: int,
        client_config: dict
    ) -> EscalationAction:
        """Determine required escalation action."""
        # Critical violations or prohibited phrases → immediate escalation
        if prohibited_phrases > 0:
            return EscalationAction.IMMEDIATE_INTERVENTION
        
        critical_violations = [v for v in violations if v.get("severity") == "critical"]
        if critical_violations:
            return EscalationAction.IMMEDIATE_INTERVENTION
        
        # Score-based escalation
        if score >= 90:
            return EscalationAction.EXECUTIVE_ATTENTION
        elif score >= 80:
            return EscalationAction.LEGAL_REVIEW
        elif score >= 65:
            return EscalationAction.COMPLIANCE_TEAM
        elif score >= 50:
            return EscalationAction.MANAGER_REVIEW
        elif score >= 35:
            return EscalationAction.SUPERVISOR_REVIEW
        else:
            return EscalationAction.NONE
    
    @staticmethod
    def _generate_justification(
        score: float,
        breakdown: dict,
        violations: list[dict],
        threats: list[str],
        prohibited_phrases: int
    ) -> str:
        """Generate human-readable justification for the risk score."""
        parts = []
        
        if prohibited_phrases > 0:
            parts.append(f"{prohibited_phrases} prohibited phrase(s) detected (automatic critical risk)")
        
        if violations:
            critical = len([v for v in violations if v.get("severity") == "critical"])
            high = len([v for v in violations if v.get("severity") == "high"])
            if critical > 0:
                parts.append(f"{critical} critical policy violation(s)")
            if high > 0:
                parts.append(f"{high} high-severity violation(s)")
        
        if threats:
            parts.append(f"{len(threats)} threat(s) detected")
        
        if breakdown.get("emotional_intensity", 0) >= 15:
            parts.append("high emotional intensity")
        
        if breakdown.get("agent_conduct", 0) >= 15:
            parts.append("poor agent conduct")
        
        if breakdown.get("time_violation", 0) > 0:
            parts.append("call timing violation")
        
        if not parts:
            return "Low risk call with no major compliance concerns"
        
        return f"Risk score {score}/100 due to: {', '.join(parts)}"
    
    @staticmethod
    def _should_auto_escalate(score: float, prohibited_phrases: int, client_config: dict) -> bool:
        """Determine if call should be auto-escalated."""
        if client_config:
            auto_escalate_setting = client_config.get("auto_escalate_on_critical", True)
            critical_threshold = client_config.get("risk_scoring", {}).get("critical_threshold", 80)
            
            if not auto_escalate_setting:
                return False
            
            return score >= critical_threshold or prohibited_phrases > 0
        
        # Default behavior
        return score >= 80 or prohibited_phrases > 0


# ---------------------------------------------------------------------------
# Call Outcome Classifier
# ---------------------------------------------------------------------------

class CallOutcomeClassifier:
    """Classifies call outcomes based on conversation analysis."""
    
    @staticmethod
    def classify_outcome(
        compliance_result: dict,
        transcript_threads: list[dict],
        risk_score: float,
    ) -> dict:
        """
        Classify call outcome with confidence scoring.
        
        Returns:
            dict with:
                - primary_outcome
                - confidence_score
                - outcome_reasoning
                - secondary_outcomes
                - next_action
                - urgency_level
        """
        # Extract key indicators
        violations = compliance_result.get("policy_violations", [])
        is_within_policy = compliance_result.get("is_within_policy", True)
        emotional_tone = compliance_result.get("emotional_tone", "Neutral")
        threats = compliance_result.get("detected_threats", [])
        final_status_raw = compliance_result.get("final_status", "")
        
        # Analyze conversation ending
        last_messages = transcript_threads[-3:] if len(transcript_threads) >= 3 else transcript_threads
        conversation_ending = " ".join([t.get("message", "") for t in last_messages]).lower()
        
        # Classify primary outcome
        primary_outcome, confidence = CallOutcomeClassifier._determine_primary_outcome(
            violations,
            is_within_policy,
            emotional_tone,
            threats,
            conversation_ending,
            risk_score,
            final_status_raw
        )
        
        # Determine secondary outcomes
        secondary_outcomes = CallOutcomeClassifier._determine_secondary_outcomes(
            primary_outcome,
            emotional_tone,
            violations,
            conversation_ending
        )
        
        # Generate outcome reasoning
        reasoning = CallOutcomeClassifier._generate_reasoning(
            primary_outcome,
            violations,
            emotional_tone,
            threats,
            conversation_ending
        )
        
        # Determine next action
        next_action = CallOutcomeClassifier._determine_next_action(
            primary_outcome,
            risk_score,
            violations
        )
        
        # Determine urgency
        urgency = CallOutcomeClassifier._determine_urgency(
            primary_outcome,
            risk_score,
            violations
        )
        
        return {
            "primary_outcome": primary_outcome.value,
            "outcome_category": primary_outcome.name,
            "confidence_score": confidence,
            "outcome_reasoning": reasoning,
            "secondary_outcomes": [s.value for s in secondary_outcomes],
            "next_action": next_action,
            "urgency_level": urgency,
            "requires_follow_up": CallOutcomeClassifier._requires_follow_up(primary_outcome),
            "customer_satisfaction_indicator": CallOutcomeClassifier._estimate_satisfaction(
                primary_outcome, 
                emotional_tone
            )
        }
    
    @staticmethod
    def _determine_primary_outcome(
        violations: list[dict],
        is_within_policy: bool,
        emotional_tone: str,
        threats: list[str],
        conversation_ending: str,
        risk_score: float,
        final_status_raw: str
    ) -> tuple[CallOutcome, float]:
        """Determine primary outcome and confidence score."""
        
        # Critical violations → Escalated
        if violations and any(v.get("severity") == "critical" for v in violations):
            return CallOutcome.ESCALATED, 0.95
        
        # Threats or high risk → Legal Dispute or Escalated
        if threats or risk_score >= 80:
            if "legal" in conversation_ending or "lawyer" in conversation_ending:
                return CallOutcome.LEGAL_DISPUTE, 0.90
            return CallOutcome.ESCALATED, 0.90
        
        # Check for explicit resolution indicators
        resolution_keywords = ["resolved", "solved", "fixed", "settled", "thank", "satisfied"]
        if any(word in conversation_ending for word in resolution_keywords):
            if "dissatisfied" in conversation_ending or "unhappy" in conversation_ending:
                return CallOutcome.CUSTOMER_DISSATISFIED, 0.85
            return CallOutcome.RESOLVED, 0.85
        
        # Check for callback/follow-up indicators
        callback_keywords = ["call back", "callback", "follow up", "get back", "check"]
        if any(word in conversation_ending for word in callback_keywords):
            return CallOutcome.CALLBACK_REQUIRED, 0.80
        
        # Check for transfer indicators
        transfer_keywords = ["transfer", "escalate", "supervisor", "manager"]
        if any(word in conversation_ending for word in transfer_keywords):
            return CallOutcome.TRANSFERRED, 0.85
        
        # Check for unresolved/pending
        if "pending" in final_status_raw.lower() or "review" in final_status_raw.lower():
            return CallOutcome.PENDING, 0.75
        
        # Emotional tone analysis
        if "angry" in emotional_tone.lower() or "aggressive" in emotional_tone.lower():
            return CallOutcome.UNRESOLVED_COMPLAINT, 0.80
        
        if "satisfied" in emotional_tone.lower() or "calm" in emotional_tone.lower():
            if not violations:
                return CallOutcome.CUSTOMER_SATISFIED, 0.80
        
        # Call dropped indicators
        dropped_keywords = ["disconnect", "hung up", "dropped", "ended abruptly"]
        if any(word in conversation_ending for word in dropped_keywords):
            return CallOutcome.DROPPED, 0.75
        
        # Default: analyze based on policy compliance
        if is_within_policy and risk_score < 40:
            return CallOutcome.RESOLVED, 0.70
        elif violations:
            return CallOutcome.UNRESOLVED_COMPLAINT, 0.65
        else:
            return CallOutcome.PENDING, 0.60
    
    @staticmethod
    def _determine_secondary_outcomes(
        primary: CallOutcome,
        emotional_tone: str,
        violations: list[dict],
        conversation_ending: str
    ) -> list[CallOutcome]:
        """Identify secondary outcome classifications."""
        secondary = []
        
        if primary == CallOutcome.RESOLVED:
            if "thank" in conversation_ending:
                secondary.append(CallOutcome.CUSTOMER_SATISFIED)
            else:
                secondary.append(CallOutcome.FOLLOW_UP_NEEDED)
        
        elif primary == CallOutcome.ESCALATED:
            if violations:
                secondary.append(CallOutcome.UNRESOLVED_COMPLAINT)
            if "legal" in conversation_ending:
                secondary.append(CallOutcome.LEGAL_DISPUTE)
        
        elif primary == CallOutcome.PENDING:
            if "callback" in conversation_ending or "follow" in conversation_ending:
                secondary.append(CallOutcome.CALLBACK_REQUIRED)
            else:
                secondary.append(CallOutcome.FOLLOW_UP_NEEDED)
        
        return secondary[:2]  # Max 2 secondary outcomes
    
    @staticmethod
    def _generate_reasoning(
        outcome: CallOutcome,
        violations: list[dict],
        emotional_tone: str,
        threats: list[str],
        conversation_ending: str
    ) -> str:
        """Generate explanation for why this outcome was classified."""
        reasons = []
        
        if outcome == CallOutcome.RESOLVED:
            reasons.append("Conversation ended with resolution indicators")
            if not violations:
                reasons.append("no policy violations detected")
        
        elif outcome == CallOutcome.ESCALATED:
            if violations:
                reasons.append(f"{len(violations)} policy violation(s) detected")
            if threats:
                reasons.append("threats detected in conversation")
            reasons.append("requires management review")
        
        elif outcome == CallOutcome.LEGAL_DISPUTE:
            reasons.append("Legal action mentioned or threatened")
            reasons.append("immediate legal team review required")
        
        elif outcome == CallOutcome.CALLBACK_REQUIRED:
            reasons.append("Agent committed to follow-up action")
        
        elif outcome == CallOutcome.DROPPED:
            reasons.append("Call ended abruptly without resolution")
        
        elif outcome == CallOutcome.UNRESOLVED_COMPLAINT:
            reasons.append("Customer concerns not adequately addressed")
            if "angry" in emotional_tone.lower():
                reasons.append("customer expressed significant frustration")
        
        elif outcome == CallOutcome.CUSTOMER_SATISFIED:
            reasons.append("Positive resolution with customer satisfaction indicators")
        
        elif outcome == CallOutcome.CUSTOMER_DISSATISFIED:
            reasons.append("Despite resolution attempt, customer remains dissatisfied")
        
        return ". ".join(reasons) if reasons else "Classification based on conversation flow analysis"
    
    @staticmethod
    def _determine_next_action(
        outcome: CallOutcome,
        risk_score: float,
        violations: list[dict]
    ) -> str:
        """Recommend specific next action."""
        if outcome == CallOutcome.ESCALATED:
            if risk_score >= 80:
                return "Immediate escalation to compliance manager and legal review"
            return "Escalate to supervisor for review and appropriate action"
        
        elif outcome == CallOutcome.LEGAL_DISPUTE:
            return "Forward to legal department immediately; document all evidence"
        
        elif outcome == CallOutcome.CALLBACK_REQUIRED:
            return "Schedule callback within 24-48 hours; ensure follow-through"
        
        elif outcome == CallOutcome.UNRESOLVED_COMPLAINT:
            return "Re-engage customer with senior agent; offer resolution options"
        
        elif outcome == CallOutcome.DROPPED:
            return "Attempt reconnection; investigate reason for call termination"
        
        elif outcome == CallOutcome.PENDING:
            return "Monitor for updates; follow up if no resolution within 3-5 business days"
        
        elif outcome == CallOutcome.CUSTOMER_DISSATISFIED:
            return "Customer retention intervention; offer goodwill gesture if appropriate"
        
        elif outcome == CallOutcome.RESOLVED:
            if violations:
                return "Document resolution; review agent performance for improvement"
            return "Close case; no further action required unless customer re-contacts"
        
        elif outcome == CallOutcome.CUSTOMER_SATISFIED:
            return "Close case successfully; use as positive training example"
        
        return "Review case details and determine appropriate next steps"
    
    @staticmethod
    def _determine_urgency(
        outcome: CallOutcome,
        risk_score: float,
        violations: list[dict]
    ) -> str:
        """Determine urgency level."""
        critical_outcomes = [
            CallOutcome.LEGAL_DISPUTE,
            CallOutcome.ESCALATED
        ]
        
        if outcome in critical_outcomes or risk_score >= 80:
            return "critical"
        
        if risk_score >= 60 or outcome == CallOutcome.UNRESOLVED_COMPLAINT:
            return "high"
        
        if outcome in [CallOutcome.CALLBACK_REQUIRED, CallOutcome.PENDING]:
            return "medium"
        
        return "low"
    
    @staticmethod
    def _requires_follow_up(outcome: CallOutcome) -> bool:
        """Determine if outcome requires follow-up."""
        follow_up_outcomes = [
            CallOutcome.CALLBACK_REQUIRED,
            CallOutcome.PENDING,
            CallOutcome.FOLLOW_UP_NEEDED,
            CallOutcome.UNRESOLVED_COMPLAINT,
            CallOutcome.DROPPED
        ]
        return outcome in follow_up_outcomes
    
    @staticmethod
    def _estimate_satisfaction(outcome: CallOutcome, emotional_tone: str) -> str:
        """Estimate customer satisfaction level."""
        if outcome == CallOutcome.CUSTOMER_SATISFIED:
            return "satisfied"
        
        if outcome == CallOutcome.CUSTOMER_DISSATISFIED:
            return "dissatisfied"
        
        if outcome in [CallOutcome.LEGAL_DISPUTE, CallOutcome.ESCALATED]:
            return "highly_dissatisfied"
        
        if outcome in [CallOutcome.RESOLVED, CallOutcome.TRANSFERRED]:
            if "calm" in emotional_tone.lower() or "neutral" in emotional_tone.lower():
                return "neutral_to_satisfied"
            return "neutral"
        
        if outcome in [CallOutcome.UNRESOLVED_COMPLAINT, CallOutcome.DROPPED]:
            return "dissatisfied"
        
        return "neutral"
