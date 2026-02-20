"""
Agent Performance Scoring System
Provides comprehensive, multi-dimensional agent quality assessment.
"""
from __future__ import annotations

from typing import Literal
from enum import Enum


# ---------------------------------------------------------------------------
# Enums for Agent Performance Classification
# ---------------------------------------------------------------------------

class PerformanceLevel(str, Enum):
    """Agent performance level categorization."""
    EXCEPTIONAL = "exceptional"      # 90-100
    EXCELLENT = "excellent"          # 80-89
    GOOD = "good"                    # 70-79
    SATISFACTORY = "satisfactory"    # 60-69
    NEEDS_IMPROVEMENT = "needs_improvement"  # 40-59
    POOR = "poor"                    # 20-39
    UNACCEPTABLE = "unacceptable"    # 0-19


class TrainingPriority(str, Enum):
    """Training priority levels."""
    CRITICAL = "critical"        # Immediate training required
    HIGH = "high"                # Training needed within 1 week
    MEDIUM = "medium"            # Training recommended within 1 month
    LOW = "low"                  # Optional enhancement training
    NONE = "none"                # No training needed


class ImprovementArea(str, Enum):
    """Specific areas where agent can improve."""
    COMMUNICATION_CLARITY = "Communication Clarity"
    ACTIVE_LISTENING = "Active Listening"
    EMPATHY_BUILDING = "Empathy and Customer Understanding"
    POLITENESS_COURTESY = "Politeness and Courtesy"
    PROFESSIONALISM = "Professional Demeanor"
    PROBLEM_SOLVING = "Problem Resolution Skills"
    COMPLIANCE_TRAINING = "Compliance and Policy Adherence"
    EMOTIONAL_REGULATION = "Emotional Control and Composure"
    LANGUAGE_USE = "Appropriate Language Use"
    CONFLICT_RESOLUTION = "Conflict De-escalation"
    PRODUCT_KNOWLEDGE = "Product/Service Knowledge"
    CALL_CONTROL = "Call Management and Control"


# ---------------------------------------------------------------------------
# Performance Component Weights
# ---------------------------------------------------------------------------

class PerformanceComponents:
    """Scoring weights for different agent performance factors."""
    
    # Communication Skills (max 30 points)
    EXCELLENT_COMMUNICATION = 30
    GOOD_COMMUNICATION = 24
    FAIR_COMMUNICATION = 18
    POOR_COMMUNICATION = 10
    
    # Customer Service Excellence (max 25 points)
    EXCELLENT_POLITENESS = 12
    GOOD_POLITENESS = 9
    FAIR_POLITENESS = 6
    POOR_POLITENESS = 2
    UNACCEPTABLE_POLITENESS = 0
    
    HIGH_EMPATHY = 13
    MEDIUM_EMPATHY = 8
    LOW_EMPATHY = 4
    NO_EMPATHY = 0
    
    # Professionalism (max 20 points)
    EXCELLENT_PROFESSIONALISM = 20
    GOOD_PROFESSIONALISM = 16
    FAIR_PROFESSIONALISM = 12
    POOR_PROFESSIONALISM = 6
    UNACCEPTABLE_PROFESSIONALISM = 0
    
    # Problem Resolution (max 15 points)
    RESOLVED_EFFECTIVELY = 15
    PARTIAL_RESOLUTION = 10
    ATTEMPTED_RESOLUTION = 6
    NO_RESOLUTION = 0
    
    # Compliance Adherence (max 10 points)
    FULL_COMPLIANCE = 10
    MINOR_VIOLATIONS = 5
    MAJOR_VIOLATIONS = 0
    
    # Negative Modifiers (deductions)
    PROHIBITED_PHRASE_PENALTY = -15
    THREAT_MADE_PENALTY = -20
    HARASSMENT_PENALTY = -25
    TIME_VIOLATION_PENALTY = -5


# ---------------------------------------------------------------------------
# Agent Performance Calculator
# ---------------------------------------------------------------------------

