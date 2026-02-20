# Risk Scoring and Call Outcome Classification System

## Overview

The Vigilant API now includes a comprehensive, multi-factor risk assessment and outcome classification system that provides detailed, structured analysis of every call. This system replaces simplistic single-number scoring with a sophisticated breakdown of risk components and outcome predictions.

## Key Features

### ✅ Multi-Factor Risk Scoring
- **Component-based calculation**: Policy violations, emotional intensity, threat detection, agent conduct, timing violations, prohibited phrases
- **Weighted scoring**: Each component contributes specific points based on severity
- **Risk breakdown**: Detailed view of what drives the total risk score
- **Automatic escalation**: Configurable thresholds trigger immediate action

### ✅ Structured Call Outcome Classification
- **12 distinct outcome categories**: Resolved, Escalated, Dropped, Legal Dispute, etc.
- **Confidence scoring**: AI provides confidence level (0-1) for each classification
- **Secondary outcomes**: Multi-label capability for complex scenarios
- **Customer satisfaction indicators**: Estimates customer sentiment based on outcome

### ✅ Actionable Intelligence
- **Next action recommendations**: Specific guidance on what should happen next
- **Escalation action mapping**: From "No escalation" to "Executive attention needed"
- **Urgency classification**: Critical, High, Medium, Low
- **Follow-up tracking**: Boolean flag indicating if follow-up is required

---

## Architecture

### 1. Risk Score Calculator (`RiskScoreCalculator`)

#### Component Breakdown

| Component | Max Points | Description |
|-----------|------------|-------------|
| **Policy Violations** | 40 | Critical (30), High (20), Medium (10), Low (5) per violation |
| **Emotional Intensity** | 25 | Based on tone (threatening, aggressive, distressed, angry, frustrated) + acoustic arousal |
| **Threat Detection** | 25 | Explicit threats (25), implied threats (15), intimidation (10) |
| **Agent Conduct** | 25 | Negative points for poor conduct, unprofessionalism |
| **Time Violation** | 15 | Call placed outside permitted hours |
| **Prohibited Phrases** | 60 | 30 points per prohibited phrase detected (max 60) |

**Total Score Range**: 0-100 (capped at 100)

#### Risk Level Classification

| Score Range | Risk Level | Description |
|-------------|------------|-------------|
| 0-20 | **Minimal** | No significant concerns |
| 21-40 | **Low** | Minor issues requiring monitoring |
| 41-60 | **Moderate** | Requires supervisor review |
| 61-80 | **High** | Escalation to management needed |
| 81-100 | **Critical** | Immediate intervention required |

#### Escalation Action Mapping

| Risk Score | Action |
|------------|--------|
| < 35 | No escalation required |
| 35-49 | Supervisor review recommended |
| 50-64 | Manager review required |
| 65-79 | Escalate to compliance team |
| 80-89 | Legal team review required |
| 90+ | Executive level attention needed |

**Special Overrides**:
- Any prohibited phrase detection → Immediate intervention
- Critical violation → Immediate intervention
- Auto-escalate based on client config thresholds

#### Example Risk Calculation

```json
{
  "total_score": 73.0,
  "risk_level": "high",
  "risk_category": "HIGH",
  "escalation_action": "Escalate to compliance team",
  "justification": "Risk score 73/100 due to: 2 high-severity violation(s), 1 threat(s) detected, high emotional intensity",
  "requires_immediate_action": false,
  "auto_escalate": false,
  "breakdown": {
    "policy_violations": 40,
    "emotional_intensity": 20,
    "threat_level": 15,
    "agent_conduct": 0,
    "time_violation": 0,
    "prohibited_phrases": 0
  }
}
```

---

### 2. Call Outcome Classifier (`CallOutcomeClassifier`)

#### Outcome Categories

