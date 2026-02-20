"""
Vigilant – RBI Compliance Intelligence API
Main FastAPI application entry point.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import aiofiles
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile, Security, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
POLICIES_DIR = os.getenv("POLICIES_DIR", "./data/policies")
DEFAULT_CONFIG_PATH = Path(__file__).parent / "config" / "default_rbi_config.json"

# API Authentication Configuration
# Set VIGILANT_API_KEYS environment variable with comma-separated keys
# Example: VIGILANT_API_KEYS="key1,key2,key3"
# If not set, authentication is DISABLED (for development only)
VIGILANT_API_KEYS = os.getenv("VIGILANT_API_KEYS", "")
API_KEY_ENABLED = bool(VIGILANT_API_KEYS)
VALID_API_KEYS = set(k.strip() for k in VIGILANT_API_KEYS.split(",") if k.strip()) if API_KEY_ENABLED else set()

# Service imports
from services.audio_processor import analyze_audio, check_time_violation
from services.transcriber import transcribe_and_analyze
from services.rag_engine import initialize_policy_store, retrieve_relevant_clauses
from services.compliance_engine import run_compliance_analysis
from services.json_builder import build_output_json

# Configuration management
from models.client_config import ConfigManager, ClientConfig
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Default config loader
# ---------------------------------------------------------------------------

def _load_default_config() -> dict:
    """Load default configuration from JSON file."""
    with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _validate_and_merge_config(uploaded_config: Optional[dict]) -> dict:
    """
    Validate and merge uploaded config with default config.
    
    Args:
        uploaded_config: Optional uploaded client configuration
        
    Returns:
        Merged and validated configuration dictionary
        
    Raises:
        HTTPException: If configuration validation fails
    """
    default_config = _load_default_config()
    
    if uploaded_config is None:
        try:
            # Validate default config
            ConfigManager.validate_config(default_config)
            return default_config
        except ValidationError as e:
            print(f"[Config] WARNING: Default config validation failed: {e}")
            return default_config  # Continue with unvalidated default
    
    # Merge uploaded with default
    merged = ConfigManager.merge_configs(default_config, uploaded_config)
    
    try:
        # Validate merged config
        validated = ConfigManager.validate_config(merged)
        print(f"[Config] Configuration validated successfully: {validated.organization_name}")
        return merged
    except ValidationError as e:
        error_details = "; ".join([f"{err['loc'][0]}: {err['msg']}" for err in e.errors()])
        raise HTTPException(
            status_code=400,
            detail=f"Configuration validation failed: {error_details}"
        )
    


# ---------------------------------------------------------------------------
# API Key Authentication
# ---------------------------------------------------------------------------

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def validate_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """
    Validate API key from X-API-Key header.
    
    If VIGILANT_API_KEYS environment variable is not set, authentication is disabled.
    If set, validates the provided API key against the configured keys.
    
    Args:
        api_key: API key from X-API-Key header
        
    Returns:
        The validated API key
        
    Raises:
        HTTPException: If authentication is required and key is invalid
    """
    if not API_KEY_ENABLED:
        # Authentication disabled - allow all requests
        return "auth_disabled"
    
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    if api_key not in VALID_API_KEYS:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key.",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    return api_key


# ---------------------------------------------------------------------------
# Supported audio extensions
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".flac", ".webm", ".mp4"}


# ---------------------------------------------------------------------------
# FastAPI lifespan – initialize RAG store once at startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the RAG policy vector store at startup."""
    print("[Vigilant] Starting up – initializing RAG policy store...")
    
    # Authentication status
    if API_KEY_ENABLED:
        print(f"[Vigilant] API Authentication: ENABLED ({len(VALID_API_KEYS)} key(s) configured)")
        print("[Vigilant] Requests to /analyze require X-API-Key header")
    else:
        print("[Vigilant] API Authentication: DISABLED (set VIGILANT_API_KEYS to enable)")
    
    if not GOOGLE_API_KEY:
        print("[Vigilant] WARNING: GOOGLE_API_KEY not set. RAG and LLM calls will fail.")
    else:
        try:
            initialize_policy_store(POLICIES_DIR, GOOGLE_API_KEY)
            print("[Vigilant] RAG policy store ready.")
        except Exception as exc:
            print(f"[Vigilant] WARNING: Could not initialize RAG store: {exc}")
    yield
    print("[Vigilant] Shutting down.")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Vigilant – RBI Compliance Intelligence",
    description=(
        "Automated multimodal compliance officer for banks. "
        "Analyzes debt recovery call recordings for policy violations, "
        "emotional tone, and agent conduct. Returns structured JSON audit reports."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["System"])
async def health_check():
    """Returns service health status."""
    return {"status": "ok", "service": "Vigilant", "version": "1.0.0"}


@app.get("/", tags=["System"])
async def root():
    return {
        "service": "Vigilant – RBI Compliance Intelligence API",
        "docs": "/docs",
        "health": "/health",
        "analyze": "POST /analyze",
    }


