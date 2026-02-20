"""
JSON Output Builder – Assembles the final Vigilant response JSON
from all service outputs, matching the exact output schema.
"""
from __future__ import annotations

import time
from typing import Optional


def _complexity_from_turns(turn_count: int) -> str:
    if turn_count <= 6:
        return "low"
    elif turn_count <= 14:
        return "medium"
    return "high"


def _parse_timestamp(ts: str) -> int:
    """Convert MM:SS timestamp to total seconds for comparison."""
    try:
        if ":" in ts:
            parts = ts.split(":")
            return int(parts[0]) * 60 + int(parts[1])
        return 0
    except:
        return 0


def _find_closest_tone(timestamp: str, emotional_graph: list[dict]) -> dict:
    """
    Find the closest tone information for a given timestamp.
    Uses intelligent interpolation if exact match isn't found.
    
    Args:
        timestamp: Timestamp in MM:SS format
        emotional_graph: List of emotion data points with timestamps
        
    Returns:
        Dict with tone, score, and acoustic_arousal, or defaults if not found
    """
    if not emotional_graph:
        return {
            "tone": "Neutral",
            "sentiment_score": 0.5,
            "acoustic_arousal": "Low"
        }
    
    target_seconds = _parse_timestamp(timestamp)
    
    # Find exact match first
    for entry in emotional_graph:
        if entry.get("timestamp") == timestamp:
            return {
                "tone": entry.get("tone", "Neutral"),
                "sentiment_score": entry.get("score", 0.5),
                "acoustic_arousal": entry.get("acoustic_arousal", "Low")
            }
    
    # Find the closest emotion data point (within 30 seconds)
    closest_entry = None
    min_diff = float('inf')
    
    for entry in emotional_graph:
        entry_seconds = _parse_timestamp(entry.get("timestamp", "00:00"))
        diff = abs(target_seconds - entry_seconds)
        
        if diff < min_diff:
            min_diff = diff
            closest_entry = entry
    
    # Use closest entry if within reasonable range (45 seconds)
    if closest_entry and min_diff <= 45:
        return {
            "tone": closest_entry.get("tone", "Neutral"),
            "sentiment_score": closest_entry.get("score", 0.5),
            "acoustic_arousal": closest_entry.get("acoustic_arousal", "Low")
        }
    
    # Fallback: return neutral if no good match
    return {
        "tone": "Neutral",
        "sentiment_score": 0.5,
        "acoustic_arousal": "Low"
    }


def _enrich_transcript_with_tones(
    transcript_threads: list[dict],
    emotional_graph: list[dict],
    compliance_result: dict
) -> list[dict]:
    """
    Enrich transcript entries with tone information matched by timestamp.
    
    Args:
        transcript_threads: Original transcript entries
        emotional_graph: Emotion data points with timestamps
        compliance_result: Full compliance analysis results
        
    Returns:
        Enhanced transcript entries with tone, sentiment_score, and acoustic_arousal
    """
    enriched_threads = []
    
    for entry in transcript_threads:
        # Copy the original entry
        enriched_entry = entry.copy()
        
        # Find and add tone information for this timestamp
        timestamp = entry.get("timestamp", "00:00")
        tone_info = _find_closest_tone(timestamp, emotional_graph)
        
        # Add tone fields
        enriched_entry["tone"] = tone_info["tone"]
        enriched_entry["sentiment_score"] = tone_info["sentiment_score"]
        enriched_entry["acoustic_arousal"] = tone_info["acoustic_arousal"]
        
        # Add speaker-specific sentiment if available
        speaker = entry.get("speaker", "unknown")
        if speaker == "customer":
            enriched_entry["speaker_sentiment"] = compliance_result.get("customer_sentiment", "Neutral")
        elif speaker == "agent":
            enriched_entry["speaker_sentiment"] = compliance_result.get("agent_sentiment", "Professional")
        
        enriched_threads.append(enriched_entry)
    
    return enriched_threads


