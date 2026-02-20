# Vigilant – RBI Compliance Intelligence Backend

> Automated multimodal compliance officer for banks.  
> Analyzes debt recovery call recordings for RBI policy violations, emotional tone, and agent conduct.

## ✨ Key Features

- **🔧 Configurable Client Context** - Customize for your business domain, products, policies, and risk triggers
- **🎯 Multi-Domain Support** - Pre-configured for Banking, Telecom, Insurance, Healthcare
- **🤖 AI-Powered Analysis** - Gemini 2.0 Flash/Pro with multimodal understanding
- **📊 Comprehensive Auditing** - Policy violations, emotional analysis, agent performance scoring
- **🎲 Multi-Factor Risk Scoring** - 6-component risk assessment with automatic escalation
- **🎯 Call Outcome Classification** - Structured 12-category outcome prediction with confidence scoring
- **👤 Agent Performance Scoring** - Multi-dimensional quality assessment with training recommendations
- **🔍 RAG-Enhanced Detection** - Retrieval Augmented Generation for accurate policy matching
- **⚡ Real-Time Processing** - Fast acoustic + LLM analysis pipeline
- **🚨 Automatic Escalation** - Critical violations trigger immediate alerts

---

## 🚀 Advanced Features

### 1. 🔧 Configurable Client Context

**Mandatory client configuration support** allows you to customize compliance analysis for your specific needs.

#### Configuration Options

- **Business Domain**: Banking, Telecom, Healthcare, Insurance, or custom
- **Products & Services**: Define risk levels and policies per product
- **Custom Compliance Rules**: Add organization-specific policies
- **Risk Triggers**: Keywords that flag compliance violations
- **Prohibited Phrases**: Automatic critical violations for forbidden language
- **Agent Quality Standards**: Minimum acceptable performance scores
- **Risk Scoring Weights**: Control how risk scores are calculated
- **Time Restrictions**: Permitted calling hours and contact limits

#### Example Configurations Included

- **🏦 Banking** ([`default_rbi_config.json`](backend/config/default_rbi_config.json)) - RBI debt recovery compliance
- **📱 Telecom** ([`example_telecom_config.json`](backend/config/example_telecom_config.json)) - TRAI guidelines
- **🏥 Healthcare** ([`example_healthcare_config.json`](backend/config/example_healthcare_config.json)) - HIPAA compliance
- **🛡️ Insurance** ([`example_insurance_config.json`](backend/config/example_insurance_config.json)) - IRDAI regulations

📚 **[Read Full Configuration Documentation](backend/config/README.md)**

---

### 2. 🎲 Risk Scoring & Call Outcome Classification

**Comprehensive risk assessment** with multi-factor scoring and structured outcome prediction.

#### Risk Scoring (0-100)

- **6-Component Breakdown**: Policy violations (40), Emotional intensity (25), Threat detection (25), Agent conduct (25), Time violations (15), Prohibited phrases (60)
- **5 Risk Levels**: Minimal → Low → Moderate → High → Critical
- **Automatic Escalation**: Configurable thresholds for immediate action
- **Detailed Justification**: Human-readable explanation for every score

#### Call Outcome Classification

- **12 Outcome Categories**: Resolved, Escalated, Dropped, Legal Dispute, Unresolved, Callback Required, etc.
- **Confidence Scoring**: 0-1 confidence level for each classification
- **Secondary Outcomes**: Multi-label capability for complex scenarios
- **Next Action Recommendations**: Specific guidance for each outcome

📚 **[Read Risk & Outcome Documentation](RISK_AND_OUTCOME_CLASSIFICATION.md)**

---

### 3. 👤 Agent Quality & Performance Scoring

**Multi-dimensional agent assessment** with actionable insights and training recommendations.

#### 5-Component Performance Scoring

- **Communication Skills** (30 pts): Clarity, articulation, professional tone
- **Customer Service** (25 pts): Politeness (12) + Empathy (13)
- **Professionalism** (20 pts): Demeanor, boundaries, respect
- **Problem Resolution** (15 pts): Issue understanding and solution effectiveness
- **Compliance Adherence** (10 pts): Policy compliance and proper procedures

#### Performance Levels (7 Tiers)

Exceptional (90-100) → Excellent (80-89) → Good (70-79) → Satisfactory (60-69) → Needs Improvement (40-59) → Poor (20-39) → Unacceptable (0-19)

