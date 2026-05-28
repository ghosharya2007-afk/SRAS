"""
SRAS Gemini AI Service
======================
Three Gemini use cases:
  1. Request Classification — auto-detect type, severity, urgency
  2. Situation Report (SITREP) — operational summary for admins
  3. Zone Demand Forecast — predict demand for next 4 hours
"""

import json
import os
import traceback
from datetime import datetime, timezone
from typing import Optional

import google.generativeai as genai

# Configure on module load
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def _get_model(model_name: str = "gemini-1.5-flash"):
    """Get a Gemini model instance with safety settings."""
    return genai.GenerativeModel(
        model_name,
        generation_config=genai.GenerationConfig(
            temperature=0.3,
            max_output_tokens=1024,
        ),
    )


def _parse_json_safe(text: str) -> Optional[dict]:
    """Extract JSON from Gemini response, handling markdown code blocks."""
    cleaned = text.strip()
    # Remove markdown code fences if present
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Remove first and last lines (fences)
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start:end])
            except json.JSONDecodeError:
                return None
    return None


# ─── USE CASE 1: Request Classification ─────────────────────────

async def analyze_request(user_text: str) -> dict:
    """
    Analyze emergency request text using Gemini.
    Returns structured classification with type, severity, keywords.
    
    Fallback: returns default moderate-severity classification on error.
    """
    fallback = {
        "type": "food",
        "severity": 5,
        "urgency_keywords": [],
        "confidence": 0.0,
        "reasoning": "AI classification unavailable — using default values",
    }

    if not GEMINI_API_KEY:
        return {**fallback, "reasoning": "Gemini API key not configured"}

    prompt = f"""You are an emergency triage AI for a disaster response system.
Analyze the following emergency request and return ONLY a valid JSON object 
with no markdown, no explanation.

Request text: "{user_text}"

Return exactly:
{{
  "type": "food" or "medical" or "shelter" or "critical",
  "severity": <integer 1-10>,
  "urgency_keywords": ["word1", "word2"],
  "confidence": <float 0.0-1.0>,
  "reasoning": "<one sentence>"
}}

Severity guide:
1-3: Non-urgent, stable situation
4-6: Moderate urgency, worsening conditions
7-8: High urgency, at-risk individuals (children, elderly, disabled)
9-10: Life-threatening, immediate action required (cardiac, trauma, bleeding)

Category guide:
- "food": hunger, water, nutrition needs
- "shelter": housing, displacement, exposure to elements
- "medical": illness, injury, medication needs (non-life-threatening)
- "critical": life-threatening emergencies (cardiac arrest, severe trauma, drowning)"""

    try:
        model = _get_model("gemini-1.5-flash")
        response = model.generate_content(prompt)
        parsed = _parse_json_safe(response.text)

        if parsed and "type" in parsed and "severity" in parsed:
            # Validate and clamp values
            parsed["severity"] = max(1, min(10, int(parsed["severity"])))
            parsed["confidence"] = max(0.0, min(1.0, float(parsed.get("confidence", 0.5))))
            if parsed["type"] not in ("food", "medical", "shelter", "critical"):
                parsed["type"] = "food"
            return parsed
        else:
            return {**fallback, "reasoning": "AI returned unparseable response"}

    except Exception as e:
        traceback.print_exc()
        return {**fallback, "reasoning": f"AI error: {str(e)[:100]}"}


# ─── USE CASE 2: Situation Report (SITREP) ──────────────────────

async def generate_sitrep(stats: dict) -> dict:
    """
    Generate a professional SITREP from current operational data.
    Uses Gemini 1.5 Pro for better reasoning.
    """
    fallback_report = (
        "## SITREP — Manual Report Required\n\n"
        "AI situation report generation is currently unavailable.\n"
        "Please review the dashboard metrics manually."
    )

    if not GEMINI_API_KEY:
        return {"report": fallback_report, "generated_at": datetime.now(timezone.utc).isoformat()}

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    stats_json = json.dumps(stats, indent=2, default=str)

    prompt = f"""You are an emergency operations coordinator AI.
Generate a professional SITREP (Situation Report) based on this real-time operational data.

Current timestamp: {timestamp}

OPERATIONAL DATA:
{stats_json}

Format your response as:

## SITREP — {timestamp}

**SITUATION OVERVIEW**
[2 sentences on current state]

**CRITICAL ITEMS** (bullet list, max 4)

**RESOURCE STATUS**
[1-2 sentences]

**RECOMMENDED IMMEDIATE ACTION**
[1 specific, actionable recommendation]

**FORECAST (next 4 hours)**
[1 sentence prediction]"""

    try:
        model = _get_model("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return {
            "report": response.text,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        traceback.print_exc()
        return {
            "report": f"{fallback_report}\n\nError: {str(e)[:200]}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


# ─── USE CASE 3: Zone Demand Forecast ───────────────────────────

async def forecast_zone_demand(zone_id: str, historical_data: list, weather: str = "clear") -> dict:
    """
    Predict demand for a zone based on historical patterns.
    Returns structured forecast with risk level and recommendations.
    """
    fallback = {
        "predicted_requests": {"food": 0, "medical": 0, "shelter": 0},
        "recommendation": "Insufficient data for AI forecast. Monitor manually.",
        "risk_level": "MEDIUM",
        "reasoning": "AI forecast unavailable",
    }

    if not GEMINI_API_KEY:
        return fallback

    now = datetime.now(timezone.utc)
    day_of_week = now.strftime("%A")
    hour = now.strftime("%H")

    prompt = f"""Emergency resource demand analyst AI.
Analyze this zone's request history and provide a forecast.

Zone: {zone_id}
Current time: {day_of_week}, {hour}:00
Last 7 days daily request counts by type:
{json.dumps(historical_data, indent=2)}
Weather condition: {weather}

Provide:
1. Predicted demand for next 4 hours (as numbers by type)
2. One specific pre-positioning recommendation
3. Risk level: LOW / MEDIUM / HIGH / CRITICAL

Reply ONLY with valid JSON:
{{
  "predicted_requests": {{ "food": <int>, "medical": <int>, "shelter": <int> }},
  "recommendation": "<specific action string>",
  "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
  "reasoning": "<one sentence>"
}}"""

    try:
        model = _get_model("gemini-1.5-flash")
        response = model.generate_content(prompt)
        parsed = _parse_json_safe(response.text)
        if parsed and "predicted_requests" in parsed:
            if parsed.get("risk_level") not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
                parsed["risk_level"] = "MEDIUM"
            return parsed
        return fallback
    except Exception as e:
        traceback.print_exc()
        return {**fallback, "reasoning": f"AI error: {str(e)[:100]}"}
