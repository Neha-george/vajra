# Testing Guide: Configurable Client Context

## Test Scenarios

### Test 1: Default Configuration
**Objective**: Verify system works with default RBI banking configuration

```bash
curl -X POST http://localhost:8000/analyze \
  -F "audio_file=@test_audio.mp3"
```

**Expected**:
- Response includes `config_applied` with `business_domain: "Banking / Debt Recovery"`
- `active_policy_set: "RBI_Compliance_v2.1"`
- `monitored_products` includes Credit Card, Personal Loan, etc.

---

### Test 2: Custom Telecom Configuration
**Objective**: Test domain-specific configuration (Telecom)

```bash
curl -X POST http://localhost:8000/analyze \
  -F "audio_file=@test_audio.mp3" \
  -F "client_config=@backend/config/example_telecom_config.json"
```

**Expected**:
- `config_applied.business_domain: "Telecommunications"`
- `config_applied.organization_name: "Example Telecom Corp"`
- Risk triggers include "Service Termination Threat", "Data Privacy Breach"
- Custom rules include "Transparent Pricing", "No Forced Upgrades"

---

### Test 3: Prohibited Phrase Detection
**Objective**: Verify automatic detection of prohibited phrases

**Setup**: Create a test config with prohibited phrases:
```json
{
  "business_domain": "Banking / Debt Recovery",
  "organization_name": "Test Bank",
  "active_policy_set": "TEST_v1",
  "monitored_products": ["Credit Card"],
  "risk_triggers": ["Threat"],
  "prohibited_phrases": [
    "you will go to jail",
    "we will tell your family"
  ],
  "custom_rules": []
}
```

**Test**: Upload audio where agent says one of the prohibited phrases

**Expected**:
- `policy_violations` includes violation with:
  - `clause_id: "CLIENT-PROHIBITED-PHRASE"`
  - `rule_name: "Prohibited Language Used"`
  - `severity: "critical"`
  - `evidence_quote` contains the actual phrase
- `risk_escalation_score` ≥ 85
- `compliance_flags` includes "Prohibited Language"
- `is_within_policy: false`

---

### Test 4: Custom Rule Enforcement
**Objective**: Verify custom rules are enforced

**Setup**: Create config with custom rule:
```json
{
  "business_domain": "Banking",
  "organization_name": "Custom Bank",
  "active_policy_set": "CUST_v1",
  "monitored_products": ["Loan"],
  "risk_triggers": [],
  "prohibited_phrases": [],
  "custom_rules": [
    {
      "rule_id": "CUST-001",
      "rule_name": "No Third-Party Contact",
      "description": "Agents must never contact third parties about customer debts without written authorization",
      "severity": "critical",
      "category": "Privacy"
    }
  ]
}
```

**Test**: Upload audio where agent discusses contacting family/employer

**Expected**:
- If violated, `policy_violations` includes the custom rule
- `clause_id: "CUST-001"`
- Listed in `compliance_flags`

---

### Test 5: Config Validation - Invalid Config
**Objective**: Verify validation catches invalid configurations

**Setup**: Create invalid config (missing required field):
```json
{
  "organization_name": "Test Org",
  "monitored_products": ["Product A"]
}
```
(Missing required `business_domain`)

**Test**:
```bash
curl -X POST http://localhost:8000/analyze \
  -F "audio_file=@test.mp3" \
  -F "client_config=@invalid_config.json"
```

**Expected**:
- HTTP 400 Bad Request
- Error message: "Configuration validation failed: business_domain: field required"

---

### Test 6: Config Merging
**Objective**: Verify custom config merges with default

**Setup**: Minimal custom config:
```json
{
  "business_domain": "Insurance",
  "organization_name": "My Insurance Co",
  "prohibited_phrases": [
    "you're trying to cheat us"
  ]
}
```

**Test**:
```bash
curl -X POST http://localhost:8000/analyze \
  -F "audio_file=@test.mp3" \
  -F "client_config=@minimal_config.json"
```

**Expected**:
- `config_applied.business_domain: "Insurance"` (from custom)
- `config_applied.organization_name: "My Insurance Co"` (from custom)
- `config_applied.prohibited_phrases` includes custom phrase
- Other fields (risk_triggers, custom_rules) inherited from default
- All required fields present in merged config

---

### Test 7: Risk Scoring Configuration
**Objective**: Verify risk scoring weights are applied

**Setup**: Config with custom risk weights:
```json
{
  "business_domain": "Banking",
  "organization_name": "Test Bank",
  "risk_scoring": {
    "base_threshold": 40,
    "critical_threshold": 70,
    "weight_policy_violations": 0.5,
    "weight_emotional_tone": 0.3,
    "weight_threat_detection": 0.2
  }
}
```

**Expected**:
- Custom thresholds used for escalation decisions
- Risk scores reflect the configured weights
- Response includes `config_applied.risk_scoring` with custom values

---

### Test 8: Agent Quality Thresholds
**Objective**: Verify agent quality standards are enforced

**Setup**: Config with strict agent standards:
```json
{
  "business_domain": "Banking",
  "organization_name": "Quality Bank",
  "agent_quality_thresholds": {
    "minimum_politeness_score": 80,
    "minimum_empathy_score": 75,
    "minimum_professionalism_score": 85,
    "minimum_overall_score": 80
  }
}
```

**Expected**:
- Agent scores compared against custom thresholds
- Recommendations reflect whether agent met the higher standards
- Config visible in `config_applied.agent_quality_thresholds`

---

### Test 9: Multiple Domain Configs
**Objective**: Test switching between different domain configurations

