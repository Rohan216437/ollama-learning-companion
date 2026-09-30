"""Wraps the local Ollama HTTP API to generate structured study material from a transcript."""
import json
import logging
import os
import re
import requests

logger = logging.getLogger(__name__)

# Configurable defaults via environment variables
DEFAULT_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
DEFAULT_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "300"))
DEFAULT_TEMPERATURE = float(os.environ.get("OLLAMA_TEMPERATURE", "0.2"))
DEFAULT_MAX_TRANSCRIPT_CHARS = int(os.environ.get("OLLAMA_MAX_TRANSCRIPT_CHARS", "45000"))

PROMPT_TEMPLATE = """You are an expert teacher creating educational study material from a YouTube video transcript.

Video title: {title}

Transcript:
\"\"\"
{transcript}
\"\"\"

Based ONLY on the transcript above, produce educational study material for a student.
- Use only the supplied transcript.
- Do not invent unsupported information.
- Generate educational material.
- Keep the content concise and useful.
- Avoid duplicate key points.
- Glossary definitions must be student-friendly.
- Flashcards must test meaningful concepts.
- Quiz questions must be answerable from the transcript.
- Exactly 4 options per question.
- Only one correct answer.
- correct_index must match the correct option.
- Return ONLY JSON.
- Do not return Markdown.
- Do not return ```json fences.

Respond with STRICT JSON matching exactly this schema:
{{
  "summary": "A clear, concise summary of the video content based strictly on the transcript.",
  "key_points": [
    "Key point 1",
    "Key point 2"
  ],
  "glossary": [
    {{
      "term": "Technical term",
      "definition": "One-sentence student-friendly definition"
    }}
  ],
  "flashcards": [
    {{
      "front": "Question or core concept",
      "back": "Answer or explanation"
    }}
  ],
  "quiz": [
    {{
      "question": "Question text directly answerable from transcript",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_index": 0,
      "explanation": "One sentence explaining why this is the correct answer based on the transcript."
    }}
  ]
}}

Requirements:
- summary: clear summary of the video.
- key_points: 6-10 items.
- glossary: 4-8 technical terms specific to the video.
- flashcards: 8-12 items.
- quiz: 5-8 questions.
- Each quiz question must have exactly 4 options.
- correct_index must be an integer between 0 and 3.
- explanation is required for each question.
- Output must be valid JSON parsable by json.loads.
"""

OLLAMA_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "key_points": {
            "type": "array",
            "items": {"type": "string"}
        },
        "glossary": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "term": {"type": "string"},
                    "definition": {"type": "string"}
                },
                "required": ["term", "definition"]
            }
        },
        "flashcards": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "front": {"type": "string"},
                    "back": {"type": "string"}
                },
                "required": ["front", "back"]
            }
        },
        "quiz": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "options": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "correct_index": {"type": "integer"},
                    "explanation": {"type": "string"}
                },
                "required": ["question", "options", "correct_index", "explanation"]
            }
        }
    },
    "required": ["summary", "key_points", "glossary", "flashcards", "quiz"]
}


class OllamaGenerationError(Exception):
    """Raised when Ollama request, parsing, or validation fails."""
    pass


def _extract_json(raw_text: str) -> dict:
    """Strip any markdown fences or surrounding commentary and parse JSON."""
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"\s*```$", "", text).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback: locate outermost JSON object
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def _validate_material(data: dict) -> dict:
    """Validate and sanitize structured study material from Ollama."""
    if not isinstance(data, dict):
        raise OllamaGenerationError("Model response is not a valid JSON object.")

    # 1. Summary
    summary = str(data.get("summary", "")).strip()
    if not summary:
        raise OllamaGenerationError("Model response did not contain a valid summary.")

    # 2. Key points
    raw_kp = data.get("key_points")
    if not isinstance(raw_kp, list) or len(raw_kp) == 0:
        raise OllamaGenerationError("Model response missing key_points.")
    key_points = [str(item).strip() for item in raw_kp if str(item).strip()]
    if not key_points:
        raise OllamaGenerationError("Model response produced no valid key points.")

    # 3. Glossary
    raw_gl = data.get("glossary")
    if not isinstance(raw_gl, list):
        raise OllamaGenerationError("Model response missing glossary.")
    glossary = []
    for item in raw_gl:
        if isinstance(item, dict) and item.get("term") and item.get("definition"):
            glossary.append({
                "term": str(item["term"]).strip(),
                "definition": str(item["definition"]).strip()
            })

    # 4. Flashcards
    raw_fc = data.get("flashcards")
    if not isinstance(raw_fc, list):
        raise OllamaGenerationError("Model response missing flashcards.")
    flashcards = []
    for item in raw_fc:
        if isinstance(item, dict) and item.get("front") and item.get("back"):
            flashcards.append({
                "front": str(item["front"]).strip(),
                "back": str(item["back"]).strip()
            })

    # 5. Quiz
    raw_quiz = data.get("quiz")
    if not isinstance(raw_quiz, list) or len(raw_quiz) == 0:
        raise OllamaGenerationError("Model response missing quiz questions.")

    quiz = []
    for item in raw_quiz:
        if not isinstance(item, dict):
            continue
        q = str(item.get("question", "")).strip()
        options = item.get("options")
        correct_index = item.get("correct_index")
        explanation = str(item.get("explanation", "")).strip()

        if not q or not isinstance(options, list) or len(options) != 4:
            continue

        clean_options = [str(opt).strip() for opt in options]
        if any(not opt for opt in clean_options):
            continue

        try:
            c_idx = int(correct_index)
        except (TypeError, ValueError):
            continue

        if c_idx not in (0, 1, 2, 3):
            continue

        quiz.append({
            "question": q,
            "options": clean_options,
            "correct_index": c_idx,
            "explanation": explanation or f"Option {chr(65 + c_idx)} is the correct answer based on the video."
        })

    if not quiz:
        raise OllamaGenerationError(
            "Invalid quiz structure generated: questions must have exactly 4 options and valid correct_index (0-3)."
        )

    return {
        "summary": summary,
        "key_points": key_points,
        "glossary": glossary,
        "flashcards": flashcards,
        "quiz": quiz,
    }