#### Training Recommendations

- **Automated weakness detection**: 12 specific improvement areas
- **Prioritized training plans**: Critical → High → Medium → Low → None
- **Management triggers**: Coaching, disciplinary action, or commendation flags
- **Specific course recommendations**: Mapped to identified weaknesses

📚 **[Read Agent Performance Documentation](AGENT_PERFORMANCE_SCORING.md)**

---

### 4. 🚀 Enterprise-Ready Architecture

**Production features** for enterprise deployment and integration.

#### Multiple Speakers Handling
- **Automatic Diarization**: Separates agent and customer speech
- **Per-Speaker Analysis**: Individual sentiment and emotion tracking
- **Turn-by-Turn Transcription**: Complete conversation flow with timestamps

#### Timeline-Based Emotion Tracking
- **High-Resolution Emotional Graph**: Track emotion changes every ~30 seconds
- **3-Stage Timeline**: Start/middle/end emotion summary
- **Acoustic Fusion**: Merges voice analytics (energy, pitch, arousal) with LLM sentiment
- **Tone Progression**: Sequential emotion evolution throughout the call

#### Extensible Schema Architecture
- **Custom Insights**: Plugin-ready design for domain-specific analysis types
- **Extensions Field**: Attach arbitrary metadata without schema changes
- **Configuration-Driven**: Define custom insight types in client config
- **Future-Proof**: Add new features without breaking existing integrations

#### API Key Authentication
- **Header-Based Security**: X-API-Key authentication for all endpoints
- **Multi-Key Support**: Whitelist multiple API keys for different clients
- **Environment Configuration**: Enable/disable via VIGILANT_API_KEYS env var
- **Production-Ready**: Secure API access for enterprise deployments

📚 **[Read Advanced Features Documentation](ADVANCED_FEATURES.md)** - Multiple speakers, emotion tracking, extensibility, authentication

---

## 🎯 Quick Usage

```bash
# Use default RBI banking config
curl -X POST http://localhost:8000/analyze \
  -H "X-API-Key: your-api-key-here" \
  -F "audio_file=@call.mp3"

# Use custom config
curl -X POST http://localhost:8000/analyze \
  -H "X-API-Key: your-api-key-here" \
  -F "audio_file=@call.mp3" \
  -F "client_config=@your_config.json"

# Use domain-specific example
curl -X POST http://localhost:8000/analyze \
  -H "X-API-Key: your-api-key-here" \
  -F "audio_file=@call.mp3" \
  -F "client_config=@backend/config/example_telecom_config.json"
```

**Note**: API key authentication is optional. Set `VIGILANT_API_KEYS` environment variable to enable. If not set, authentication is disabled for development.

📚 **[Read Full Configuration Documentation](backend/config/README.md)**

---

## Quick Start (Local – No Docker)

