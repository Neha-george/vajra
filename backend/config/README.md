# Client Configuration System

## Overview

The **Vigilant RBI Compliance Intelligence API** supports **mandatory configurable client context** that influences compliance analysis. This allows organizations to customize the system for their specific business domain, products, policies, and risk triggers.

## How It Works

### 1. Default Configuration
The system uses [`default_rbi_config.json`](./default_rbi_config.json) as the base configuration following RBI (Reserve Bank of India) compliance standards for banking and debt recovery.

### 2. Custom Configuration
Clients can upload a custom configuration JSON file when calling the `/analyze` endpoint. The custom config is merged with the default, with custom values taking precedence.

### 3. Validation
All configurations are validated against a comprehensive Pydantic schema (see [`models/client_config.py`](../models/client_config.py)) to ensure correctness.

---

## Configuration Schema

### Core Fields

#### Business Context
```json
{
  "business_domain": "Banking / Debt Recovery",
  "organization_name": "Example Bank Ltd",
  "active_policy_set": "RBI_Compliance_v2.1"
}
```

- **business_domain**: Your industry (Banking, Telecom, Healthcare, Insurance, etc.)
- **organization_name**: Your organization's name
- **active_policy_set**: Version/identifier of the policy set being enforced

#### Products & Services
```json
{
  "monitored_products": ["Credit Card", "Personal Loan", "Home Loan"],
  "products": [
    {
      "product_name": "Credit Card",
      "product_type": "Credit Facility",
      "risk_level": "high",
      "specific_policies": ["RBI-CC-01", "RBI-CC-02"]
    }
  ]
}
```

- **monitored_products**: Simple list of product names
- **products**: Detailed product configurations with risk levels and specific policies

#### Risk Triggers
```json
{
  "risk_triggers": [
    "Legal Threats",
    "Harassment",
    "Unauthorized Debit",
    "Physical Visit Threat"
  ],
  "compliance_triggers": [
    {
      "trigger_name": "Harassment Detected",
      "keywords": ["harass", "bother", "annoy"],
      "severity": "critical",
      "action_required": "Immediate escalation"
    }
  ]
}
```

- **risk_triggers**: Simple keyword list flagged as violations
- **compliance_triggers**: Detailed trigger definitions with keywords and actions

#### Custom Rules
```json
{
  "custom_rules": [
    {
      "rule_id": "CUST-001",
      "rule_name": "No Family Contact",
      "description": "Agents must not contact family members without consent",
      "severity": "critical",
      "category": "Privacy Protection"
    }
  ]
}
```

Custom rules are embedded into the RAG (Retrieval Augmented Generation) system and actively used in compliance detection.

#### Prohibited Phrases
```json
{
  "prohibited_phrases": [
    "you will go to jail",
    "we will send someone to your house",
    "we will tell your family"
  ]
}
```

**CRITICAL**: If any prohibited phrase is detected in agent utterances, it's automatically flagged as a critical violation with risk score ≥ 85.

#### Risk Scoring Configuration
```json
{
  "risk_scoring": {
    "base_threshold": 50,
    "critical_threshold": 80,
    "weight_policy_violations": 0.4,
    "weight_emotional_tone": 0.3,
    "weight_threat_detection": 0.3
  }
}
```

Controls how the overall risk score (0-100) is calculated.

#### Agent Quality Standards
```json
{
  "agent_quality_thresholds": {
    "minimum_politeness_score": 60,
    "minimum_empathy_score": 50,
    "minimum_professionalism_score": 70,
    "minimum_overall_score": 60
  }
}
```

Defines minimum acceptable agent performance scores.

#### Time & Contact Restrictions
```json
{
  "allowed_call_hours": {
    "start": "08:00",
    "end": "19:00",
    "timezone": "Asia/Kolkata"
  },
  "max_call_attempts_per_day": 3
}
```

#### Other Settings
- **auto_escalate_on_critical**: Auto-escalate calls with critical violations
- **notification_settings**: Email/webhook preferences
- **report_recipients**: List of email addresses for reports
- **config_version**: Your config schema version
- **notes**: Optional notes about this configuration

---

## Usage

### Option 1: Use Default Configuration
Simply call `/analyze` without the `client_config` parameter:

```bash
curl -X POST http://localhost:8000/analyze \
  -F "audio_file=@recording.mp3"
```

### Option 2: Upload Custom Configuration
Create a custom config JSON file and upload it:

```bash
curl -X POST http://localhost:8000/analyze \
  -F "audio_file=@recording.mp3" \
  -F "client_config=@my_custom_config.json"
```

### Option 3: Use Example Configurations
We provide domain-specific example configurations:

- **Banking**: [`default_rbi_config.json`](./default_rbi_config.json) (default)
- **Telecom**: [`example_telecom_config.json`](./example_telecom_config.json)
- **Insurance**: [`example_insurance_config.json`](./example_insurance_config.json)
- **Healthcare**: [`example_healthcare_config.json`](./example_healthcare_config.json)

Example:
```bash
curl -X POST http://localhost:8000/analyze \
  -F "audio_file=@call.mp3" \
  -F "client_config=@config/example_telecom_config.json"
```

---

## Example Configurations by Domain

### Banking (RBI Compliance)
- **Focus**: Debt recovery, loan management, fair practices
- **Key Triggers**: Legal threats, harassment, unauthorized debits, social shaming
- **Regulations**: RBI Fair Practices Code, NBFC Guidelines
- **File**: [`default_rbi_config.json`](./default_rbi_config.json)

### Telecommunications (TRAI Compliance)
- **Focus**: Service quality, billing transparency, data privacy
- **Key Triggers**: Service termination threats, unauthorized charges, forced upselling
- **Regulations**: TRAI guidelines, data protection
- **File**: [`example_telecom_config.json`](./example_telecom_config.json)