**Test 9a - Banking**:
```bash
curl -X POST http://localhost:8000/analyze \
  -F "audio_file=@banking_call.mp3" \
  -F "client_config=@backend/config/default_rbi_config.json"
```

**Test 9b - Healthcare**:
```bash
curl -X POST http://localhost:8000/analyze \
  -F "audio_file=@medical_call.mp3" \
  -F "client_config=@backend/config/example_healthcare_config.json"
```

**Test 9c - Telecom**:
```bash
curl -X POST http://localhost:8000/analyze \
  -F "audio_file=@telecom_call.mp3" \
  -F "client_config=@backend/config/example_telecom_config.json"
```

**Expected**:
- Each response reflects the appropriate domain configuration
- Violations detected are domain-relevant
- Custom rules appropriate for each industry applied

---

### Test 10: Product-Specific Policies
**Objective**: Verify product-specific policy enforcement

**Setup**: Config with detailed product definitions:
```json
{
  "business_domain": "Banking",
  "organization_name": "Product Bank",
  "monitored_products": ["Credit Card", "Home Loan"],
  "products": [
    {
      "product_name": "Credit Card",
      "product_type": "Credit Facility",
      "risk_level": "high",
      "specific_policies": ["POL-CC-01", "POL-CC-02"]
    },
    {
      "product_name": "Home Loan",
      "product_type": "Secured Loan",
      "risk_level": "low",
      "specific_policies": ["POL-HL-01"]
    }
  ]
}
```

**Expected**:
- Product configurations visible in `config_applied.products`
- Risk assessments consider product-specific risk levels
- Different treatment for high vs low risk products

---

## Integration Tests

### Integration Test 1: Full Pipeline with Custom Config
```python
import requests

# Prepare custom config
config = {
    "business_domain": "Banking",
    "organization_name": "Test Bank",
    "active_policy_set": "TEST_v1.0",
    "monitored_products": ["Credit Card"],
    "risk_triggers": ["Legal Threats", "Harassment"],
    "prohibited_phrases": ["you will go to jail"],
    "custom_rules": [{
        "rule_id": "TEST-001",
        "rule_name": "Test Rule",
        "description": "Test description",
        "severity": "high",
        "category": "Test"
    }]
}

# Send request
with open("test_audio.mp3", "rb") as audio:
    response = requests.post(
        "http://localhost:8000/analyze",
        files={
            "audio_file": audio,
            "client_config": ("config.json", json.dumps(config), "application/json")
        }
    )

# Verify response
assert response.status_code == 200
data = response.json()
assert data["config_applied"]["organization_name"] == "Test Bank"
assert "TEST-001" in str(data["config_applied"]["custom_rules"])
print("✅ Integration test passed")
```

---

## Validation Tests

### Valid Config Examples

✅ **Minimal Valid Config**:
```json
{
  "business_domain": "Banking"
}
```

✅ **Complete Valid Config**: See example config files

### Invalid Config Examples

❌ **Missing Required Field**:
```json
{
  "organization_name": "Test"
}
```
Expected error: "business_domain: field required"

❌ **Invalid Risk Weight**:
```json
{
  "business_domain": "Banking",
  "risk_scoring": {
    "weight_policy_violations": 1.5
  }
}
```
Expected error: "weight_policy_violations: ensure this value is less than or equal to 1"

❌ **Invalid Severity**:
```json
{
  "business_domain": "Banking",
  "custom_rules": [{
    "rule_id": "R1",
    "rule_name": "Test",
    "description": "Test",
    "severity": "super-critical"
  }]
}
```
Expected error: "severity: unexpected value; permitted: 'critical', 'high', 'medium', 'low'"

---

## Performance Tests

### Test: Large Custom Rules Set
**Objective**: Verify performance with many custom rules

Create config with 50+ custom rules and test response time.

**Expected**: 
- Response time < 30 seconds for typical 2-minute audio
- All rules properly loaded and enforced

### Test: Complex Config Merging
**Objective**: Test performance of config validation and merging

**Expected**:
- Config validation adds < 100ms overhead
- Merging completes instantly

---

## Monitoring Checklist

During testing, monitor logs for:

- `[Config] Configuration validated successfully: <org_name>`
- `[Pipeline] Config applied: <org> | Policy Set: <set> | Domain: <domain>`
- `[ComplianceEngine] PROHIBITED PHRASE DETECTED: '<phrase>' at <timestamp>`
- `[ComplianceEngine] Added N prohibited phrase violations`
- `[RAG] Client rules vectorstore built with N entries`

---

## Success Criteria

All tests should verify:

✅ Config merging works correctly  
✅ Validation catches all invalid configs  
✅ Prohibited phrases trigger automatic critical violations  
✅ Custom rules appear in compliance analysis  
✅ Risk scoring uses configured weights  
✅ Agent quality measured against configured thresholds  
✅ Domain-specific configs work for all example domains  
✅ `config_applied` field always present in response  
✅ No regression in existing functionality  
✅ Performance remains acceptable (<30s for typical calls)

---

## Test Execution Order

1. Run Test 1 (Default Config) - baseline
2. Run Test 5 (Invalid Config) - validation
3. Run Test 6 (Config Merging) - core functionality
4. Run Test 3 (Prohibited Phrases) - automatic detection
5. Run Test 4 (Custom Rules) - rule enforcement
6. Run Test 2 (Telecom Config) - domain switching
7. Run Tests 7-10 - advanced features
8. Run Integration Tests - end-to-end
9. Run Performance Tests - scalability

---

**Testing completed successfully** when all scenarios pass and logs confirm proper configuration application throughout the pipeline.
