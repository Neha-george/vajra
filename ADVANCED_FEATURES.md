# Vigilant Advanced Features Guide

## Overview

This document describes the advanced analytical and architectural features of the Vigilant RBI Compliance Intelligence API, including:

1. **Multiple Speakers Handling** - Automatic speaker diarization and per-speaker analysis
2. **Timeline-Based Emotion Tracking** - Temporal emotion and sentiment analysis throughout conversations
3. **Extensible Schema Architecture** - Plugin-ready design for custom insight types
4. **API Key Authentication** - Enterprise-grade security with header-based authentication

---

## 1. Multiple Speakers Handling

### What It Does

Vigilant automatically **identifies and separates speakers** in call recordings using Google Gemini's multimodal diarization capabilities. Each conversation turn is tagged with the speaker role (`agent` or `customer`), enabling:

- **Per-speaker sentiment analysis**
- **Agent-specific compliance evaluation**
- **Customer emotion tracking**
- **Turn-by-turn conversation flow analysis**

### Implementation

#### Transcription Service
Located in `backend/services/transcriber.py`, the transcription engine:

```python
# Each transcript entry contains speaker identification
{
  "speaker": "agent" | "customer",
  "message": "Exact spoken text (translated to English if needed)",
  "timestamp": "MM:SS"
}
```

#### JSON Output Structure

The `transcript_threads` section in the API response contains the full diarized conversation:

```json
{
  "transcript_threads": [
    {
      "speaker": "agent",
      "message": "Hello, I am calling regarding your outstanding credit card dues.",
      "timestamp": "00:05"
    },
    {
      "speaker": "customer",
      "message": "I have already paid. Please check your records.",
      "timestamp": "00:15"
    }
  ]
}
```

### Use Cases

1. **Agent Compliance Monitoring**: Analyze only agent utterances for policy violations
2. **Customer Emotion Tracking**: Monitor customer emotional state throughout the call
3. **Conversation Flow Analysis**: Understand turn-taking patterns and interruption dynamics
4. **Training & Quality Assurance**: Generate speaker-specific performance reports

### Code References