def build_output_json(
    request_id: str,
    call_timestamp_utc: str,
    processing_start_time: float,
    transcription_result: dict,
    acoustic_segments: list[dict],
    compliance_result: dict,
    time_violation_result: dict,
    client_config: dict,
) -> dict:
    """
    Assemble the complete Vigilant response JSON.

    Args:
        request_id: Unique request identifier
        call_timestamp_utc: Original call timestamp (from metadata or current time)
        processing_start_time: time.time() at start of pipeline
        transcription_result: Output from transcriber.py
        acoustic_segments: Output from audio_processor.py
        compliance_result: Output from compliance_engine.py
        time_violation_result: Output from audio_processor.check_time_violation()
        client_config: The merged client+default configuration dict

    Returns:
        Complete dict matching the Vigilant output JSON schema
    """
    processing_ms = int((time.time() - processing_start_time) * 1000)
    transcript_threads = transcription_result.get("transcript_threads", [])

    # ---- metadata ----
    metadata = {
        "timestamp": call_timestamp_utc,
        "detected_languages": transcription_result.get("detected_languages", ["English"]),
        "processing_time_ms": processing_ms,
        "conversation_complexity": _complexity_from_turns(len(transcript_threads)),
    }

    # ---- config_applied ----
    config_applied = {
        "business_domain": client_config.get("business_domain", "Banking / Debt Recovery"),
        "monitored_products": client_config.get("monitored_products", []),
        "active_policy_set": client_config.get("active_policy_set", "RBI_Compliance_v2.1"),
        "risk_triggers": client_config.get("risk_triggers", []),
    }

    # ---- intelligence_summary ----
    entities = transcription_result.get("entities", [])
    # Ensure each entity has required fields
    cleaned_entities = []
    for i, entity in enumerate(entities):
        cleaned_entities.append({
            "text": entity.get("text", ""),
            "id": entity.get("id", f"entity_{i:02d}"),
            "type": entity.get("type", "UNKNOWN"),
        })

    # Get primary intent with better fallback
    primary_intent = transcription_result.get("primary_intent", "")
    if not primary_intent or primary_intent == "Unknown":
        # Try to infer from conversation_about or category
        conversation_about = transcription_result.get("conversation_about", "")
        category = transcription_result.get("category", "")
        if "fraud" in conversation_about.lower() or "fraud" in category.lower():
            primary_intent = "To report fraudulent activity and seek resolution"
        elif "dispute" in conversation_about.lower() or "dispute" in category.lower():
            primary_intent = "To dispute charges or payments"
        elif "payment" in conversation_about.lower():
            primary_intent = "To discuss payment-related concerns"
        elif "complaint" in conversation_about.lower() or "complaint" in category.lower():
            primary_intent = "To file a complaint and request action"
        else:
            primary_intent = "Customer inquiry or concern requiring assistance"

    # Build intelligence summary - prefer transcription data for conversation details
    # and use compliance summary only for the overall assessment
    
    # Generate conversation summary from transcript if compliance summary is generic/fallback
    compliance_summary = compliance_result.get("summary", "")
    is_fallback_summary = (
        "processing error" in compliance_summary.lower() or 
        "no summary available" in compliance_summary.lower() or
        not compliance_summary
    )
    
    if is_fallback_summary and transcription_result.get("transcript_threads"):
        # Generate summary from transcription data
        threads = transcription_result["transcript_threads"]
        conv_about = transcription_result.get("conversation_about", "general discussion")
        category = transcription_result.get("category", "Customer Service Call")
        
        summary = (
            f"This is a {category.lower()} recording with {len(threads)} conversation turns between an agent and customer. "
            f"The conversation is about {conv_about}. "
        )
        
        # Add intent and key issues
        if primary_intent and primary_intent != "Customer inquiry or concern requiring assistance":
            summary += f"The customer's primary intent is: {primary_intent}. "
        
        key_topics = transcription_result.get("key_topics", [])
        if key_topics and len(key_topics) > 0:
            summary += f"Key topics discussed include: {', '.join(key_topics[:4])}. "
        
        # Add root cause if meaningful
        root_cause = transcription_result.get("root_cause", "")
        if root_cause and "unclear" not in root_cause.lower():
            summary += f"Root cause: {root_cause}. "
        
        # Check for compliance flags from compliance_result
        if not compliance_result.get("is_within_policy", True):
            violations = compliance_result.get("policy_violations", [])
            if violations:
                summary += f"Compliance analysis detected {len(violations)} potential policy violation(s). "
        
        summary += "Detailed analysis and risk assessment have been performed."
    else:
        summary = compliance_summary if compliance_summary else "No summary available."
    
    intelligence_summary = {
        "summary": summary,
        "category": transcription_result.get("category", compliance_result.get("category", "Debt Recovery")),
        "conversation_about": transcription_result.get("conversation_about", "Debt collection call"),
        "primary_intent": primary_intent,
        "key_topics": transcription_result.get("key_topics", []),
        "entities": cleaned_entities,
        "root_cause": transcription_result.get("root_cause", "Reason for contact unclear - requires review"),
    }

    # ---- emotional_and_tonal_analysis ----
    emotional_graph = compliance_result.get("emotional_graph", [])
    
    # If emotional_graph is empty or minimal, generate from acoustic segments and transcript
    if len(emotional_graph) < 2 and acoustic_segments and len(acoustic_segments) > 0:
        emotional_graph = []
        overall_sentiment = compliance_result.get("overall_sentiment", "Neutral")
        
        for seg in acoustic_segments:
            arousal = seg.get("acoustic_arousal", "Low")
            energy = seg.get("energy_score", 0.5)
            
            # Map acoustic arousal + energy + overall sentiment to more accurate tone
            if arousal == "High" and energy > 0.7:
                if "Frustrated" in overall_sentiment or "Angry" in overall_sentiment:
                    tone = "Angry"
                elif "Distressed" in overall_sentiment or "Anxious" in overall_sentiment:
                    tone = "Distressed"
                elif "Aggressive" in overall_sentiment:
                    tone = "Aggressive"
                else:
                    tone = "Intense"
            elif arousal == "High" and energy > 0.5:
                tone = "Frustrated"
            elif arousal == "Medium":
                if "Negative" in overall_sentiment or "Frustrated" in overall_sentiment:
                    tone = "Concerned"
                else:
                    tone = "Neutral"
            else:
                tone = "Calm" if "Positive" in overall_sentiment else "Neutral"
            
            emotional_graph.append({
                "timestamp": seg.get("timestamp", "00:00"),
                "tone": tone,
                "score": energy,
                "acoustic_arousal": arousal
            })
    
    # Merge acoustic arousal if not already in emotional_graph
    if acoustic_segments and emotional_graph:
        acoustic_map = {seg["timestamp"]: seg["acoustic_arousal"] for seg in acoustic_segments}
        for point in emotional_graph:
            if "acoustic_arousal" not in point or not point["acoustic_arousal"]:
                point["acoustic_arousal"] = acoustic_map.get(point.get("timestamp", ""), "Low")

    emotional_and_tonal_analysis = {
        "overall_sentiment": compliance_result.get("overall_sentiment", "Neutral"),
        "emotional_tone": compliance_result.get("emotional_tone", "Neutral"),
        "tone_progression": compliance_result.get("tone_progression", ["Neutral"]),
        "emotional_graph": emotional_graph,
        "emotion_timeline": compliance_result.get(
            "emotion_timeline",
            [
                {"time": "start", "emotion": "neutral"},
                {"time": "middle", "emotion": "neutral"},
                {"time": "end", "emotion": "neutral"},
            ],
        ),
    }

    # ---- compliance_and_risk_audit ----
    policy_violations = compliance_result.get("policy_violations", [])

    # Ensure time violation is included if detected and not already present
    if time_violation_result.get("violation", False):
        existing_ids = {v.get("clause_id") for v in policy_violations}
        if "INTERNAL-TIME-01" not in existing_ids:
            policy_violations.append(
                {
                    "clause_id": "INTERNAL-TIME-01",
                    "rule_name": time_violation_result.get("rule_name", "Operating Hours Compliance"),
                    "description": time_violation_result.get("description", ""),
                    "timestamp": time_violation_result.get("ist_time", "??:??"),
                    "evidence_quote": (
                        f"Call timestamp detected as {time_violation_result.get('ist_time', 'unknown')} IST."
                    ),
                }
            )

    has_violations = len(policy_violations) > 0
    is_within_policy = compliance_result.get("is_within_policy", not has_violations)

    compliance_flags = compliance_result.get("compliance_flags", [])
    if has_violations and not compliance_flags:
        compliance_flags = ["Policy Violation Detected"]

    # Extract comprehensive risk data
    comprehensive_risk = compliance_result.get("comprehensive_risk_assessment", {})
    risk_breakdown = comprehensive_risk.get("breakdown", {})

    compliance_and_risk_audit = {
        "is_within_policy": is_within_policy,
        "compliance_flags": compliance_flags,
        "policy_violations": policy_violations,
        "detected_threats": compliance_result.get("detected_threats", []),
        "risk_scores": {
            "fraud_risk": compliance_result.get("fraud_risk", "low"),
            "escalation_risk": compliance_result.get("escalation_risk", "low"),
            "urgency_level": compliance_result.get("urgency_level", "low"),
            "risk_escalation_score": compliance_result.get("risk_escalation_score", 0),
        },
        "comprehensive_risk_assessment": {
            "total_score": comprehensive_risk.get("total_score", 0),
            "risk_level": comprehensive_risk.get("risk_level", "minimal"),
            "risk_category": comprehensive_risk.get("risk_category", "MINIMAL"),
            "escalation_action": comprehensive_risk.get("escalation_action", "No escalation required"),
            "justification": comprehensive_risk.get("justification", ""),
            "requires_immediate_action": comprehensive_risk.get("requires_immediate_action", False),
            "auto_escalate": comprehensive_risk.get("auto_escalate", False),
            "risk_breakdown": {
                "policy_violations": risk_breakdown.get("policy_violations", 0),
                "emotional_intensity": risk_breakdown.get("emotional_intensity", 0),
                "threat_level": risk_breakdown.get("threat_level", 0),
                "agent_conduct": risk_breakdown.get("agent_conduct", 0),
                "time_violation": risk_breakdown.get("time_violation", 0),
                "prohibited_phrases": risk_breakdown.get("prohibited_phrases", 0),
            }
        }
    }

    # ---- performance_and_outcomes ----
    outcome_classification = compliance_result.get("outcome_classification", {})
    agent_performance_assessment = compliance_result.get("agent_performance_assessment", {})
    
    performance_and_outcomes = {
        "agent_performance": {
            "overall_quality_score": compliance_result.get("agent_quality_score", 50),
            "performance_level": compliance_result.get("performance_level", "satisfactory"),
            "performance_category": agent_performance_assessment.get("performance_category", "SATISFACTORY"),
            "component_scores": {
                "communication_skills": agent_performance_assessment.get("breakdown", {}).get("communication_skills", 18),
                "politeness": agent_performance_assessment.get("breakdown", {}).get("politeness", 6),
                "empathy": agent_performance_assessment.get("breakdown", {}).get("empathy", 8),
                "professionalism": agent_performance_assessment.get("breakdown", {}).get("professionalism", 12),
                "problem_resolution": agent_performance_assessment.get("breakdown", {}).get("problem_resolution", 6),
                "compliance_adherence": agent_performance_assessment.get("breakdown", {}).get("compliance_adherence", 5),
                "penalties": agent_performance_assessment.get("breakdown", {}).get("penalties", 0)
            },
            "qualitative_ratings": {
                "politeness": compliance_result.get("agent_politeness", "fair"),
                "empathy": compliance_result.get("agent_empathy", "medium"),
                "professionalism": compliance_result.get("agent_professionalism", "fair")
            },
            "strengths": compliance_result.get("agent_strengths", []),
            "weaknesses": compliance_result.get("agent_weaknesses", []),
            "specific_feedback": agent_performance_assessment.get("specific_feedback", ""),
            "requires_coaching": compliance_result.get("requires_coaching", False),
            "requires_disciplinary_action": compliance_result.get("requires_disciplinary_action", False),
            "commendation_worthy": compliance_result.get("commendation_worthy", False)
        },
        "training_and_development": {
            "training_priority": compliance_result.get("training_priority", "none"),
            "training_recommendations": compliance_result.get("training_recommendations", []),
        },
        "call_outcome": {
            "primary_outcome": compliance_result.get("call_outcome_prediction", "Pending"),
            "outcome_category": outcome_classification.get("outcome_category", "PENDING"),
            "confidence_score": compliance_result.get("outcome_confidence", 0.0),
            "outcome_reasoning": compliance_result.get("outcome_reasoning", ""),
            "secondary_outcomes": outcome_classification.get("secondary_outcomes", []),
        },
        "follow_up_actions": {
            "next_action": compliance_result.get("next_action", "Review manually."),
            "requires_follow_up": compliance_result.get("requires_follow_up", False),
            "recommended_action": compliance_result.get("recommended_action", "Review manually."),
        },
        "customer_indicators": {
            "satisfaction_indicator": compliance_result.get("customer_satisfaction_indicator", "neutral"),
            "repeat_complaint_detected": compliance_result.get("repeat_complaint_detected", False),
        },
        "final_status": compliance_result.get("final_status", "Pending Review"),
    }

    # ---- extensions (for custom insight types) ----
    extensions = {
        "custom_insights": {},
        "plugin_data": {},
        "reserved_for_future_use": {}
    }
    
    # If client config defines custom insights, include their configuration
    if client_config.get("custom_insights"):
        extensions["custom_insights"] = {
            "configured": list(client_config.get("custom_insights", {}).keys()),
            "note": "Custom insight processing can be implemented as plugins. "
                    "Add processors in json_builder.py to populate results here."
        }
    
    # Include any custom extensions from client config
    if client_config.get("extensions"):
        extensions["client_extensions"] = client_config.get("extensions")

    # ---- enrich transcript_threads with tone information ----
    enriched_transcript_threads = _enrich_transcript_with_tones(
        transcript_threads,
        emotional_graph,
        compliance_result
    )

    # ---- assemble final output ----
    return {
        "request_id": request_id,
        "metadata": metadata,
        "config_applied": config_applied,
        "intelligence_summary": intelligence_summary,
        "emotional_and_tonal_analysis": emotional_and_tonal_analysis,
        "compliance_and_risk_audit": compliance_and_risk_audit,
        "transcript_threads": enriched_transcript_threads,
        "performance_and_outcomes": performance_and_outcomes,
        "extensions": extensions,
    }