class AgentPerformanceCalculator:
    """
    Multi-dimensional agent performance scorer.
    Generates comprehensive quality assessment with actionable feedback.
    """
    
    @staticmethod
    def calculate_performance_score(
        politeness: str,
        empathy: str,
        professionalism: str,
        policy_violations: list[dict],
        detected_threats: list[str],
        call_outcome: str,
        prohibited_phrases_detected: int,
        time_violation: bool,
        transcript_threads: list[dict] = None,
        emotional_tone: str = "",
    ) -> dict:
        """
        Calculate comprehensive agent performance score.
        
        Returns:
            dict with:
                - total_score (0-100)
                - performance_level (exceptional/excellent/good/satisfactory/needs_improvement/poor/unacceptable)
                - breakdown (component scores)
                - strengths (list of strong areas)
                - weaknesses (list of improvement areas)
                - training_priority
                - training_recommendations
                - specific_feedback
        """
        breakdown = {}
        score = 0
        
        # 1. Communication Skills Score (max 30 points)
        communication_score = AgentPerformanceCalculator._calculate_communication_score(
            transcript_threads,
            emotional_tone
        )
        breakdown["communication_skills"] = communication_score
        score += communication_score
        
        # 2. Customer Service Excellence Score (max 25 points)
        # 2a. Politeness (max 12 points)
        politeness_score = AgentPerformanceCalculator._calculate_politeness_score(politeness)
        breakdown["politeness"] = politeness_score
        score += politeness_score
        
        # 2b. Empathy (max 13 points)
        empathy_score = AgentPerformanceCalculator._calculate_empathy_score(empathy)
        breakdown["empathy"] = empathy_score
        score += empathy_score
        
        # 3. Professionalism Score (max 20 points)
        professionalism_score = AgentPerformanceCalculator._calculate_professionalism_score(professionalism)
        breakdown["professionalism"] = professionalism_score
        score += professionalism_score
        
        # 4. Problem Resolution Score (max 15 points)
        resolution_score = AgentPerformanceCalculator._calculate_resolution_score(
            call_outcome,
            policy_violations
        )
        breakdown["problem_resolution"] = resolution_score
        score += resolution_score
        
        # 5. Compliance Adherence Score (max 10 points)
        compliance_score = AgentPerformanceCalculator._calculate_compliance_score(
            policy_violations,
            prohibited_phrases_detected
        )
        breakdown["compliance_adherence"] = compliance_score
        score += compliance_score
        
        # 6. Apply Penalties (negative modifiers)
        penalties = AgentPerformanceCalculator._calculate_penalties(
            prohibited_phrases_detected,
            detected_threats,
            time_violation,
            policy_violations
        )
        breakdown["penalties"] = penalties
        score += penalties
        
        # Cap at 0-100 range
        score = min(100, max(0, score))
        
        # Determine performance level
        performance_level = AgentPerformanceCalculator._determine_performance_level(score)
        
        # Identify strengths and weaknesses
        strengths = AgentPerformanceCalculator._identify_strengths(
            breakdown, 
            politeness, 
            empathy, 
            professionalism
        )
        weaknesses = AgentPerformanceCalculator._identify_weaknesses(
            breakdown,
            politeness,
            empathy,
            professionalism,
            policy_violations,
            call_outcome
        )
        
        # Determine training priority
        training_priority = AgentPerformanceCalculator._determine_training_priority(
            score,
            weaknesses,
            prohibited_phrases_detected,
            policy_violations
        )
        
        # Generate training recommendations
        training_recommendations = AgentPerformanceCalculator._generate_training_recommendations(
            weaknesses,
            policy_violations,
            prohibited_phrases_detected
        )
        
        # Generate specific feedback
        specific_feedback = AgentPerformanceCalculator._generate_specific_feedback(
            score,
            strengths,
            weaknesses,
            policy_violations
        )
        
        return {
            "total_score": round(score, 1),
            "performance_level": performance_level.value,
            "performance_category": performance_level.name,
            "breakdown": breakdown,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "training_priority": training_priority.value,
            "training_recommendations": training_recommendations,
            "specific_feedback": specific_feedback,
            "requires_coaching": score < 70,
            "requires_disciplinary_action": score < 40 or prohibited_phrases_detected > 0,
            "commendation_worthy": score >= 90
        }
    
    @staticmethod
    def _calculate_communication_score(transcript_threads: list[dict], emotional_tone: str) -> int:
        """Calculate communication skills score (max 30)."""
        if not transcript_threads:
            return 18  # Default: fair
        
        agent_messages = [t for t in transcript_threads if t.get("speaker") == "Agent"]
        
        if not agent_messages:
            return 18
        
        # Analyze communication quality
        score = 18  # Start at fair
        
        # Check for clear, complete sentences
        avg_message_length = sum(len(t.get("message", "")) for t in agent_messages) / max(len(agent_messages), 1)
        
        if avg_message_length > 50:  # Good detail
            score += 6
        elif avg_message_length > 30:
            score += 3
        
        # Check for professional tone indicators
        professional_phrases = ["understand", "assist", "help", "appreciate", "apologies"]
        professional_count = sum(
            1 for msg in agent_messages 
            for phrase in professional_phrases 
            if phrase in msg.get("message", "").lower()
        )
        
        if professional_count >= 3:
            score += 6
        elif professional_count >= 1:
            score += 3
        
        # Penalty for aggressive tone
        if "aggressive" in emotional_tone.lower() or "threatening" in emotional_tone.lower():
            score -= 10
        
        return min(30, max(0, score))
    
    @staticmethod
    def _calculate_politeness_score(politeness: str) -> int:
        """Calculate politeness score (max 12)."""
        politeness_lower = politeness.lower()
        
        if "excellent" in politeness_lower:
            return PerformanceComponents.EXCELLENT_POLITENESS
        elif "good" in politeness_lower:
            return PerformanceComponents.GOOD_POLITENESS
        elif "fair" in politeness_lower:
            return PerformanceComponents.FAIR_POLITENESS
        elif "poor" in politeness_lower:
            return PerformanceComponents.POOR_POLITENESS
        else:  # unacceptable
            return PerformanceComponents.UNACCEPTABLE_POLITENESS
    
    @staticmethod
    def _calculate_empathy_score(empathy: str) -> int:
        """Calculate empathy score (max 13)."""
        empathy_lower = empathy.lower()
        
        if "high" in empathy_lower:
            return PerformanceComponents.HIGH_EMPATHY
        elif "medium" in empathy_lower:
            return PerformanceComponents.MEDIUM_EMPATHY
        elif "low" in empathy_lower:
            return PerformanceComponents.LOW_EMPATHY
        else:  # none
            return PerformanceComponents.NO_EMPATHY
    
    @staticmethod
    def _calculate_professionalism_score(professionalism: str) -> int:
        """Calculate professionalism score (max 20)."""
        professionalism_lower = professionalism.lower()
        
        if "excellent" in professionalism_lower:
            return PerformanceComponents.EXCELLENT_PROFESSIONALISM
        elif "good" in professionalism_lower:
            return PerformanceComponents.GOOD_PROFESSIONALISM
        elif "fair" in professionalism_lower:
            return PerformanceComponents.FAIR_PROFESSIONALISM
        elif "poor" in professionalism_lower:
            return PerformanceComponents.POOR_PROFESSIONALISM
        else:  # unacceptable
            return PerformanceComponents.UNACCEPTABLE_PROFESSIONALISM
    
    @staticmethod
    def _calculate_resolution_score(call_outcome: str, policy_violations: list[dict]) -> int:
        """Calculate problem resolution score (max 15)."""
        outcome_lower = call_outcome.lower()
        
        # High resolution score outcomes
        if any(word in outcome_lower for word in ["resolved", "satisfied", "customer satisfied"]):
            return PerformanceComponents.RESOLVED_EFFECTIVELY
        
        # Partial resolution outcomes
        elif any(word in outcome_lower for word in ["callback", "pending", "follow-up", "transferred"]):
            return PerformanceComponents.PARTIAL_RESOLUTION
        
        # Attempted but not resolved
        elif any(word in outcome_lower for word in ["escalated", "unresolved"]):
            # Penalize if violations caused escalation
            if policy_violations and any(v.get("severity") in ["critical", "high"] for v in policy_violations):
                return PerformanceComponents.NO_RESOLUTION
            return PerformanceComponents.ATTEMPTED_RESOLUTION
        
        # Poor outcomes
        elif any(word in outcome_lower for word in ["dropped", "legal", "dissatisfied"]):
            return PerformanceComponents.NO_RESOLUTION
        
        # Default: attempted
        return PerformanceComponents.ATTEMPTED_RESOLUTION
    
    @staticmethod
    def _calculate_compliance_score(policy_violations: list[dict], prohibited_phrases: int) -> int:
        """Calculate compliance adherence score (max 10)."""
        if prohibited_phrases > 0:
            return PerformanceComponents.MAJOR_VIOLATIONS
        
        critical_violations = [v for v in policy_violations if v.get("severity") == "critical"]
        high_violations = [v for v in policy_violations if v.get("severity") == "high"]
        
        if critical_violations:
            return PerformanceComponents.MAJOR_VIOLATIONS
        elif high_violations or len(policy_violations) >= 3:
            return PerformanceComponents.MINOR_VIOLATIONS
        elif policy_violations:
            return PerformanceComponents.MINOR_VIOLATIONS
        else:
            return PerformanceComponents.FULL_COMPLIANCE
    
    @staticmethod
    def _calculate_penalties(
        prohibited_phrases: int,
        detected_threats: list[str],
        time_violation: bool,
        policy_violations: list[dict]
    ) -> int:
        """Calculate negative modifiers (penalties)."""
        penalty = 0
        
        if prohibited_phrases > 0:
            penalty += PerformanceComponents.PROHIBITED_PHRASE_PENALTY * min(prohibited_phrases, 2)
        
        if detected_threats:
            # Check if agent made threats
            for violation in policy_violations:
                if "threat" in violation.get("description", "").lower():
                    penalty += PerformanceComponents.THREAT_MADE_PENALTY
                    break
        
        # Check for harassment patterns
        harassment_keywords = ["harassment", "intimidation", "coercion"]
        for violation in policy_violations:
            if any(keyword in violation.get("description", "").lower() for keyword in harassment_keywords):
                penalty += PerformanceComponents.HARASSMENT_PENALTY
                break
        
        if time_violation:
            penalty += PerformanceComponents.TIME_VIOLATION_PENALTY
        
        return penalty
    
    @staticmethod
    def _determine_performance_level(score: float) -> PerformanceLevel:
        """Determine performance level category from score."""
        if score >= 90:
            return PerformanceLevel.EXCEPTIONAL
        elif score >= 80:
            return PerformanceLevel.EXCELLENT
        elif score >= 70:
            return PerformanceLevel.GOOD
        elif score >= 60:
            return PerformanceLevel.SATISFACTORY
        elif score >= 40:
            return PerformanceLevel.NEEDS_IMPROVEMENT
        elif score >= 20:
            return PerformanceLevel.POOR
        else:
            return PerformanceLevel.UNACCEPTABLE
    
    @staticmethod
    def _identify_strengths(
        breakdown: dict,
        politeness: str,
        empathy: str,
        professionalism: str
    ) -> list[str]:
        """Identify agent's strong areas."""
        strengths = []
        
        if breakdown.get("communication_skills", 0) >= 24:
            strengths.append("Excellent communication clarity and articulation")
        
        if politeness.lower() in ["excellent", "good"]:
            strengths.append("Strong politeness and courtesy")
        
        if empathy.lower() == "high":
            strengths.append("High empathy and customer understanding")
        
        if professionalism.lower() in ["excellent", "good"]:
            strengths.append("Professional demeanor and conduct")
        
        if breakdown.get("problem_resolution", 0) >= 12:
            strengths.append("Effective problem resolution skills")
        
        if breakdown.get("compliance_adherence", 0) == 10:
            strengths.append("Full compliance with policies and regulations")
        
        if breakdown.get("penalties", 0) == 0:
            strengths.append("No policy violations or inappropriate conduct")
        
        if not strengths:
            strengths.append("Completed the call interaction")
        
        return strengths
    
    @staticmethod
    def _identify_weaknesses(
        breakdown: dict,
        politeness: str,
        empathy: str,
        professionalism: str,
        policy_violations: list[dict],
        call_outcome: str
    ) -> list[ImprovementArea]:
        """Identify areas needing improvement."""
        weaknesses = []
        
        if breakdown.get("communication_skills", 0) < 18:
            weaknesses.append(ImprovementArea.COMMUNICATION_CLARITY)
            weaknesses.append(ImprovementArea.ACTIVE_LISTENING)
        
        if politeness.lower() in ["poor", "unacceptable"]:
            weaknesses.append(ImprovementArea.POLITENESS_COURTESY)
        
        if empathy.lower() in ["low", "none"]:
            weaknesses.append(ImprovementArea.EMPATHY_BUILDING)
        
        if professionalism.lower() in ["poor", "unacceptable"]:
            weaknesses.append(ImprovementArea.PROFESSIONALISM)
        
        if breakdown.get("problem_resolution", 0) < 10:
            weaknesses.append(ImprovementArea.PROBLEM_SOLVING)
        
        if breakdown.get("compliance_adherence", 0) < 10:
            weaknesses.append(ImprovementArea.COMPLIANCE_TRAINING)
        
        if policy_violations:
            # Check for specific violation types
            for violation in policy_violations:
                desc = violation.get("description", "").lower()
                if "language" in desc or "inappropriate" in desc:
                    if ImprovementArea.LANGUAGE_USE not in weaknesses:
                        weaknesses.append(ImprovementArea.LANGUAGE_USE)
                if "threat" in desc or "aggressive" in desc:
                    if ImprovementArea.CONFLICT_RESOLUTION not in weaknesses:
                        weaknesses.append(ImprovementArea.CONFLICT_RESOLUTION)
                    if ImprovementArea.EMOTIONAL_REGULATION not in weaknesses:
                        weaknesses.append(ImprovementArea.EMOTIONAL_REGULATION)
        
        if "dissatisfied" in call_outcome.lower() or "dropped" in call_outcome.lower():
            if ImprovementArea.CONFLICT_RESOLUTION not in weaknesses:
                weaknesses.append(ImprovementArea.CONFLICT_RESOLUTION)
        
        return weaknesses
    
    @staticmethod
    def _determine_training_priority(
        score: float,
        weaknesses: list[ImprovementArea],
        prohibited_phrases: int,
        policy_violations: list[dict]
    ) -> TrainingPriority:
        """Determine training priority level."""
        if prohibited_phrases > 0:
            return TrainingPriority.CRITICAL
        
        critical_violations = [v for v in policy_violations if v.get("severity") == "critical"]
        if critical_violations:
            return TrainingPriority.CRITICAL
        
        if score < 40:
            return TrainingPriority.CRITICAL
        elif score < 60:
            return TrainingPriority.HIGH
        elif score < 70:
            return TrainingPriority.MEDIUM
        elif score < 80:
            return TrainingPriority.LOW
        else:
            return TrainingPriority.NONE
    
    @staticmethod
    def _generate_training_recommendations(
        weaknesses: list[ImprovementArea],
        policy_violations: list[dict],
        prohibited_phrases: int
    ) -> list[str]:
        """Generate specific training recommendations."""
        recommendations = []
        
        # Critical training needs
        if prohibited_phrases > 0:
            recommendations.append("CRITICAL: Immediate training on prohibited language and appropriate communication")
            recommendations.append("CRITICAL: Review and sign-off on company communication guidelines")
        
        if policy_violations:
            critical = [v for v in policy_violations if v.get("severity") == "critical"]
            if critical:
                recommendations.append("CRITICAL: Mandatory compliance retraining on policy violations committed")
        
        # Weakness-specific training
        training_map = {
            ImprovementArea.COMMUNICATION_CLARITY: "Communication skills workshop: Clear articulation and message structuring",
            ImprovementArea.ACTIVE_LISTENING: "Active listening training: Techniques for better customer understanding",
            ImprovementArea.EMPATHY_BUILDING: "Empathy and emotional intelligence training",
            ImprovementArea.POLITENESS_COURTESY: "Customer service excellence: Politeness and professional courtesy",
            ImprovementArea.PROFESSIONALISM: "Professional conduct and business etiquette training",
            ImprovementArea.PROBLEM_SOLVING: "Problem-solving and resolution skills workshop",
            ImprovementArea.COMPLIANCE_TRAINING: "Compliance and regulatory adherence certification course",
            ImprovementArea.EMOTIONAL_REGULATION: "Stress management and emotional control training",
            ImprovementArea.LANGUAGE_USE: "Appropriate language and tone training for customer interactions",
            ImprovementArea.CONFLICT_RESOLUTION: "Conflict de-escalation and resolution techniques",
            ImprovementArea.PRODUCT_KNOWLEDGE: "Product/service knowledge enhancement sessions",
            ImprovementArea.CALL_CONTROL: "Call management and control strategies workshop"
        }
        
        for weakness in weaknesses:
            if weakness in training_map:
                recommendations.append(training_map[weakness])
        
        if not recommendations:
            recommendations.append("Continue current performance level with periodic refresher training")
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    @staticmethod
    def _generate_specific_feedback(
        score: float,
        strengths: list[str],
        weaknesses: list[ImprovementArea],
        policy_violations: list[dict]
    ) -> str:
        """Generate human-readable specific feedback."""
        feedback_parts = []
        
        # Performance summary
        if score >= 90:
            feedback_parts.append("Outstanding performance demonstrating exceptional customer service and compliance.")
        elif score >= 80:
            feedback_parts.append("Excellent performance with strong customer service and professional conduct.")
        elif score >= 70:
            feedback_parts.append("Good performance overall with room for skill enhancement.")
        elif score >= 60:
            feedback_parts.append("Satisfactory performance but requires focused improvement in key areas.")
        elif score >= 40:
            feedback_parts.append("Performance needs significant improvement. Coaching required.")
        else:
            feedback_parts.append("Unacceptable performance. Immediate intervention and retraining necessary.")
        
        # Strengths
        if strengths:
            feedback_parts.append(f"Key strengths: {', '.join(strengths[:3])}")
        
        # Improvement areas
        if weaknesses:
            weakness_names = [w.value for w in weaknesses[:3]]
            feedback_parts.append(f"Focus areas for improvement: {', '.join(weakness_names)}")
        
        # Critical issues
        if policy_violations:
            critical = len([v for v in policy_violations if v.get("severity") == "critical"])
            high = len([v for v in policy_violations if v.get("severity") == "high"])
            if critical > 0:
                feedback_parts.append(f"{critical} critical policy violation(s) require immediate corrective action.")
            elif high > 0:
                feedback_parts.append(f"{high} high-severity violation(s) need to be addressed promptly.")
        
        return " ".join(feedback_parts)