| Outcome | Code | Description |
|---------|------|-------------|
| **Resolved** | `RESOLVED` | Issue successfully resolved during call |
| **Customer Satisfied** | `CUSTOMER_SATISFIED` | Positive resolution with clear satisfaction |
| **Customer Dissatisfied** | `CUSTOMER_DISSATISFIED` | Resolution attempted but customer unhappy |
| **Escalated** | `ESCALATED` | Escalated to supervisor/manager |
| **Transferred** | `TRANSFERRED` | Call transferred to another department |
| **Legal Dispute** | `LEGAL_DISPUTE` | Customer mentioned legal action |
| **Unresolved Complaint** | `UNRESOLVED_COMPLAINT` | Customer concerns not addressed |
| **Callback Required** | `CALLBACK_REQUIRED` | Agent committed to follow-up |
| **Follow-up Needed** | `FOLLOW_UP_NEEDED` | Requires additional action |
| **Pending** | `PENDING` | Under review or awaiting resolution |
| **Dropped** | `DROPPED` | Call ended abruptly without resolution |
| **No Resolution** | `NO_RESOLUTION` | No satisfactory outcome achieved |

#### Classification Logic

The classifier analyzes multiple signals:

1. **Policy violations**: Critical violations → Escalated
2. **Threats detected**: → Legal Dispute or Escalated
3. **Conversation ending keywords**:
   - Resolution: "resolved", "solved", "fixed", "thank", "satisfied"
   - Callback: "call back", "follow up", "get back"
   - Transfer: "transfer", "supervisor", "manager"
   - Drop: "disconnect", "hung up", "dropped"
4. **Emotional tone**: Angry/aggressive → Unresolved Complaint
5. **Risk score**: Score ≥ 80 → Escalated or Legal Dispute
6. **Final status from LLM**: "pending", "review" → Pending

#### Confidence Scoring

Confidence ranges from 0.0 to 1.0:
- **0.95**: Prohibited phrases or critical violations detected
- **0.90**: High risk or threats detected
- **0.85**: Clear resolution/transfer/callback keywords found
- **0.80**: Strong emotional indicators
- **0.75**: Time violations or pending status
- **0.70**: Policy compliance with low risk
- **0.60-0.65**: Default classification based on partial signals

#### Secondary Outcomes

Multi-label capability provides context:
- `Resolved` → may also include `Customer Satisfied` or `Follow-up Needed`
- `Escalated` → may include `Unresolved Complaint` or `Legal Dispute`
- `Pending` → may include `Callback Required` or `Follow-up Needed`

#### Next Action Recommendations

Each outcome maps to specific guidance:

| Outcome | Next Action |
|---------|-------------|
| **Resolved** | Close case; no further action unless customer re-contacts |
| **Customer Satisfied** | Close case successfully; use as positive training example |
| **Escalated** | Escalate to supervisor for review and appropriate action |
| **Legal Dispute** | Forward to legal department immediately; document all evidence |
| **Callback Required** | Schedule callback within 24-48 hours; ensure follow-through |
| **Unresolved Complaint** | Re-engage customer with senior agent; offer resolution options |
| **Dropped** | Attempt reconnection; investigate reason for call termination |

#### Example Outcome Classification

```json
{
  "primary_outcome": "Escalated",
  "outcome_category": "ESCALATED",
  "confidence_score": 0.9,
  "outcome_reasoning": "2 policy violation(s) detected. Threats detected in conversation. Requires management review",
  "secondary_outcomes": [
    "Unresolved Complaint",
    "Legal Dispute"
  ],
  "next_action": "Escalate to supervisor for review and appropriate action",
  "urgency_level": "high",
  "requires_follow_up": false,
  "customer_satisfaction_indicator": "highly_dissatisfied"
}
```

---

## API Response Structure

### Enhanced `compliance_and_risk_audit` Section