### Insurance (IRDAI Compliance)
- **Focus**: Claims management, medical data privacy, fair settlement
- **Key Triggers**: Unjustified claim denials, medical info misuse, delay tactics
- **Regulations**: IRDAI regulations, insurance fair practices
- **File**: [`example_insurance_config.json`](./example_insurance_config.json)

### Healthcare (HIPAA Compliance)
- **Focus**: Patient privacy, medical data protection, sensitive communication
- **Key Triggers**: Medical information disclosure, patient harassment, discrimination
- **Regulations**: HIPAA, patient rights protection
- **File**: [`example_healthcare_config.json`](./example_healthcare_config.json)

---

## How Configuration Influences Analysis

### 1. **RAG Clause Retrieval**
- Custom rules are embedded into the vector database
- System retrieves both standard policies and client-specific rules
- Risk triggers are treated as policy clauses

### 2. **Compliance Detection**
- LLM is instructed to enforce all custom rules
- Prohibited phrases trigger automatic critical violations
- Agent quality is measured against configured thresholds

### 3. **Risk Scoring**
- Weights from `risk_scoring` control the final risk score calculation
- Prohibited phrase detection sets minimum score to 85
- Thresholds determine escalation urgency

### 4. **Output Structure**
- `config_applied` field in response shows which config was used
- Violations reference custom rule IDs when applicable
- Recommendations reflect domain-specific requirements

---

## Validation

### Automatic Validation
All configurations are automatically validated when uploaded. If validation fails, you'll receive a detailed error:

```json
{
  "detail": "Configuration validation failed: business_domain: field required; risk_scoring.weight_policy_violations: ensure this value is less than or equal to 1"
}
```

### Schema Enforcement
The system enforces:
- **Required fields**: `business_domain`, `organization_name`
- **Type checking**: Strings, integers, floats, booleans, lists, objects
- **Range validation**: Scores (0-100), weights (0.0-1.0)
- **Enum validation**: Severity levels, risk levels
- **List constraints**: Non-empty required lists

### Best Practices
1. **Start with an example**: Copy a domain-specific example and modify
2. **Test incrementally**: Make small changes and test
3. **Use meaningful IDs**: Rule IDs should be descriptive (e.g., `BANK-PRIV-001`)
4. **Be specific**: Precise prohibited phrases and triggers work better
5. **Document your config**: Use the `notes` field to explain your setup

---

## Advanced: Creating Custom Configurations

### Step 1: Copy a Template
```bash
cp backend/config/default_rbi_config.json my_config.json
```

### Step 2: Customize Core Settings
```json
{
  "business_domain": "Your Domain",
  "organization_name": "Your Org",
  "active_policy_set": "YOUR_POLICY_v1.0"
}
```

### Step 3: Define Your Products
```json
{
  "monitored_products": ["Product A", "Product B"],
  "products": [
    {
      "product_name": "Product A",
      "product_type": "Service Type",
      "risk_level": "high",
      "specific_policies": ["POL-01"]
    }
  ]
}
```

### Step 4: Add Domain-Specific Rules
```json
{
  "custom_rules": [
    {
      "rule_id": "ORG-001",
      "rule_name": "Your Rule Name",
      "description": "Detailed description of what agents must/must not do",
      "severity": "critical",
      "category": "Your Category"
    }
  ]
}
```

### Step 5: Define Prohibited Phrases
```json
{
  "prohibited_phrases": [
    "phrase that should never be used",
    "another inappropriate phrase"
  ]
}
```

### Step 6: Test Your Configuration
```bash
curl -X POST http://localhost:8000/analyze \
  -F "audio_file=@test.mp3" \
  -F "client_config=@my_config.json"
```

---

## API Response

The analysis response includes a `config_applied` field showing which configuration was used:

```json
{
  "request_id": "REQ-ABC123-MA",
  "config_applied": {
    "business_domain": "Banking / Debt Recovery",
    "organization_name": "RBI Standard Compliance",
    "active_policy_set": "RBI_Compliance_v2.1",
    "monitored_products": ["Credit Card", "Personal Loan"],
    "config_version": "2.0.0"
  },
  "compliance_analysis": {
    "is_within_policy": false,
    "policy_violations": [
      {
        "clause_id": "CLIENT-PROHIBITED-PHRASE",
        "rule_name": "Prohibited Language Used",
        "description": "Agent used prohibited phrase: 'you will go to jail'",
        "timestamp": "01:23",
        "evidence_quote": "If you don't pay, you will go to jail",
        "severity": "critical"
      }
    ]
  }
}
```

---

## Troubleshooting

### Config Not Applied
- Check JSON syntax (use a validator like jsonlint.com)
- Ensure file is uploaded with correct parameter name: `client_config`
- Check server logs for validation errors

### Custom Rules Not Detected
- Ensure `rule_id` follows a consistent pattern
- Check `description` is detailed enough for LLM understanding
- Verify rules appear in the `config_applied` response field

### Prohibited Phrases Not Detected
- Phrases are case-insensitive but must match substring
- Use specific phrases, not generic words
- Check agent utterances in transcript

### Risk Score Not Changing
- Verify `risk_scoring` weights sum to approximately 1.0
- Check if prohibited phrases set minimum score (85)
- Review `weight_policy_violations` setting

---

## Support

For questions or issues with client configuration:

1. Check this documentation
2. Review example configurations in `backend/config/`
3. Examine the schema in `backend/models/client_config.py`
4. Review API response `config_applied` to verify what was used

---

**Version**: 2.0.0  
**Last Updated**: 2026-02-21  
**Schema Definition**: [`backend/models/client_config.py`](../models/client_config.py)
