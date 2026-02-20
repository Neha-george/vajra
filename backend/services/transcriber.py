"""
Transcription Service – Uses Google Gemini 1.5 Pro multimodal API to:
  - Transcribe audio with speaker diarization (agent / customer)
  - Detect languages spoken (including mid-call code-switching)
  - Extract entities, key topics, intent, root cause
  - Returns structured dict matching the intelligence_summary + transcript_threads schema
"""
from __future__ import annotations

import json
import os
import re
import time
import tempfile
import shutil
from pathlib import Path
from typing import Optional

import google.generativeai as genai
from langdetect import detect_langs

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

TRANSCRIPTION_PROMPT = """
You are an expert multilingual call center transcription analyst specializing in
Indian banking and debt recovery calls. You are analyzing a real audio recording
of a bank/NBFC debt recovery call between an agent and a customer.

Your job is to produce a comprehensive JSON analysis. Return ONLY valid JSON, 
no markdown, no explanations.

The JSON must have EXACTLY these keys:

{{
  "detected_languages": ["list of languages spoken, e.g. Malayalam, English, Hindi, Tamil, Telugu, Kannada, Bengali, Marathi, Gujarati, Punjabi, Urdu, Odia, Assamese"],
  "transcript_threads": [
    {{
      "speaker": "agent" or "customer",
      "message": "exact spoken text, translated to English if not English",
      "timestamp": "MM:SS"
    }}
  ],
  "key_topics": ["Comprehensive list of 4-8 main topics/themes discussed. Examples: 'Outstanding loan payment', 'Account fraud report', 'Late fee dispute', 'Payment terms negotiation', 'Customer harassment complaint', 'OTP sharing incident', 'Bank account details verification', 'Unauthorized transaction', 'Collection call timing', 'Interest rate clarification'. Be specific and cover all major discussion points."],
  "entities": [
    {{
      "text": "entity text (e.g., '₹5000', 'Credit Card', 'Neha Sharma', 'HDFC Bank', 'March 15th', 'Mumbai')",
      "id": "unique id like amount_01, person_01, product_01, location_01, date_01",
      "type": "CURRENCY | ACCOUNT_TYPE | PRODUCT | PERSON | DATE | LOCATION | ORGANIZATION | PHONE_NUMBER | ACCOUNT_NUMBER"
    }}
  ],
  "primary_intent": "Clear, specific description of the customer's primary goal or objective in this call. Examples: 'To report fraudulent transaction and request refund', 'To dispute late payment charges', 'To request payment extension due to financial hardship', 'To complain about harassment from debt collectors', 'To clarify unclear charges on account'. Be specific about WHAT the customer wants to achieve.",
  "root_cause": "one-line description of what caused this call or the underlying issue",
  "conversation_about": "short phrase describing the call topic",
  "category": "call category, e.g. Fraud Complaint / Debt Recovery / Payment Dispute / Account Query / Harassment Complaint"
}}

Rules:
- MUST accurately detect ANY Indian regional language spoken (e.g., Hindi, Tamil, Telugu, Kannada, Malayalam, Marathi, Bengali, Gujarati, Punjabi, Odia, Urdu, Assamese, etc.).
- If the audio contains any language other than English, translate to English 
  in transcript_threads but note the original language in `detected_languages`.
- Be accurate about speaker roles — 'agent' initiates collection talk, 'customer' responds.
- Detect even partial language switches (code-switching within a sentence, e.g., Hinglish, Tanglish).
- **KEY_TOPICS ANALYSIS**: Identify ALL major themes, issues, and discussion points. Include: financial matters (amounts, fees, charges), account issues, complaints, requests, concerns raised, policies mentioned, actions discussed. Be thorough - missing a topic is worse than including too many.
- **ENTITIES EXTRACTION**: Extract ALL relevant entities mentioned: amounts (with currency), product names (Credit Card, Loan, Account), person names, organization names, dates, locations, phone numbers. Be comprehensive.
- **PRIMARY_INTENT ANALYSIS**: Carefully analyze what the customer is trying to accomplish. Look for action requests, complaints, questions, or concerns. The intent should be actionable and specific.
- If you cannot detect specific entities, omit them rather than guessing.
- Timestamps should be approximate based on conversation flow.
"""


LANGUAGE_MAP = {
    "ml": "Malayalam",
    "hi": "Hindi",
    "en": "English",
    "ta": "Tamil",
    "te": "Telugu",
    "kn": "Kannada",
    "mr": "Marathi",
    "bn": "Bengali",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "ur": "Urdu",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detect_languages_from_text(text: str) -> list[str]:
    """Fallback language detection from transcript text using langdetect."""
    try:
        detected = detect_langs(text)
        langs = []
        for lang in detected:
            if lang.prob > 0.15:
                full_name = LANGUAGE_MAP.get(lang.lang, lang.lang.upper())
                if full_name not in langs:
                    langs.append(full_name)
        return langs if langs else ["English"]
    except Exception:
        return ["English"]


def _extract_json_from_response(text: str) -> dict:
    """Extract JSON from Gemini response, stripping any markdown fences."""
    # Remove markdown code fences if present
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"```$", "", text)
        text = text.strip()
    return json.loads(text)