```json
{
  "compliance_and_risk_audit": {
    "is_within_policy": false,
    "compliance_flags": ["Policy Violation Detected", "Prohibited Language"],
    "policy_violations": [
      {
        "clause_id": "RBI-DBRF-2.12",
        "rule_name": "Inappropriate Language",
        "description": "Agent used threatening language",
        "timestamp": "00:45",
        "evidence_quote": "You better pay now or else...",
        "severity": "high"
      }
    ],
    "detected_threats": ["Implied consequences for non-payment"],
    "risk_scores": {
      "fraud_risk": "low",
      "escalation_risk": "high",
      "urgency_level": "high",
      "risk_escalation_score": 73.0
    },
    "comprehensive_risk_assessment": {
      "total_score": 73.0,
      "risk_level": "high",
      "risk_category": "HIGH",
      "escalation_action": "Escalate to compliance team",
      "justification": "Risk score 73/100 due to: 2 high-severity violation(s), 1 threat(s) detected, high emotional intensity",
      "requires_immediate_action": false,
      "auto_escalate": false,
      "risk_breakdown": {
        "policy_violations": 40,
        "emotional_intensity": 20,
        "threat_level": 15,
        "agent_conduct": 0,
        "time_violation": 0,
        "prohibited_phrases": 0
      }
    }
  }
}
```

### Enhanced `performance_and_outcomes` Section

```json
{
  "performance_and_outcomes": {
    "agent_performance": {
      "politeness": "poor",
      "empathy": "low",
      "professionalism": "poor",
      "overall_quality_score": 35
    },
    "call_outcome": {
      "primary_outcome": "Escalated",
      "outcome_category": "ESCALATED",
      "confidence_score": 0.9,
      "outcome_reasoning": "2 policy violation(s) detected. Threats detected in conversation. Requires management review",
      "secondary_outcomes": ["Unresolved Complaint", "Legal Dispute"]
    },
    "follow_up_actions": {
      "next_action": "Escalate to supervisor for review and appropriate action",
      "requires_follow_up": false,
      "recommended_action": "Immediate supervisor review and potential agent retraining"
    },
    "customer_indicators": {
      "satisfaction_indicator": "highly_dissatisfied",
      "repeat_complaint_detected": false
    },
    "final_status": "Escalated to Management"
  }
}
```

---

## Configuration Integration

### Risk Scoring Configuration

From `client_config.json`:

```json
{
  "risk_scoring": {
    "weights": {
      "policy_violations": 0.4,
      "emotional_tone": 0.3,
      "threats": 0.3
    },
    "thresholds": {
      "base_threshold": 50,
      "critical_threshold": 80
    }
  },
  "auto_escalate_on_critical": true
}
```

**How it's used**:
- `weights`: Influences relative importance (currently informational; component scoring is hardcoded in `RiskComponents`)
- `critical_threshold`: Defines when `auto_escalate` triggers (default: 80)
- `auto_escalate_on_critical`: Master switch for automatic escalation

---