- Speaker diarization prompt: [transcriber.py:40-45](backend/services/transcriber.py#L40-L45)
- Speaker role extraction: [transcriber.py:124-131](backend/services/transcriber.py#L124-L131)
- Per-speaker analysis in compliance engine: [compliance_engine.py:190](backend/services/compliance_engine.py#L190)

---

## 2. Timeline-Based Emotion Tracking

### What It Does

Vigilant tracks **emotional evolution throughout conversations**, combining:

- **Transcript-based sentiment analysis** (from language content)
- **Acoustic emotion detection** (from voice characteristics: energy, pitch, arousal)
- **Temporal emotion graphs** (showing emotion changes over time)

This provides a complete picture of how emotions escalate or de-escalate during calls.

### Output Structure

The API returns **three complementary emotion tracking formats**:

#### A. Emotional Graph (High-Resolution Timeline)

Tracks emotion at ~30-second intervals with acoustic validation:

```json
{
  "emotional_and_tonal_analysis": {
    "emotional_graph": [
      {
        "timestamp": "00:15",
        "tone": "Neutral",
        "score": 0.3,
        "acoustic_arousal": "Low"
      },
      {
        "timestamp": "00:45",
        "tone": "Concerned",
        "score": 0.6,
        "acoustic_arousal": "Medium"
      },
      {
        "timestamp": "01:15",
        "tone": "Frustrated",
        "score": 0.8,
        "acoustic_arousal": "High"
      }
    ]
  }
}
```

**Fields:**
- `timestamp`: Time point in conversation (MM:SS)
- `tone`: Emotional tone category (Neutral, Concerned, Frustrated, Angry, Distressed, Aggressive, Threatening)
- `score`: Intensity score (0.0 = calm, 1.0 = peak intensity)
- `acoustic_arousal`: Voice energy level (Low/Medium/High) from acoustic analysis

#### B. Emotion Timeline (3-Stage Summary)

High-level emotion state at three key conversation phases:

```json
{
  "emotion_timeline": [
    {"time": "start", "emotion": "neutral"},
    {"time": "middle", "emotion": "frustrated"},
    {"time": "end", "emotion": "angry"}
  ]
}
```

**Phases:**
- `start`: Opening/greeting (first 15% of conversation)
- `middle`: Main issue discussion (middle 70% of conversation)
- `end`: Resolution/conclusion (final 15% of conversation)

#### C. Tone Progression (Ordered List)

Sequential list showing emotional evolution from start to end:

```json
{
  "tone_progression": ["Neutral", "Concerned", "Frustrated", "Angry"]
}
```

### Acoustic Integration

Vigilant merges **speech signal features** with **LLM-derived sentiment**:

- **Energy Score**: Overall voice intensity (loud vs quiet)
- **Pitch (Hz)**: Voice fundamental frequency (high-pitched = stressed/anxious)
- **Zero-Crossing Rate (ZCR)**: Speech noisiness (high = distress/shouting)
- **Arousal Level**: Composite measure (Low/Medium/High)

These acoustic features are computed in `backend/services/audio_processor.py` and merged into the emotional_graph in `backend/services/json_builder.py`.

### Use Cases

1. **Escalation Detection**: Identify when conversations shift from calm to hostile
2. **Agent Training**: Show agents the emotional impact of their responses
3. **Risk Scoring**: Factor emotional intensity into risk calculations
4. **Coaching Insights**: Pinpoint exact moments where tone deteriorated

### Code References

- Emotion extraction prompt: [compliance_engine.py:70-95](backend/services/compliance_engine.py#L70-L95)
- Acoustic processing: [audio_processor.py](backend/services/audio_processor.py)
- Emotion graph assembly: [json_builder.py:105-145](backend/services/json_builder.py#L105-L145)
- Acoustic-emotion merging: [json_builder.py:127-135](backend/services/json_builder.py#L127-L135)

---

## 3. Extensible Schema Architecture

### What It Does

Vigilant's JSON output schema is designed to be **extensible without breaking changes**. Organizations can:

- Add **custom insight types** via plugin processors
- Attach **arbitrary metadata** without schema modifications
- Define **domain-specific analyses** in configuration

### Implementation

#### A. Custom Insights Configuration

In your client configuration JSON (`ClientConfig`), define custom insight types:

```json
{
  "custom_insights": {
    "sentiment_by_speaker": {
      "enabled": true,
      "config": {
        "threshold": 0.7,
        "aggregate_method": "weighted_average"
      }
    },
    "topic_clustering": {
      "enabled": true,
      "config": {
        "min_clusters": 3,
        "algorithm": "kmeans"
      }
    },
    "regulatory_keyword_matching": {
      "enabled": true,
      "config": {
        "custom_keywords": ["foreclosure", "repossession", "default"]
      }
    }
  }
}
```

**Fields:**
- `enabled`: Boolean flag to activate this insight type
- `config`: Free-form dictionary with insight-specific parameters

#### B. Extensions Field in Output

The API response includes an `extensions` section for custom data:

```json
{
  "request_id": "REQ-ABC123-MA",
  "metadata": { ... },
  "intelligence_summary": { ... },
  "extensions": {
    "custom_insights": {
      "configured": ["sentiment_by_speaker", "topic_clustering"],
      "note": "Custom insight processing can be implemented as plugins"
    },
    "client_extensions": {
      "internal_case_id": "CASE-2024-001234",
      "assigned_reviewer": "john.doe@example.com",
      "priority_level": "high"
    },
    "plugin_data": {},
    "reserved_for_future_use": {}
  }
}
```

**Subsections:**
- `custom_insights`: Results from custom insight processors
- `client_extensions`: Arbitrary client-defined metadata from config
- `plugin_data`: Space for third-party plugin outputs
- `reserved_for_future_use`: Placeholder for future Vigilant features

#### C. Client Extensions in Configuration

Attach arbitrary metadata to your configuration:

```json
{
  "business_domain": "Banking",
  "organization_name": "Example Bank",
  "extensions": {
    "internal_case_id": "CASE-2024-001234",
    "cost_center": "CC-DEV-001",
    "compliance_officer": "jane.smith@example.com",
    "custom_tags": ["high-risk", "legal-hold", "audit-required"]
  }
}
```

This metadata flows through to the API response `extensions.client_extensions` field.

### How to Add Custom Insights

To implement a new insight type:

1. **Define the insight in client config**:
   ```json
   {
     "custom_insights": {
       "my_custom_insight": {
         "enabled": true,
         "config": {"param1": "value1"}
       }
     }
   }
   ```

2. **Create a processor module** (e.g., `backend/services/custom_insights/my_custom_insight.py`):
   ```python
   def process_my_custom_insight(
       transcript_threads: list[dict],
       config: dict,
       compliance_result: dict
   ) -> dict:
       """
       Process custom insight logic.
       
       Returns:
           Custom insight results as a dictionary
       """
       # Your custom analysis logic here
       return {
           "insight_type": "my_custom_insight",
           "results": { ... }
       }
   ```

3. **Register the processor in `json_builder.py`**:
   ```python
   # In build_output_json function
   if "my_custom_insight" in client_config.get("custom_insights", {}):
       insight_config = client_config["custom_insights"]["my_custom_insight"]
       if insight_config.get("enabled"):
           from services.custom_insights.my_custom_insight import process_my_custom_insight
           extensions["custom_insights"]["my_custom_insight"] = process_my_custom_insight(
               transcription_result["transcript_threads"],
               insight_config["config"],
               compliance_result
           )
   ```

### Use Cases

1. **Industry-Specific Analysis**: Add healthcare compliance checks, financial regulatory scans, etc.
2. **Custom Metrics**: Track organization-specific KPIs (e.g., script adherence, brand language usage)
3. **Integration Metadata**: Attach CRM IDs, ticket numbers, or other system references
4. **Experimental Features**: Test new analysis algorithms without production schema changes

### Code References

- ClientConfig extensions: [client_config.py:345-358](backend/models/client_config.py#L345-L358)
- JSON output extensions: [json_builder.py:240-265](backend/services/json_builder.py#L240-L265)

---

## 4. API Key Authentication

### What It Does

Vigilant supports **header-based API key authentication** to secure the `/analyze` endpoint. When enabled:

- All requests to `/analyze` must include a valid API key
- Keys are validated against a whitelist
- Invalid or missing keys return 401/403 errors
- Authentication can be disabled for development

### Configuration

#### Enable Authentication

Set the `VIGILANT_API_KEYS` environment variable with comma-separated keys:

**Linux/Mac:**
```bash
export VIGILANT_API_KEYS="your-secret-key-1,your-secret-key-2,your-secret-key-3"
```

**Windows PowerShell:**
```powershell
$env:VIGILANT_API_KEYS="your-secret-key-1,your-secret-key-2,your-secret-key-3"
```

**Docker Compose:**
```yaml
services:
  backend:
    environment:
      - VIGILANT_API_KEYS=your-secret-key-1,your-secret-key-2
```

**.env file:**
```
VIGILANT_API_KEYS=your-secret-key-1,your-secret-key-2,your-secret-key-3
```

#### Disable Authentication (Development Only)

If `VIGILANT_API_KEYS` is not set or empty, authentication is **disabled**. The server will accept all requests without validation.

**Warning:** Only disable authentication in development/testing environments. Production deployments should always use authentication.

### Making Authenticated Requests

Include the API key in the `X-API-Key` header:

#### cURL Example
```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "X-API-Key: your-secret-key-1" \
  -F "audio_file=@call_recording.mp3" \
  -F "client_config=@config.json"
```

#### Python Example
```python
import requests

url = "http://localhost:8000/analyze"
headers = {"X-API-Key": "your-secret-key-1"}
files = {
    "audio_file": open("call_recording.mp3", "rb"),
    "client_config": open("config.json", "rb")
}

response = requests.post(url, headers=headers, files=files)
print(response.json())
```

#### JavaScript/TypeScript Example
```javascript
const formData = new FormData();
formData.append('audio_file', audioFile);
formData.append('client_config', configFile);

const response = await fetch('http://localhost:8000/analyze', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-secret-key-1'
  },
  body: formData
});

const result = await response.json();
```

### Error Responses

#### Missing API Key (401 Unauthorized)
```json
{
  "detail": "Missing API key. Provide X-API-Key header."
}
```

#### Invalid API Key (403 Forbidden)
```json
{
  "detail": "Invalid API key."
}
```

### Startup Behavior

When Vigilant starts, it logs the authentication status:

**Authentication Enabled:**
```
[Vigilant] API Authentication: ENABLED (3 key(s) configured)
[Vigilant] Requests to /analyze require X-API-Key header
```

**Authentication Disabled:**
```
[Vigilant] API Authentication: DISABLED (set VIGILANT_API_KEYS to enable)
```

### Security Best Practices

1. **Use Strong Keys**: Generate cryptographically secure random keys
   ```bash
   # Linux/Mac
   openssl rand -hex 32
   
   # Python
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Rotate Keys Regularly**: Change API keys periodically (quarterly recommended)

3. **Key Segregation**: Use different keys for different clients/environments:
   ```bash
   VIGILANT_API_KEYS=client-a-prod-key,client-b-prod-key,internal-testing-key
   ```

4. **Never Commit Keys**: Keep keys in environment variables or secret management systems, never in code

5. **HTTPS in Production**: Always use HTTPS for API requests to prevent key interception

6. **Rate Limiting**: Consider adding rate limiting middleware for additional protection (not included by default)

### Implementation Details

- **Dependency Injection**: Uses FastAPI's `Security` and `Depends` for clean authentication
- **Header Location**: API key must be in `X-API-Key` header (case-insensitive)
- **Validation**: Keys are validated against an in-memory set loaded at startup
- **Auto-Error**: Authentication errors return proper HTTP status codes (401/403)

### Code References

- Authentication configuration: [main.py:24-31](backend/main.py#L24-L31)
- Validation function: [main.py:107-140](backend/main.py#L107-L140)
- Endpoint protection: [main.py:217](backend/main.py#L217)
- Startup logging: [main.py:160-165](backend/main.py#L160-L165)

---

## Integration Examples

### Complete Request with All Features

```python
import requests
import json

# Configuration with custom extensions
config = {
    "business_domain": "Banking / Debt Recovery",
    "organization_name": "Example Bank Ltd",
    "active_policy_set": "RBI_Compliance_v2.1",
    "monitored_products": ["Credit Card", "Personal Loan"],
    "custom_insights": {
        "sentiment_by_speaker": {
            "enabled": True,
            "config": {"threshold": 0.7}
        }
    },
    "extensions": {
        "case_id": "CASE-2024-001234",
        "reviewer": "compliance@example.com"
    }
}

# Make authenticated request
response = requests.post(
    "https://your-vigilant-instance.com/analyze",
    headers={"X-API-Key": "your-production-key"},
    files={
        "audio_file": open("call_recording.mp3", "rb"),
        "client_config": ("config.json", json.dumps(config), "application/json")
    }
)

result = response.json()

# Access speaker-diarized transcript
for turn in result["transcript_threads"]:
    print(f"[{turn['timestamp']}] {turn['speaker'].upper()}: {turn['message']}")

# Access emotion timeline
for emotion_point in result["emotional_and_tonal_analysis"]["emotional_graph"]:
    print(f"{emotion_point['timestamp']}: {emotion_point['tone']} (arousal: {emotion_point['acoustic_arousal']})")

# Access custom extensions
print("Custom metadata:", result["extensions"]["client_extensions"])
```

---

## Summary

| Feature | Implementation | Location |
|---------|----------------|----------|
| **Multiple Speakers** | Automatic diarization in transcription | `transcriber.py` |
| **Emotion Tracking** | 3-format timeline + acoustic fusion | `json_builder.py`, `audio_processor.py` |
| **Extensible Schema** | `custom_insights` + `extensions` fields | `client_config.py`, `json_builder.py` |
| **API Authentication** | X-API-Key header validation | `main.py` |

All features are **production-ready** and available in the current Vigilant deployment.

---

## Need Help?

- **Documentation**: See [README.md](README.md) for setup and deployment
- **Configuration Guide**: See [config/README.md](backend/config/README.md) for client context configuration
- **Risk Scoring**: See [RISK_AND_OUTCOME_CLASSIFICATION.md](RISK_AND_OUTCOME_CLASSIFICATION.md)
- **Agent Performance**: See [AGENT_PERFORMANCE_SCORING.md](AGENT_PERFORMANCE_SCORING.md)
