from __future__ import annotations
import os, json, time, hashlib, random
from dataclasses import dataclass
from typing import List, Dict, Any
from flask import Blueprint, render_template, request, jsonify

# Optional: use OpenAI official client if available; else fall back to requests
USE_OFFICIAL = True
try:
    from openai import OpenAI  # pip install openai
except Exception:
    USE_OFFICIAL = False
import requests

assignment_bp = Blueprint("assignment", __name__)

# --------------------------
# Config
# --------------------------
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
MODEL_QUESTIONS = os.environ.get("ASSIGNMENT_QUESTION_MODEL", "gpt-4o-mini")
MODEL_GRADING   = os.environ.get("ASSIGNMENT_GRADING_MODEL", "gpt-4o-mini")

def _client():
    if not OPENAI_API_KEY:
        return None
    if USE_OFFICIAL:
        return OpenAI(api_key=OPENAI_API_KEY)
    return None  # we'll call via requests if not official

def _chat_request(model: str, system_prompt: str, user_prompt: str, response_format: str | None = None) -> str:
    """
    Performs a chat request and returns the assistant content (string).
    If official client not installed, uses HTTPS requests fallback.
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("Missing OPENAI_API_KEY")

    if USE_OFFICIAL:
        client = _client()
        # Prefer Chat Completions for wide compatibility
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.6,
            response_format={"type": "json_object"} if response_format == "json" else None,
        )
        return resp.choices[0].message.content

    # Fallback: raw HTTPS
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "temperature": 0.6,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    if response_format == "json":
        payload["response_format"] = {"type": "json_object"}

    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"]

# --------------------------
# Helper: safe JSON parse
# --------------------------
def _safe_json(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        # Try stripping code fences if present
        t = text.strip()
        if t.startswith("```"):
            t = t.strip("`")
            # remove "json" language tag if any
            parts = t.split("\n", 1)
            if len(parts) == 2:
                t = parts[1]
        return json.loads(t)

# --------------------------
# Routes
# --------------------------
@assignment_bp.route("/assignment")
def assignment_home():
    return render_template("assignment.html")

@assignment_bp.route("/assignment/api/generate", methods=["POST"])
def assignment_generate():
    """
    Input JSON: { "name": "...", "neptun": "...", "language": "English|Hungarian|..." }
    Output JSON: { "seed": "...", "questions": [{"id":"Q1","text":"..."}, ...] }
    """
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    neptun = (data.get("neptun") or "").strip().upper()
    language = (data.get("language") or "English").strip()

    # unique-ish seed: hash of neptun + today's date
    today = time.strftime("%Y-%m-%d")
    seed_str = f"{neptun}|{today}|{random.randint(1000,9999)}"
    seed_hash = hashlib.sha256(seed_str.encode("utf-8")).hexdigest()[:12]

    # If API key missing, provide a deterministic fallback set (still unique-ish)
    if not OPENAI_API_KEY:
        random.seed(seed_hash)
        qs = [
            {"id": f"Q{i+1}",
             "text": f"[{language}] Describe, in 3–5 sentences, how you would use the Set Theory Minerals game to analyze {random.choice(['I Δ S','I ∩ M','S ∩ M','U \\ (I ∪ S ∪ M)','I \\ (S ∪ M)'])} for a chosen mineral. Explain your reasoning."}
            for i in range(10)
        ]
        return jsonify({"seed": seed_hash, "questions": qs})

    # Build prompt for GPT to emit JSON questions
    system_prompt = (
        "You are an educational content generator. "
        "You will produce exactly 10 open-ended, typing-only assignment questions in JSON. "
        "Context: A student will use an interactive Venn diagram game with sets I (Igneous), S (Sedimentary), M (Metamorphic); "
        "the game supports intersections (∩), differences (\\), symmetric differences (Δ), unions (∪), triple intersection, outside (complement). "
        "Questions must require descriptive reasoning about regions, not just numeric counts. "
        "Ensure at least 3 questions explicitly involve Δ, 1 involves the triple intersection, and 1 involves outside/complement. "
        "Students can write in any language; the instructor provides a preferred language. "
        "Return strict JSON with keys: questions:[{id:'Q1'..'Q10', text:'...'}]. No extra commentary."
    )

    user_prompt = f"""
Preferred language: {language}
Uniqueness token (seed): {seed_hash}
Student: {name or 'Anonymous'} / Neptun: {neptun or 'UNKNOWN'}