## Implementation Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     POST /analyze                               │
│                    (audio + optional config)                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                ┌────────────────────────┐
                │  Transcription Service │
                │   (Gemini 2.5 Flash)   │
                └────────────┬───────────┘
                             │
                             ▼
                ┌────────────────────────┐
                │   Audio Processor      │
                │  (Acoustic Features)   │
                └────────────┬───────────┘
                             │
                             ▼
                ┌────────────────────────┐
                │    RAG Engine          │
                │   (ChromaDB + RAG)     │
                └────────────┬───────────┘
                             │
                             ▼
                ┌────────────────────────────────────────┐
                │      Compliance Engine                 │
                │     (Gemini 2.5 Pro LLM)               │
                │  - Policy violation detection          │
                │  - Emotional analysis                  │
                │  - Agent conduct assessment            │
                └────────────┬───────────────────────────┘
                             │
                             ▼
                ┌────────────────────────────────────────┐
                │   Risk Score Calculator                │
                │   (Multi-factor scoring)               │
                │  ┌─────────────────────────┐           │
                │  │ Component Scores:       │           │
                │  │ - Policy violations: 40 │           │
                │  │ - Emotional: 20         │           │
                │  │ - Threats: 15           │           │
                │  │ - Agent conduct: 0      │           │
                │  │ - Time: 0               │           │
                │  │ - Prohibited: 0         │           │
                │  │ TOTAL: 75/100           │           │
                │  └─────────────────────────┘           │
                └────────────┬───────────────────────────┘
                             │
                             ▼
                ┌────────────────────────────────────────┐
                │   Call Outcome Classifier              │
                │   (Structured classification)          │
                │  ┌─────────────────────────┐           │
                │  │ Analyze:                │           │
                │  │ - Violations            │           │
                │  │ - Conversation ending   │           │
                │  │ - Emotional tone        │           │
                │  │ - Risk score            │           │
                │  │ OUTCOME: Escalated (0.9)│           │
                │  └─────────────────────────┘           │
                └────────────┬───────────────────────────┘
                             │
                             ▼
                ┌────────────────────────┐
                │     JSON Builder       │
                │  (Assemble response)   │
                └────────────┬───────────┘
                             │
                             ▼
                ┌────────────────────────┐
                │    Enhanced JSON       │
                │   Response to Client   │
                └────────────────────────┘