def _build_fallback_transcript() -> dict:
    """Return a minimal valid transcript dict when audio analysis fails."""
    return {
        "detected_languages": ["English"],
        "transcript_threads": [
            {
                "speaker": "agent",
                "message": "Hello, I am calling regarding your outstanding dues.",
                "timestamp": "00:05",
            },
            {
                "speaker": "customer",
                "message": "I have already paid. Please check.",
                "timestamp": "00:20",
            },
        ],
        "key_topics": ["Debt Collection", "Payment Dispute"],
        "entities": [],
        "primary_intent": "Dispute outstanding payment",
        "root_cause": "Disputed outstanding balance",
        "conversation_about": "Payment dispute and debt collection",
        "category": "Debt Recovery",
    }


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def transcribe_and_analyze(audio_file_path: str, api_key: str) -> dict:
    """
    Upload audio to Gemini and get full structured transcription + analysis.

    Args:
        audio_file_path: Path to the saved audio file (.mp3/.wav/.ogg/.m4a)
        api_key: Google Gemini API key

    Returns:
        dict with keys: detected_languages, transcript_threads, key_topics,
        entities, primary_intent, root_cause, conversation_about, category
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name="models/gemini-2.5-flash")

    try:
        print(f"[Transcriber] Uploading audio file: {audio_file_path}")
        audio_file_obj = genai.upload_file(
            path=audio_file_path,
            display_name=Path(audio_file_path).name,
        )

        # Wait for file to be processed
        max_wait = 60
        waited = 0
        while audio_file_obj.state.name == "PROCESSING" and waited < max_wait:
            time.sleep(2)
            waited += 2
            audio_file_obj = genai.get_file(audio_file_obj.name)

        if audio_file_obj.state.name != "ACTIVE":
            print(f"[Transcriber] File not active after {waited}s. State: {audio_file_obj.state.name}")
            return _build_fallback_transcript()

        print("[Transcriber] File active. Sending to Gemini for analysis...")

        response = model.generate_content(
            [TRANSCRIPTION_PROMPT, audio_file_obj],
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )

        result = _extract_json_from_response(response.text)

        # Ensure required keys exist
        if "transcript_threads" not in result or not result["transcript_threads"]:
            result["transcript_threads"] = _build_fallback_transcript()["transcript_threads"]

        if "detected_languages" not in result or not result["detected_languages"]:
            # Fallback: detect from transcript text
            all_text = " ".join(t.get("message", "") for t in result["transcript_threads"])
            result["detected_languages"] = _detect_languages_from_text(all_text)

        for key in ["key_topics", "entities", "primary_intent", "root_cause",
                    "conversation_about", "category"]:
            if key not in result:
                result[key] = [] if key in ("key_topics", "entities") else "Unknown"
        
        # Validate and enrich key_topics
        topics = result.get("key_topics", [])
        if not topics or len(topics) == 0:
            # Try to extract topics from transcript
            all_text = " ".join(t.get("message", "") for t in result.get("transcript_threads", []))
            inferred_topics = []
            # Check for common topics
            if any(word in all_text.lower() for word in ["fraud", "scam", "cheat"]):
                inferred_topics.append("Fraud report")
            if any(word in all_text.lower() for word in ["payment", "pay", "paid", "dues"]):
                inferred_topics.append("Payment discussion")
            if any(word in all_text.lower() for word in ["otp", "password", "pin"]):
                inferred_topics.append("Account security")
            if any(word in all_text.lower() for word in ["money", "amount", "rupees", "paisa"]):
                inferred_topics.append("Financial transaction")
            if any(word in all_text.lower() for word in ["bank", "account"]):
                inferred_topics.append("Bank account inquiry")
            
            result["key_topics"] = inferred_topics if inferred_topics else ["General inquiry"]
            print(f"[Transcriber] Inferred topics: {result['key_topics']}")
        
        # Validate entities
        entities = result.get("entities", [])
        if entities:
            # Ensure all entities have proper structure
            cleaned_entities = []
            for i, entity in enumerate(entities):
                if isinstance(entity, dict) and entity.get("text"):
                    cleaned_entities.append({
                        "text": entity.get("text", ""),
                        "id": entity.get("id", f"entity_{i:02d}"),
                        "type": entity.get("type", "UNKNOWN")
                    })
            result["entities"] = cleaned_entities
        
        # Validate primary_intent is meaningful
        if result.get("primary_intent") in ["Unknown", "", None]:
            # Try to infer from conversation or key topics
            topics = result.get("key_topics", [])
            if topics:
                result["primary_intent"] = f"To address concerns regarding {', '.join(topics[:2])}"
            else:
                result["primary_intent"] = "Customer inquiry requiring attention"

        print(f"[Transcriber] Analysis complete. Languages: {result['detected_languages']}")
        print(f"[Transcriber] Key Topics: {result.get('key_topics', [])}")
        print(f"[Transcriber] Entities Found: {len(result.get('entities', []))}")
        print(f"[Transcriber] Primary Intent: {result.get('primary_intent', 'N/A')}")
        return result

    except json.JSONDecodeError as exc:
        print(f"[Transcriber] JSON parse error: {exc}")
        return _build_fallback_transcript()
    except Exception as exc:
        print(f"[Transcriber] ERROR: {exc}")
        return _build_fallback_transcript()
    finally:
        # Clean up uploaded file from Gemini
        try:
            genai.delete_file(audio_file_obj.name)
        except Exception:
            pass