def generate_learning_material(
    transcript: str,
    video_title: str,
    base_url: str = None,
    model_name: str = None,
    timeout: int = None,
    temperature: float = None,
    max_chars: int = None,
) -> dict:
    """Call Ollama /api/chat to generate structured study material from transcript."""
    base_url = (base_url or os.environ.get("OLLAMA_BASE_URL", DEFAULT_BASE_URL)).rstrip("/")
    model_name = model_name or os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL)
    timeout = int(timeout if timeout is not None else os.environ.get("OLLAMA_TIMEOUT", DEFAULT_TIMEOUT))
    temperature = float(temperature if temperature is not None else os.environ.get("OLLAMA_TEMPERATURE", DEFAULT_TEMPERATURE))
    max_chars = int(max_chars if max_chars is not None else os.environ.get("OLLAMA_MAX_TRANSCRIPT_CHARS", DEFAULT_MAX_TRANSCRIPT_CHARS))

    trimmed_transcript = transcript[:max_chars] if transcript else ""
    prompt = PROMPT_TEMPLATE.format(title=video_title or "Untitled video", transcript=trimmed_transcript)

    chat_url = f"{base_url}/api/chat"
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "system",
                "content": "You are a professional educational assistant that strictly outputs structured JSON matching the requested schema."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "stream": False,
        "format": OLLAMA_JSON_SCHEMA,
        "options": {
            "temperature": temperature
        }
    }

    try:
        response = requests.post(chat_url, json=payload, timeout=timeout)
    except requests.exceptions.ConnectionError:
        raise OllamaGenerationError(
            f"Local AI service is unavailable. Please make sure Ollama is running at {base_url}."
        )
    except requests.exceptions.Timeout:
        raise OllamaGenerationError(
            f"Local AI service timed out ({timeout}s). The model took too long to generate study material."
        )
    except requests.exceptions.RequestException as exc:
        raise OllamaGenerationError(f"Local AI request failed: {exc}")

    # If the model or Ollama version does not support schema format, fall back to "format": "json"
    if response.status_code == 400 and isinstance(payload.get("format"), dict):
        payload["format"] = "json"
        try:
            response = requests.post(chat_url, json=payload, timeout=timeout)
        except requests.exceptions.RequestException as exc:
            raise OllamaGenerationError(f"Local AI request failed: {exc}")

    if response.status_code == 404:
        raise OllamaGenerationError(
            f"Configured Ollama model '{model_name}' was not found. Please run 'ollama pull {model_name}'."
        )
    if response.status_code != 200:
        err_detail = ""
        try:
            err_detail = response.json().get("error", response.text)
        except Exception:
            err_detail = response.text
        raise OllamaGenerationError(
            f"Ollama returned an error (status {response.status_code}): {err_detail}"
        )

    try:
        resp_data = response.json()
    except Exception as exc:
        raise OllamaGenerationError(f"Ollama returned an invalid response: {exc}")

    raw_text = resp_data.get("message", {}).get("content", "")
    if not raw_text or not raw_text.strip():
        raise OllamaGenerationError("Ollama returned an empty response.")

    try:
        data = _extract_json(raw_text)
    except (json.JSONDecodeError, AttributeError) as exc:
        raise OllamaGenerationError(f"Could not parse Ollama's response as JSON: {exc}")

    return _validate_material(data)


# Alias for backward compatibility
generate_study_material = generate_learning_material