# ---------------------------------------------------------------------------
# Agent Performance Comparator (for benchmarking)
# ---------------------------------------------------------------------------

class AgentPerformanceComparator:
    """Compare agent performance against benchmarks or team averages."""
    
    @staticmethod
    def compare_to_benchmark(
        agent_score: float,
        team_average: float = 75.0,
        company_benchmark: float = 80.0
    ) -> dict:
        """
        Compare agent performance to benchmarks.
        
        Returns:
            dict with comparison metrics and positioning
        """
        return {
            "agent_score": agent_score,
            "team_average": team_average,
            "company_benchmark": company_benchmark,
            "vs_team_average": round(agent_score - team_average, 1),
            "vs_company_benchmark": round(agent_score - company_benchmark, 1),
            "percentile_vs_team": AgentPerformanceComparator._calculate_percentile(
                agent_score, 
                team_average
            ),
            "meets_company_standard": agent_score >= company_benchmark,
            "performance_tier": AgentPerformanceComparator._determine_tier(
                agent_score, 
                company_benchmark
            )
        }
    
    @staticmethod
    def _calculate_percentile(score: float, average: float) -> str:
        """Estimate percentile based on score vs average."""
        diff = score - average
        if diff >= 20:
            return "Top 10%"
        elif diff >= 10:
            return "Top 25%"
        elif diff >= 0:
            return "Above average (50th-75th percentile)"
        elif diff >= -10:
            return "Below average (25th-50th percentile)"
        else:
            return "Bottom 25%"
    
    @staticmethod
    def _determine_tier(score: float, benchmark: float) -> str:
        """Determine performance tier."""
        if score >= benchmark + 10:
            return "Elite Performer"
        elif score >= benchmark:
            return "Meets Standard"
        elif score >= benchmark - 10:
            return "Approaching Standard"
        else:
            return "Below Standard"