### 1. Prerequisites
- Python 3.11+
- [FFmpeg](https://ffmpeg.org/download.html) installed and on PATH (required for MP3 decoding)

### 2. Setup

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure API Key

Edit `backend/.env`:
```
GOOGLE_API_KEY=your_actual_gemini_api_key_here
```

Get a free Gemini API key at: https://aistudio.google.com/app/apikey

### 4. Run the Server

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

On first startup, the RAG policy vector store is built and cached in `./chroma_db/`.  
Subsequent startups load from cache.

### 5. Test the API

Open Swagger UI: http://localhost:8000/docs

**Health check:**
```bash
curl http://localhost:8000/health
```

**Analyze a call recording:**
```bash
curl -X POST http://localhost:8000/analyze \
  -F "audio_file=@your_call.mp3"
```

**With custom client config:**
```bash
curl -X POST http://localhost:8000/analyze \
  -F "audio_file=@your_call.mp3" \
  -F "client_config=@my_bank_config.json"
```

**Run test suite (requires a test audio file):**
```bash
python test_api.py your_call.mp3
```

---

## Docker

```bash
# From project root
docker-compose up --build
```

API available at: http://localhost:8000

---

## API Reference

### `POST /analyze`

| Field | Type | Required | Description |
|---|---|---|---|
| `audio_file` | File | ✅ | Call recording (.mp3, .wav, .ogg, .m4a, .flac) |
| `client_config` | File | ❌ | Bank-specific JSON policy config |

**Response:** Complete compliance audit JSON (see schema below)

### `GET /health`
Returns `{"status": "ok", "service": "Vigilant"}`

---

## Output JSON Schema

```json
{
  "request_id": "REQ-XXXXXX-MA",
  "metadata": { "timestamp", "detected_languages", "processing_time_ms", "conversation_complexity" },
  "config_applied": { "business_domain", "monitored_products", "active_policy_set", "risk_triggers" },
  "intelligence_summary": { "summary", "category", "conversation_about", "primary_intent", "key_topics", "entities", "root_cause" },
  "emotional_and_tonal_analysis": { "overall_sentiment", "emotional_tone", "tone_progression", "emotional_graph", "emotion_timeline" },
  "compliance_and_risk_audit": { "is_within_policy", "compliance_flags", "policy_violations", "detected_threats", "risk_scores" },
  "transcript_threads": [{ "speaker", "message", "timestamp" }],
  "performance_and_outcomes": { "agent_performance", "call_outcome_prediction", "repeat_complaint_detected", "final_status", "recommended_action" }
}
```

---

## Architecture

```
POST /analyze
     │
     ├── librosa     → Acoustic Analysis (energy, pitch, arousal per segment)
     │
     ├── Gemini 1.5  → Multimodal Transcription (speaker diarization, language detection)
     │
     ├── ChromaDB    → RAG Policy Retrieval (RBI clauses relevant to each agent utterance)
     │
     ├── Gemini 1.5  → Agentic Compliance Reasoning (violations, emotional graph, scores)
     │
     └── JSON Builder → Final structured output
```

---

## Client Configuration

Vigilant supports **mandatory configurable client context** that influences compliance analysis.

### Minimal Example

```json
{
  "business_domain": "Banking / Debt Recovery",
  "organization_name": "Your Bank Ltd",
  "active_policy_set": "YOUR_POLICY_v1.0",
  "monitored_products": ["Credit Card", "Personal Loan"],
  "risk_triggers": ["Legal Threats", "Harassment", "Abuse"],
  "prohibited_phrases": [
    "you will go to jail",
    "we will tell your family"
  ],
  "custom_rules": [
    {
      "rule_id": "CUSTOM-001",
      "rule_name": "No Family Contact",
      "description": "Agents must not contact family members without explicit written consent",
      "severity": "critical",
      "category": "Privacy Protection"
    }
  ]
}
```

### How Configuration Influences Analysis

1. **RAG Retrieval**: Custom rules embedded into vector store alongside RBI policies
2. **Violation Detection**: LLM enforces all custom rules and triggers
3. **Prohibited Phrases**: Automatic critical violations (risk score ≥ 85)
4. **Risk Scoring**: Weighted calculation based on your configuration
5. **Agent Standards**: Quality measured against your thresholds

### Complete Schema Reference

For the full configuration schema with all options, see:

📚 **[Complete Configuration Guide](backend/config/README.md)**

Includes:
- Full schema documentation
- Domain-specific examples (Banking, Telecom, Healthcare, Insurance)
- Validation and best practices
- Advanced customization guide

---

## Project Structure

```
backend/
├── main.py                    # FastAPI app + pipeline orchestrator
├── requirements.txt
├── Dockerfile
├── .env                       # API keys (add yours here)
├── test_api.py                # API test suite
├── config/
│   ├── README.md              # 📚 Complete configuration documentation
│   ├── default_rbi_config.json        # Default RBI banking config
│   ├── example_telecom_config.json    # Telecom/TRAI config
│   ├── example_insurance_config.json  # Insurance/IRDAI config
│   └── example_healthcare_config.json # Healthcare/HIPAA config
├── data/
│   └── policies/
│       ├── rbi_recovery_guidelines.txt
│       ├── nbfc_fair_practices.txt
│       └── internal_policies.txt
├── models/
│   ├── schemas.py             # Pydantic v2 response models
│   └── client_config.py       # 🆕 Client configuration schema & validation
└── services/
    ├── audio_processor.py     # librosa acoustic analysis + time violation check
    ├── transcriber.py         # Gemini multimodal transcription
    ├── rag_engine.py          # ChromaDB + LangChain RAG pipeline
    ├── compliance_engine.py   # 🔧 Config-aware agentic compliance reasoner
    └── json_builder.py        # Final JSON assembler
```
