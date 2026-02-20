"""
Compliance Engine – Agentic LLM reasoning using Gemini 1.5 Pro.
Takes transcript, acoustic data, retrieved RAG clauses and client config,
and produces the full emotional + compliance audit analysis as JSON.
"""
from __future__ import annotations

import json
import re
from typing import Optional

import google.generativeai as genai

from services.risk_scoring import RiskScoreCalculator, CallOutcomeClassifier
from services.agent_performance import AgentPerformanceCalculator


# ---------------------------------------------------------------------------
# System prompt for the compliance reasoner
# ---------------------------------------------------------------------------

COMPLIANCE_PROMPT_TEMPLATE = """
You are a senior RBI (Reserve Bank of India) compliance auditor AI called "Vigilant".
You specialize in auditing debt recovery calls for policy violations, emotional tone,
and agent conduct.

You are given:
1. TRANSCRIPT: A diarized call transcript (agent vs. customer turns with timestamps)
2. ACOUSTIC DATA: Per-segment audio emotion data (energy, pitch, arousal level)
3. POLICY CLAUSES: Relevant RBI/NBFC policy clauses retrieved from compliance database
4. CLIENT CONFIG: Active risk triggers and rules for this bank
5. CALL TIMESTAMP: When this call was placed

---

TRANSCRIPT:
{transcript}

---

ACOUSTIC DATA:
{acoustic}

---

RELEVANT POLICY CLAUSES:
{clauses}

---

CLIENT CONFIG:
{config}

---

CALL TIMESTAMP (UTC): {timestamp}
CALL TIMESTAMP (IST): {ist_time}
TIME VIOLATION DETECTED: {time_violation}
{time_violation_detail}

---

Your task: Produce a comprehensive compliance audit. Return ONLY valid JSON 
(no markdown, no explanation).

**CRITICAL INSTRUCTIONS FOR SENTIMENT & EMOTIONAL ANALYSIS:**
- Analyze OVERALL_SENTIMENT by examining the entire conversation flow, language intensity, and acoustic arousal levels
- Determine EMOTIONAL_TONE by combining verbal cues (word choice, phrasing, complaints) with acoustic data (High/Medium/Low arousal)
- Consider customer language: complaints, frustration indicators, urgency, anxiety, anger, distress, calmness
- Consider agent language: empathy, professionalism, reassurance, defensiveness, aggression
- Use acoustic_arousal from ACOUSTIC DATA to validate and refine your sentiment assessment
- OVERALL_SENTIMENT options: "Positive", "Neutral", "Negative", "Frustrated", "Anxious", "Aggressive", "Distressed", "High Tension"
- EMOTIONAL_TONE options: "Calm", "Neutral", "Concerned", "Frustrated", "Angry", "Distressed", "Aggressive", "Threatening", "Anxious", "Panicked"

The JSON must have EXACTLY these top-level keys:

{{
  "summary": "A comprehensive 5-7 sentence summary covering: (1) the nature and context of the call, (2) key issues or concerns raised by the customer, (3) how the agent responded or handled the situation, (4) any critical moments or turning points in the conversation, (5) apparent outcome or resolution status, and (6) overall assessment of the interaction quality and compliance stance.",
  "category": "call category e.g. Fraud Complaint / Debt Recovery",
  "overall_sentiment": "e.g. Negative / High Tension / Distressed / Frustrated (Must reflect the actual emotional state from transcript and acoustic data)",
  "emotional_tone": "e.g. Distressed / Aggressive / Anxious / Threatening (Must match the conversation intensity and acoustic arousal)",
  "tone_progression": ["ordered list tracking tone evolution from start to end"],
  "emotional_graph": [
    {{
      "timestamp": "MM:SS",
      "tone": "Neutral|Frustrated|Angry|Threatening|Distressed|Aggressive",
      "score": 0.0,
      "acoustic_arousal": "Low|Medium|High"
    }}
  ],
  "emotion_timeline": [
    {{"time": "start", "emotion": "neutral"}},
    {{"time": "middle", "emotion": "frustrated"}},
    {{"time": "end", "emotion": "angry"}}
  ],
  "is_within_policy": false,
  "compliance_flags": ["list of high-level flag names"],
  "policy_violations": [
    {{
      "clause_id": "RBI-REC-04",
      "rule_name": "No Physical Threats",
      "description": "explanation",
      "timestamp": "MM:SS",
      "evidence_quote": "exact agent quote from transcript"
    }}
  ],
  "detected_threats": ["plain English threat descriptions"],
  "fraud_risk": "low|medium|high",
  "escalation_risk": "low|medium|high",
  "urgency_level": "low|medium|high",
  "risk_escalation_score": 0,
  "agent_politeness": "excellent|good|fair|poor|unacceptable",
  "agent_empathy": "high|medium|low|none",
  "agent_professionalism": "excellent|good|fair|poor|unacceptable",
  "agent_quality_score": 0,
  "customer_sentiment": "Positive|Neutral|Negative|Frustrated|Anxious|Angry|Distressed|Satisfied",
  "agent_sentiment": "Professional|Empathetic|Neutral|Defensive|Aggressive|Impatient|Courteous",
  "call_outcome_prediction": "e.g. Escalation Likely / Legal Dispute",
  "repeat_complaint_detected": false,
  "final_status": "e.g. Escalated to Compliance Manager",
  "recommended_action": "specific action for compliance team"
}}

Rules:
- **SENTIMENT & EMOTION ANALYSIS:**
  * Carefully read the TRANSCRIPT and identify emotional indicators in customer language (frustration, anxiety, anger, distress)
  * Cross-reference with ACOUSTIC DATA arousal levels (High arousal = intense emotions)
  * overall_sentiment must accurately reflect the conversation's emotional state
  * emotional_tone must match the intensity level (calm vs concerned vs distressed vs aggressive)
  * tone_progression should show how emotions evolved throughout the call
  * emotional_graph must show emotional changes at key moments in the conversation
  * customer_sentiment: Analyze ONLY customer utterances for their emotional state (Positive if satisfied/calm, Negative if upset, Frustrated if annoyed, Anxious if worried, Angry if hostile, Distressed if panicked)
  * agent_sentiment: Analyze ONLY agent utterances for their emotional demeanor (Professional if neutral/proper, Empathetic if showing understanding, Courteous if polite, Defensive if justifying, Aggressive if confrontational, Impatient if rushed)
- emotional_graph must have one entry per ~30 seconds of conversation (use transcript timestamps)
- Each emotional_graph entry must combine: (1) verbal tone from transcript analysis, (2) acoustic_arousal from ACOUSTIC DATA
- For emotion_timeline: analyze start (opening), middle (main issue discussion), end (resolution/outcome)
- policy_violations must cite real clause_ids from the POLICY CLAUSES section provided
- If time violation was detected, add it as a policy_violation with clause_id INTERNAL-TIME-01
- risk_escalation_score: 0–100 integer reflecting combined risk (consider violations, arousal, threats)
- agent_quality_score: 0–100 (100 = perfect agent, 0 = completely non-compliant)
- Be thorough — a missed violation is worse than a false positive in compliance auditing
- evidence_quote must be the exact agent utterance from the transcript
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_transcript(transcript_threads: list[dict]) -> str:
    lines = []
    for t in transcript_threads:
        speaker = t.get("speaker", "unknown").upper()
        ts = t.get("timestamp", "??:??")
        msg = t.get("message", "")
        lines.append(f"[{ts}] {speaker}: {msg}")
    return "\n".join(lines)


def _format_acoustic(acoustic_segments: list[dict]) -> str:
    lines = []
    for seg in acoustic_segments:
        lines.append(
            f"[{seg['timestamp']}] Energy={seg['energy_score']:.2f} "
            f"Pitch={seg['pitch_hz']:.0f}Hz ZCR={seg['zcr']:.4f} "
            f"Arousal={seg['acoustic_arousal']}"
        )
    return "\n".join(lines) if lines else "No acoustic data available."


def _format_clauses(clauses: list[dict]) -> str:
    if not clauses:
        return "No specific clauses retrieved. Apply general RBI recovery guidelines."
    lines = []
    for c in clauses:
        lines.append(
            f"[{c['clause_id']}] {c['rule_name']}\n  {c['description'][:200]}"
        )
    return "\n".join(lines)


def _format_config_context(config: dict, validated_config=None) -> str:
    """Format client config with emphasis on active rules and triggers."""
    lines = [
        f"ORGANIZATION: {config.get('organization_name', 'N/A')}",
        f"BUSINESS DOMAIN: {config.get('business_domain', 'N/A')}",
        f"POLICY SET: {config.get('active_policy_set', 'N/A')}",
        f"\nMONITORED PRODUCTS: {', '.join(config.get('monitored_products', []))}",
        f"\nRISK TRIGGERS (these are compliance violations):",
    ]
    
    for trigger in config.get('risk_triggers', []):
        lines.append(f"  - {trigger}")
    
    custom_rules = config.get('custom_rules', [])
    if custom_rules:
        lines.append(f"\nCUSTOM RULES (critical for compliance):")
        for rule in custom_rules:
            lines.append(
                f"  - [{rule.get('rule_id', 'N/A')}] {rule.get('rule_name', 'N/A')} "
                f"(Severity: {rule.get('severity', 'high')})"
            )
            lines.append(f"    {rule.get('description', 'N/A')}")
    
    prohibited = config.get('prohibited_phrases', [])
    if prohibited:
        lines.append(f"\nPROHIBITED PHRASES (automatic violations if detected):")
        for phrase in prohibited[:10]:  # Show first 10
            lines.append(f"  - \"{phrase}\"")
        if len(prohibited) > 10:
            lines.append(f"  ... and {len(prohibited) - 10} more")
    
    # Add agent quality thresholds
    thresholds = config.get('agent_quality_thresholds', {})
    if thresholds:
        lines.append(f"\nAGENT QUALITY REQUIREMENTS:")
        lines.append(f"  - Minimum Politeness: {thresholds.get('minimum_politeness_score', 60)}")
        lines.append(f"  - Minimum Empathy: {thresholds.get('minimum_empathy_score', 50)}")
        lines.append(f"  - Minimum Professionalism: {thresholds.get('minimum_professionalism_score', 70)}")
        lines.append(f"  - Minimum Overall: {thresholds.get('minimum_overall_score', 60)}")
    
    return "\n".join(lines)


def _check_prohibited_phrases(transcript_threads: list[dict], prohibited_phrases: list[str]) -> list[dict]:
    """
    Check if any prohibited phrases appear in agent utterances.
    
    Returns:
        List of detected violations with details
    """
    detected_violations = []
    
    for thread in transcript_threads:
        speaker = thread.get("speaker", "").lower()
        if speaker != "agent":
            continue
            
        message = thread.get("message", "").lower()
        timestamp = thread.get("timestamp", "??:??")
        
        for phrase in prohibited_phrases:
            if phrase.lower() in message:
                detected_violations.append({
                    "timestamp": timestamp,
                    "prohibited_phrase": phrase,
                    "context": thread.get("message", ""),
                    "severity": "critical"
                })
                print(f"[ComplianceEngine] PROHIBITED PHRASE DETECTED: '{phrase}' at {timestamp}")
    
    return detected_violations


def _extract_json(text: str) -> dict:
    """Strip markdown fences and parse JSON."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"```$", "", text).strip()
    return json.loads(text)


def _build_fallback_compliance(transcript_threads=None, acoustic_segments=None) -> dict:
    """Build fallback compliance result when AI analysis fails."""
    
    # Try to generate a basic summary from transcript
    summary = "Analysis could not be completed due to a processing error. Manual review recommended."
    category = "Unclassified - Requires Review"
    
    if transcript_threads and len(transcript_threads) > 0:
        # Generate basic summary from transcript
        agent_msgs = [t.get('message', '') for t in transcript_threads if t.get('speaker', '').lower() == 'agent']
        customer_msgs = [t.get('message', '') for t in transcript_threads if t.get('speaker', '').lower() == 'customer']
        
        if agent_msgs and customer_msgs:
            summary = (
                f"This is a call interaction between an agent and customer with {len(transcript_threads)} conversation turns. "
                f"The conversation involves discussion between the agent and customer. "
                f"Automated compliance analysis could not be completed. Manual review is recommended to assess policy compliance, "
                f"emotional tone, and agent conduct."
            )
            
            # Try to infer category from content
            all_text = ' '.join(agent_msgs + customer_msgs).lower()
            if 'fraud' in all_text or 'scam' in all_text:
                category = "Fraud Complaint"
            elif 'payment' in all_text or 'due' in all_text or 'loan' in all_text:
                category = "Debt Recovery"
            elif 'dispute' in all_text or 'charge' in all_text:
                category = "Payment Dispute"
            elif 'complaint' in all_text:
                category = "Customer Complaint"
    
    return {
        "summary": summary,
        "category": category,
        "overall_sentiment": "Neutral",
        "emotional_tone": "Neutral",
        "tone_progression": ["Neutral"],
        "emotional_graph": [
            {"timestamp": "00:00", "tone": "Neutral", "score": 0.5, "acoustic_arousal": "Low"}
        ],
        "emotion_timeline": [
            {"time": "start", "emotion": "neutral"},
            {"time": "middle", "emotion": "neutral"},
            {"time": "end", "emotion": "neutral"},
        ],
        "is_within_policy": True,
        "compliance_flags": [],
        "policy_violations": [],
        "detected_threats": [],
        "fraud_risk": "low",
        "escalation_risk": "low",
        "urgency_level": "low",
        "risk_escalation_score": 0,
        "agent_politeness": "fair",
        "agent_empathy": "medium",
        "agent_professionalism": "fair",
        "agent_quality_score": 50,
        "call_outcome_prediction": "Resolved",
        "repeat_complaint_detected": False,
        "final_status": "Pending Review",
        "recommended_action": "Manual review required.",
    }


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def run_compliance_analysis(
    transcript_threads: list[dict],
    acoustic_segments: list[dict],
    retrieved_clauses: list[dict],
    client_config: dict,
    call_timestamp_utc: str,
    time_violation_result: dict,
    api_key: str,
) -> dict:
    """
    Run the agentic LLM compliance reasoner with config-aware analysis.

    Returns a dict with all compliance, emotional, and performance fields.
    """
    from models.client_config import ConfigManager, ClientConfig
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name="models/gemini-2.5-pro")

    # Validate config and create ConfigManager instance for utilities
    try:
        validated_config = ConfigManager.validate_config(client_config)
    except Exception as e:
        print(f"[ComplianceEngine] Config validation warning: {e}")
        validated_config = None

    # Format inputs
    transcript_text = _format_transcript(transcript_threads)
    acoustic_text = _format_acoustic(acoustic_segments)
    clauses_text = _format_clauses(retrieved_clauses)
    
    # Enhance config text with active triggers and rules
    config_summary = _format_config_context(client_config, validated_config)
    
    # Pre-analyze for prohibited phrases
    prohibited_phrases_detected = _check_prohibited_phrases(
        transcript_threads, 
        client_config.get("prohibited_phrases", [])
    )
    
    # Format prohibited phrases for prompt
    prohibited_context = ""
    if prohibited_phrases_detected:
        prohibited_context = "\n\n⚠️ PROHIBITED PHRASES DETECTED (automatic critical violations):\n"
        for violation in prohibited_phrases_detected:
            prohibited_context += (
                f"  - [{violation['timestamp']}] \"{violation['prohibited_phrase']}\"\n"
                f"    Context: \"{violation['context'][:100]}...\"\n"
            )

    ist_time = time_violation_result.get("ist_time", "unknown")
    time_viol = time_violation_result.get("violation", False)
    time_viol_detail = (
        f"TIME VIOLATION DETAIL: {time_violation_result['description']}"
        if time_viol
        else ""
    )

    prompt = COMPLIANCE_PROMPT_TEMPLATE.format(
        transcript=transcript_text,
        acoustic=acoustic_text,
        clauses=clauses_text,
        config=config_summary + prohibited_context,  # Use enhanced config with prohibited detections
        timestamp=call_timestamp_utc,
        ist_time=ist_time,
        time_violation="YES" if time_viol else "NO",
        time_violation_detail=time_viol_detail,
    )

    try:
        print("[ComplianceEngine] Running Gemini compliance analysis...")
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.05,
            ),
        )
        result = _extract_json(response.text)
        
        # Post-process: Add prohibited phrase violations if detected
        if prohibited_phrases_detected:
            existing_violations = result.get('policy_violations', [])
            for prohibited_violation in prohibited_phrases_detected:
                # Add as a policy violation
                existing_violations.append({
                    "clause_id": "CLIENT-PROHIBITED-PHRASE",
                    "rule_name": "Prohibited Language Used",
                    "description": f"Agent used prohibited phrase: '{prohibited_violation['prohibited_phrase']}'",
                    "timestamp": prohibited_violation['timestamp'],
                    "evidence_quote": prohibited_violation['context'],
                    "severity": "critical"
                })
            result['policy_violations'] = existing_violations
            result['is_within_policy'] = False
            
            # Ensure high risk score
            current_score = result.get('risk_escalation_score', 0)
            result['risk_escalation_score'] = max(current_score, 85)  # Minimum 85 for prohibited phrases
            
            # Add to compliance flags
            compliance_flags = result.get('compliance_flags', [])
            if "Prohibited Language" not in compliance_flags:
                compliance_flags.append("Prohibited Language")
            result['compliance_flags'] = compliance_flags
            
            print(f"[ComplianceEngine] Added {len(prohibited_phrases_detected)} prohibited phrase violations")
        
        # ---- Calculate Comprehensive Risk Score ----
        comprehensive_risk = RiskScoreCalculator.calculate_comprehensive_score(
            policy_violations=result.get('policy_violations', []),
            emotional_tone=result.get('emotional_tone', 'Neutral'),
            detected_threats=result.get('detected_threats', []),
            agent_conduct={
                'politeness': result.get('agent_politeness', 'fair'),
                'professionalism': result.get('agent_professionalism', 'fair')
            },
            time_violation=time_viol,
            prohibited_phrases_detected=len(prohibited_phrases_detected) if prohibited_phrases_detected else 0,
            acoustic_arousal_high_count=sum(
                1 for seg in acoustic_segments if seg.get('arousal', '').lower() == 'high'
            ),
            client_config=client_config
        )
        
        # Merge comprehensive risk data into result
        result['comprehensive_risk_assessment'] = comprehensive_risk
        result['risk_escalation_score'] = comprehensive_risk['total_score']
        result['escalation_risk'] = comprehensive_risk['risk_level']
        result['escalation_action'] = comprehensive_risk['escalation_action']
        result['risk_breakdown'] = comprehensive_risk['breakdown']
        result['requires_immediate_action'] = comprehensive_risk['requires_immediate_action']
        result['auto_escalate'] = comprehensive_risk['auto_escalate']
        
        print(f"[ComplianceEngine] Comprehensive Risk Score: {comprehensive_risk['total_score']}/100 ({comprehensive_risk['risk_level']})")
        
        # ---- Classify Call Outcome ----
        outcome_classification = CallOutcomeClassifier.classify_outcome(
            compliance_result=result,
            transcript_threads=transcript_threads,
            risk_score=comprehensive_risk['total_score']
        )
        
        # Merge outcome classification into result
        result['outcome_classification'] = outcome_classification
        result['call_outcome_prediction'] = outcome_classification['primary_outcome']
        result['outcome_confidence'] = outcome_classification['confidence_score']
        result['outcome_reasoning'] = outcome_classification['outcome_reasoning']
        result['next_action'] = outcome_classification['next_action']
        result['urgency_level'] = outcome_classification['urgency_level']
        result['requires_follow_up'] = outcome_classification['requires_follow_up']
        result['customer_satisfaction_indicator'] = outcome_classification['customer_satisfaction_indicator']
        
        print(f"[ComplianceEngine] Call Outcome: {outcome_classification['primary_outcome']} (confidence: {outcome_classification['confidence_score']})")
        
        # ---- Calculate Agent Performance Score ----
        agent_performance = AgentPerformanceCalculator.calculate_performance_score(
            politeness=result.get('agent_politeness', 'fair'),
            empathy=result.get('agent_empathy', 'medium'),
            professionalism=result.get('agent_professionalism', 'fair'),
            policy_violations=result.get('policy_violations', []),
            detected_threats=result.get('detected_threats', []),
            call_outcome=outcome_classification['primary_outcome'],
            prohibited_phrases_detected=len(prohibited_phrases_detected) if prohibited_phrases_detected else 0,
            time_violation=time_viol,
            transcript_threads=transcript_threads,
            emotional_tone=result.get('emotional_tone', 'Neutral')
        )
        
        # Merge agent performance data into result
        result['agent_performance_assessment'] = agent_performance
        result['agent_quality_score'] = agent_performance['total_score']
        result['performance_level'] = agent_performance['performance_level']
        result['agent_strengths'] = agent_performance['strengths']
        result['agent_weaknesses'] = [w.value for w in agent_performance['weaknesses']]
        result['training_priority'] = agent_performance['training_priority']
        result['training_recommendations'] = agent_performance['training_recommendations']
        result['requires_coaching'] = agent_performance['requires_coaching']
        result['requires_disciplinary_action'] = agent_performance['requires_disciplinary_action']
        result['commendation_worthy'] = agent_performance['commendation_worthy']
        
        print(f"[ComplianceEngine] Agent Performance: {agent_performance['total_score']}/100 ({agent_performance['performance_level']})")
        
        print(
            f"[ComplianceEngine] Done. Violations: {len(result.get('policy_violations', []))} | "
            f"Risk Score: {comprehensive_risk['total_score']}/100 | "
            f"Outcome: {outcome_classification['primary_outcome']} | "
            f"Agent Score: {agent_performance['total_score']}/100"
        )
        return result
    except json.JSONDecodeError as exc:
        print(f"[ComplianceEngine] JSON parse error: {exc}")
        return _build_fallback_compliance(transcript_threads, acoustic_segments)
    except Exception as exc:
        print(f"[ComplianceEngine] ERROR: {exc}")
        return _build_fallback_compliance(transcript_threads, acoustic_segments)