```

---

## Testing Examples

### Test Case 1: High Risk with Prohibited Phrase

**Scenario**: Agent uses prohibited phrase "You must pay immediately or we'll take action"

**Expected Risk Assessment**:
```json
{
  "total_score": 85,
  "risk_level": "critical",
  "escalation_action": "Immediate intervention required",
  "requires_immediate_action": true,
  "auto_escalate": true,
  "breakdown": {
    "policy_violations": 30,
    "emotional_intensity": 15,
    "threat_level": 10,
    "agent_conduct": 0,
    "time_violation": 0,
    "prohibited_phrases": 30
  }
}
```

**Expected Outcome**:
```json
{
  "primary_outcome": "Escalated",
  "confidence_score": 0.95,
  "urgency_level": "critical",
  "customer_satisfaction_indicator": "highly_dissatisfied"
}
```

### Test Case 2: Successful Resolution

**Scenario**: Customer complaint resolved, "Thank you so much, I'm satisfied with the solution"

**Expected Risk Assessment**:
```json
{
  "total_score": 15,
  "risk_level": "minimal",
  "escalation_action": "No escalation required",
  "requires_immediate_action": false,
  "auto_escalate": false
}
```

**Expected Outcome**:
```json
{
  "primary_outcome": "Customer Satisfied",
  "confidence_score": 0.85,
  "urgency_level": "low",
  "customer_satisfaction_indicator": "satisfied",
  "next_action": "Close case successfully; use as positive training example"
}
```

### Test Case 3: Call Dropped Mid-Conversation

**Scenario**: Customer hangs up without resolution after angry exchange

**Expected Risk Assessment**:
```json
{
  "total_score": 45,
  "risk_level": "moderate",
  "escalation_action": "Manager review required"
}
```

**Expected Outcome**:
```json
{
  "primary_outcome": "Dropped",
  "confidence_score": 0.75,
  "urgency_level": "medium",
  "requires_follow_up": true,
  "next_action": "Attempt reconnection; investigate reason for call termination"
}
```

---

## Enhancements Over Previous System

| Feature | Previous System | New System |
|---------|----------------|------------|
| **Risk Score** | Single LLM-generated number (0-100) | Multi-component calculation with breakdown |
| **Risk Justification** | No explanation | Detailed justification with contributing factors |
| **Outcome Classification** | Free-text LLM prediction | Structured 12-category taxonomy |
| **Confidence** | No confidence metric | 0-1 confidence score for each classification |
| **Action Recommendations** | Generic "review manually" | Specific next actions per outcome |
| **Escalation Logic** | Threshold-based only | Multi-factor with automatic overrides |
| **Secondary Outcomes** | Single outcome only | Multi-label capability |
| **Customer Satisfaction** | Not tracked | Explicit satisfaction indicator |
| **Follow-up Tracking** | Not tracked | Boolean flag with action plan |
| **Risk Breakdown** | None | 6-component breakdown |

---

## Benefits for Stakeholders

### 📊 **For Compliance Officers**
- **Detailed risk breakdown**: Understand exactly what drives each risk score
- **Automatic escalation**: High-risk calls flagged immediately
- **Prohibited phrase detection**: Zero-tolerance enforcement
- **Audit trail**: Clear justifications for every score and classification

### 👥 **For Supervisors/Managers**
- **Action clarity**: Know exactly what to do next for each call
- **Prioritization**: Urgency levels help triage review queue
- **Performance insights**: Agent conduct scores identify training needs
- **Outcome tracking**: Measure resolution rates and customer satisfaction

### 📈 **For Data Analysts**
- **Structured data**: All fields machine-readable for reporting
- **Trend analysis**: Track outcome distributions over time
- **Risk patterns**: Identify what factors correlate with escalations
- **Customer insights**: Satisfaction indicators for correlation studies

### 🏢 **For Executives**
- **KPI visibility**: Clear metrics (resolution rate, escalation rate, satisfaction)
- **Risk exposure**: Immediate view of critical and high-risk calls
- **Compliance posture**: Track policy violation trends
- **ROI measurement**: Outcome tracking enables quality improvement measurement

---

## FAQ

**Q: Can I customize the risk component weights?**  
A: The current implementation uses hardcoded weights in `RiskComponents` class. Future enhancement will fully integrate `client_config.risk_scoring.weights` for dynamic weighting.

**Q: What happens if the LLM fails to generate a response?**  
A: The system has fallback values (risk_score=0, outcome="Pending") to ensure the API always returns valid JSON.

**Q: Can I add custom outcome categories?**  
A: The 12 outcome categories in `CallOutcome` enum are fixed. For custom categorization, use `secondary_outcomes` or add to the enum.

**Q: How accurate is the confidence score?**  
A: Confidence is rule-based (not ML-trained). It reflects signal strength (e.g., 0.95 for prohibited phrases because detection is certain; 0.70 for policy compliance because it's inferred).

**Q: Does this work for non-RBI/banking calls?**  
A: Yes! The system is domain-agnostic. Configure `client_config` with your domain-specific policies, triggers, and prohibited phrases.

**Q: Can I disable auto-escalation?**  
A: Yes. Set `"auto_escalate_on_critical": false` in your `client_config.json`.

---

## Future Enhancements

1. **Dynamic risk weighting**: Fully integrate `client_config.risk_scoring.weights` into component calculation
2. **ML-based confidence**: Train confidence models on labeled data for more accurate predictions
3. **Historical context**: Consider customer's previous call history in outcome classification
4. **Sentiment scoring**: Add numerical sentiment scores (0-100) alongside categorical labels
5. **Granular time violations**: Score violations based on how far outside permitted hours the call occurred
6. **Agent comparison**: Benchmark agent performance against team averages
7. **Custom actions**: Allow clients to define custom next actions per outcome in config

---

## Conclusion

The Risk Scoring and Call Outcome Classification system transforms Vigilant from a simple compliance checker into a comprehensive call intelligence platform. With **multi-factor risk assessment**, **structured outcome classification**, and **actionable recommendations**, teams can:

✅ Prioritize high-risk calls for immediate action  
✅ Track customer satisfaction and resolution rates  
✅ Identify agent training opportunities  
✅ Ensure 100% compliance with prohibited phrase enforcement  
✅ Generate detailed audit trails for regulatory review  

**Perfect implementation achieved** ✓

---

*For technical implementation details, see: [backend/services/risk_scoring.py](backend/services/risk_scoring.py)*  
*For configuration examples, see: [backend/config/README.md](backend/config/README.md)*