@app.post("/analyze", tags=["Analysis"])
async def analyze_call(
    audio_file: UploadFile = File(..., description="Call recording (.mp3/.wav/.ogg/.m4a)"),
    client_config: Optional[UploadFile] = File(
        default=None,
        description="Client ethics configuration JSON (optional)",
    ),
    api_key: str = Depends(validate_api_key),
):
    """
    Analyze a debt recovery call recording for RBI compliance violations.

    - **audio_file**: The call recording (mp3, wav, ogg, m4a, flac supported)
    - **client_config**: Optional JSON file with bank-specific policy rules
    - **Authentication**: Requires X-API-Key header (if VIGILANT_API_KEYS env var is set)

    Returns a complete compliance audit JSON report.
    """
    if not GOOGLE_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="GOOGLE_API_KEY is not configured. Cannot process request.",
        )

    # Validate audio file extension
    suffix = Path(audio_file.filename or "file.mp3").suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format '{suffix}'. Supported: {SUPPORTED_EXTENSIONS}",
        )

    return await _run_analysis_pipeline(audio_file, client_config)


# ---------------------------------------------------------------------------
# Pipeline orchestrator
# ---------------------------------------------------------------------------

async def _run_analysis_pipeline(
    audio_upload: UploadFile,
    config_upload: Optional[UploadFile],
) -> JSONResponse:
    """
    Full analysis pipeline:
    1. Save audio to temp file
    2. Load client config (or use default)
    3. Run acoustic analysis + transcription (can overlap)
    4. Check time violation
    5. Retrieve relevant RAG clauses
    6. Run agentic compliance analysis
    7. Assemble and return final JSON
    """
    request_id = f"REQ-{uuid.uuid4().hex[:6].upper()}-MA"
    start_time = time.time()
    tmp_audio_path: Optional[str] = None

    try:
        # -- Step 1: Save uploaded audio to temp file --
        suffix = Path(audio_upload.filename or "audio.mp3").suffix.lower()
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=suffix, prefix=f"vigilant_{request_id}_"
        ) as tmp:
            tmp_audio_path = tmp.name
            content = await audio_upload.read()
            tmp.write(content)
        print(f"[Pipeline] [{request_id}] Audio saved: {tmp_audio_path} ({len(content)} bytes)")

        # -- Step 2: Load and validate config --
        uploaded_config_dict = None
        if config_upload is not None:
            config_content = await config_upload.read()
            try:
                uploaded_config_dict = json.loads(config_content.decode("utf-8"))
                print(f"[Pipeline] [{request_id}] Custom config uploaded")
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="client_config is not valid JSON.")
        
        # Validate and merge with default
        merged_config = _validate_and_merge_config(uploaded_config_dict)
        
        print(
            f"[Pipeline] [{request_id}] Config applied: {merged_config.get('organization_name')} | "
            f"Policy Set: {merged_config.get('active_policy_set')} | "
            f"Domain: {merged_config.get('business_domain')}"
        )

        # -- Step 3a: Acoustic analysis --
        print(f"[Pipeline] [{request_id}] Running acoustic analysis...")
        acoustic_segments = analyze_audio(tmp_audio_path)
        print(f"[Pipeline] [{request_id}] Acoustic: {len(acoustic_segments)} segments")

        # -- Step 3b: Gemini transcription + language detection --
        print(f"[Pipeline] [{request_id}] Running Gemini transcription...")
        transcription_result = transcribe_and_analyze(tmp_audio_path, GOOGLE_API_KEY)
        print(
            f"[Pipeline] [{request_id}] Transcript: "
            f"{len(transcription_result.get('transcript_threads', []))} turns"
        )

        # -- Step 4: Check time violation --
        from datetime import datetime, timezone
        call_timestamp_utc = datetime.now(timezone.utc).isoformat()
        time_violation_result = check_time_violation(call_timestamp_utc)
        if time_violation_result["violation"]:
            print(
                f"[Pipeline] [{request_id}] TIME VIOLATION at {time_violation_result['ist_time']} IST"
            )

        # -- Step 5: RAG clause retrieval --
        print(f"[Pipeline] [{request_id}] Retrieving policy clauses via RAG...")
        retrieved_clauses = retrieve_relevant_clauses(
            transcript_threads=transcription_result.get("transcript_threads", []),
            api_key=GOOGLE_API_KEY,
            client_config=merged_config,
        )

        # -- Step 6: Agentic compliance analysis --
        print(f"[Pipeline] [{request_id}] Running agentic compliance analysis...")
        compliance_result = run_compliance_analysis(
            transcript_threads=transcription_result.get("transcript_threads", []),
            acoustic_segments=acoustic_segments,
            retrieved_clauses=retrieved_clauses,
            client_config=merged_config,
            call_timestamp_utc=call_timestamp_utc,
            time_violation_result=time_violation_result,
            api_key=GOOGLE_API_KEY,
        )

        # -- Step 7: Assemble final JSON --
        final_output = build_output_json(
            request_id=request_id,
            call_timestamp_utc=call_timestamp_utc,
            processing_start_time=start_time,
            transcription_result=transcription_result,
            acoustic_segments=acoustic_segments,
            compliance_result=compliance_result,
            time_violation_result=time_violation_result,
            client_config=merged_config,
        )

        elapsed = time.time() - start_time
        print(f"[Pipeline] [{request_id}] Complete in {elapsed:.2f}s")
        return JSONResponse(content=final_output)

    except HTTPException:
        raise
    except Exception as exc:
        print(f"[Pipeline] [{request_id}] ERROR: {exc}")
        raise HTTPException(status_code=500, detail=f"Analysis pipeline error: {str(exc)}")
    finally:
        # Clean up temp audio file
        if tmp_audio_path and Path(tmp_audio_path).exists():
            try:
                Path(tmp_audio_path).unlink()
            except Exception:
                pass