Constraints:
- 10 items, ids Q1..Q10
- Each requires a multi-sentence written description (2–6 sentences).
- Reference geology context and the specific regions they must reason about in the game.
- Avoid asking for uploads; screenshots optional wording is allowed once at most.
- No solutions. No rubric in output. JSON only.
- Use set symbols (∩, ∪, \\ , Δ, U) where relevant.
JSON only, structure:
{{
  "questions": [
    {{ "id": "Q1", "text": "..." }},
    ...
    {{ "id": "Q10", "text": "..." }}
  ]
}}
    """.strip()

    try:
        content = _chat_request(MODEL_QUESTIONS, system_prompt, user_prompt, response_format="json")
        obj = _safe_json(content)
        questions = obj.get("questions", [])
        # Basic sanity
        if not isinstance(questions, list) or len(questions) != 10:
            raise ValueError("Model did not return 10 questions.")
        for i, q in enumerate(questions, 1):
            q["id"] = f"Q{i}"
        return jsonify({"seed": seed_hash, "questions": questions})
    except Exception as e:
        # Fallback deterministic list on any error
        random.seed(seed_hash)
        qs = [
            {"id": f"Q{i+1}",
             "text": f"[{language}] Explain, in 2–5 sentences, insights from highlighting {random.choice(['I Δ S','I Δ M','S Δ M','I ∩ S','I ∩ S ∩ M','U \\ (I ∪ S ∪ M)'])} "
                     f"for two minerals of your choice. Link the region to geology."}
            for i in range(10)
        ]
        return jsonify({"seed": seed_hash, "questions": qs, "warning": "fallback_used"})

@assignment_bp.route("/assignment/api/grade", methods=["POST"])
def assignment_grade():
    """
    Input JSON:
    {
      "name": "...", "neptun": "...",
      "language": "English|...",
      "seed": "...",
      "qa": [{"id":"Q1","question":"...","answer":"..."} ...]  # 10 items
    }
    Output JSON:
    {
      "per_question":[{"id":"Q1","score":0-10,"feedback":"..."}...],
      "overall_pct": 0-100,
      "pass": true|false,
      "summary":"..."
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    neptun = (data.get("neptun") or "").strip().upper()
    language = (data.get("language") or "English").strip()
    qa = data.get("qa") or []

    # If no key, do a simple length-based heuristic (safe fallback).
    if not OPENAI_API_KEY:
        perq = []
        total = 0
        for item in qa:
            ans = (item.get("answer") or "").strip()
            # crude heuristic: 0..10 based on length & presence of set symbols
            base = min(10, max(0, len(ans)//120))
            bonus = 1 if any(sym in ans for sym in ["∩","∪","\\","Δ","U"]) else 0
            score = min(10, base + bonus)
            total += score
            perq.append({"id": item.get("id","?"), "score": score, "feedback": "Heuristic scoring (offline)."})
        overall = round(total / (len(qa) * 10) * 100) if qa else 0
        return jsonify({
            "per_question": perq,
            "overall_pct": overall,
            "pass": overall >= 70,
            "summary": "Offline grading fallback — install/openai and set OPENAI_API_KEY for rubric-based grading."
        })

    # GPT-based grading
    system_prompt = (
        "You are a strict but fair grader for open-ended set-theory tasks in geology context. "
        "Grade 10 answers (Q1..Q10) that reference an interactive Venn diagram with sets I,S,M and operations ∩, ∪, \\ , Δ, outside U. "
        "Use the rubric: clarity (3), correctness of set reasoning (4), geology context linkage (3) = total 10 points per question. "
        "Be concise in feedback (1–2 sentences). Return strict JSON only."
    )

    # Build a compact user prompt
    payload = {
        "language": language,
        "student": {"name": name, "neptun": neptun},
        "qa": [{"id": item.get("id","?"),
                "question": (item.get("question") or "")[:600],
                "answer": (item.get("answer") or "")[:4000]} for item in qa]
    }
    user_prompt = json.dumps({
        "grade_request": payload,
        "return_format": {
            "per_question": [{"id": "Q1", "score": 0, "feedback": "short sentence"}],
            "overall_pct": 0,
            "pass": True,
            "summary": "1–2 sentences"
        }
    }, ensure_ascii=False)

    try:
        content = _chat_request(MODEL_GRADING, system_prompt, user_prompt, response_format="json")
        obj = _safe_json(content)
        perq = obj.get("per_question", [])
        overall = int(obj.get("overall_pct", 0))
        passed = bool(obj.get("pass", overall >= 70))
        summary = obj.get("summary", "")
        # Safety clamps
        clean = []
        total = 0
        for item in perq:
            sid = item.get("id","?")
            sc = int(item.get("score", 0))
            sc = max(0, min(10, sc))
            fb = (item.get("feedback") or "").strip()
            total += sc
            clean.append({"id": sid, "score": sc, "feedback": fb})
        if not perq and qa:
            # compute from total if needed
            overall = round(total / (len(qa) * 10) * 100)
            passed = overall >= 70
        return jsonify({
            "per_question": clean,
            "overall_pct": overall,
            "pass": passed,
            "summary": summary
        })
    except Exception as e:
        # Fall back to heuristic if GPT fails
        perq = []
        total = 0
        for item in qa:
            ans = (item.get("answer") or "").strip()
            base = min(10, max(0, len(ans)//120))
            bonus = 1 if any(sym in ans for sym in ["∩","∪","\\","Δ","U"]) else 0
            score = min(10, base + bonus)
            total += score
            perq.append({"id": item.get("id","?"), "score": score, "feedback": "Heuristic scoring (API error fallback)."})
        overall = round(total / (len(qa) * 10) * 100) if qa else 0
        return jsonify({
            "per_question": perq,
            "overall_pct": overall,
            "pass": overall >= 70,
            "summary": "API error fallback — heuristic scoring used."
        })
