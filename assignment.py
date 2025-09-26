from __future__ import annotations
import os, json, time, hashlib, random
from typing import List, Dict, Any
from flask import Blueprint, render_template, request, jsonify

assignment_bp = Blueprint("assignment", __name__)

# ============== CONFIG ==============
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
MODEL_GRADING   = os.environ.get("ASSIGNMENT_GRADING_MODEL", "gpt-4o-mini")

USE_OFFICIAL = True
try:
    from openai import OpenAI   # pip install openai
except Exception:
    USE_OFFICIAL = False
import requests

def _client():
    if not OPENAI_API_KEY:
        return None
    if USE_OFFICIAL:
        return OpenAI(api_key=OPENAI_API_KEY)
    return None

def _chat_request(model: str, system_prompt: str, user_prompt: str) -> str:
    """Returns assistant content (JSON string)."""
    if not OPENAI_API_KEY:
        raise RuntimeError("Missing OPENAI_API_KEY")

    if USE_OFFICIAL:
        client = _client()
        resp = client.chat.completions.create(
            model=model,
            temperature=0.4,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        return resp.choices[0].message.content

    # Fallback HTTP
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    }
    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"]

def _safe_json(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        t = (text or "").strip()
        if t.startswith("```"):
            t = t.strip("`")
            parts = t.split("\n", 1)
            if len(parts) == 2:
                t = parts[1]
        return json.loads(t)

# ============== DATA (example-aligned) ==============
SET_LABELS = {
    "I": "Igneous",
    "S": "Sedimentary",
    "M": "Metamorphic",
}
PAIRS = [("I","S"), ("I","M"), ("S","M")]

# Minerals by canonical region (from your example)
REG_MINERALS = {
    "I": ["Olivine","Pyroxene","Plagioclase Feldspar","Amphibole","Biotite","Ilmenite"],
    "S": ["Gypsum","Halite","Kaolinite","Opal","Galena","Hematite"],
    "M": ["Garnet","Kyanite","Staurolite","Sillimanite","Chlorite","Graphite"],
    "I∩S": ["Zeolite"],
    "I∩M": ["Serpentine","Hornblende","Muscovite"],
    "S∩M": ["Calcite","Dolomite","Talc"],
    "I∩S∩M": ["Quartz"],
    "outside": [],  # left empty on purpose (students can propose ideas)
}

# Question templates: short, simple, concept-check focused.
TEMPLATES = [
    # 1: Define a set + give example
    lambda rng, A, B: {
        "text": f"In your own words, what does set {A} ({SET_LABELS[A]}) represent in the game? "
                f"Give one example mineral that typically belongs to {A}."
    },
    # 2: Intersection
    lambda rng, A, B: {
        "text": f"Explain the intersection {A} ∩ {B}. Name one mineral that could lie in {A} ∩ {B} and say why."
    },
    # 3: Difference
    lambda rng, A, B: {
        "text": f"Explain the difference {A} \\ {B} in geology terms. Give one example mineral you expect in {A} but not in {B}."
    },
    # 4: Symmetric difference
    lambda rng, A, B: {
        "text": f"What does the symmetric difference {A} Δ {B} capture? "
                f"Give one mineral that would be included in {A} Δ {B} and one that would be excluded; justify briefly."
    },
    # 5: Union
    lambda rng, A, B: {
        "text": f"What does the union {A} ∪ {B} represent? Give one mineral only in {A} and one only in {B}."
    },
    # 6: Triple intersection
    lambda rng, A, B: {
        "text": f"What does the triple intersection I ∩ S ∩ M represent? Use Quartz as your example."
    },
    # 7: Outside / complement
    lambda rng, A, B: {
        "text": "What is the 'Outside all sets' region U \\ (I ∪ S ∪ M)? "
                "Provide one plausible mineral/material that might fall outside and explain."
    },
    # 8: Named example from S∩M
    lambda rng, A, B: {
        "text": "Calcite is placed in S ∩ M in our example. Explain in 2–3 sentences why this makes sense geologically."
    },
    # 9: Write a sentence with notation
    lambda rng, A, B: {
        "text": f"If a mineral belongs to {B} but not {A}, write a one‑sentence statement using set notation and "
                f"give one example from the game you think fits."
    },
    # 10: Compare ∩ and Δ
    lambda rng, A, B: {
        "text": f"Compare {A} ∩ {B} vs {A} Δ {B} in your own words. When would you use each to reason about minerals?"
    },
    # 11: Named example from I∩S
    lambda rng, A, B: {
        "text": "Does Zeolite belong to I ∩ S in the example? Answer in 1–2 sentences and justify."
    },
    # 12: Free pick mapping
    lambda rng, A, B: {
        "text": "Pick any mineral from the game and state which of {I,S,M} it belongs to (possibly multiple). "
                "Justify briefly in geology terms."
    },
]

def _seed_from_identity(name: str, neptun: str) -> int:
    today = time.strftime("%Y-%m-%d")
    key = f"{name}|{neptun}|{today}"
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return int(h, 16) % (2**31 - 1)

def _gen_questions(name: str, neptun: str) -> Dict[str, Any]:
    rng = random.Random(_seed_from_identity(name, neptun))
    # Select 10 different templates
    chosen_idx = rng.sample(range(len(TEMPLATES)), 10)
    # For each, choose a pair (A,B) for those that need it
    def pick_pair():
        return rng.choice(PAIRS)
    qlist = []
    for i, ti in enumerate(chosen_idx, start=1):
        A, B = pick_pair()
        q = TEMPLATES[ti](rng, A, B)
        qlist.append({"id": f"Q{i:02d}", "text": q["text"]})
    return {"seed": str(_seed_from_identity(name, neptun)), "questions": qlist}

# ============== ROUTES ==============
@assignment_bp.route("/assignment")
def assignment_home():
    return render_template("assignment.html")

@assignment_bp.route("/assignment/api/generate", methods=["POST"])
def assignment_generate():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    neptun = (data.get("neptun") or "").strip().upper()
    if not name or not neptun:
        return jsonify({"error": "Missing name or Neptun code"}), 400
    return jsonify(_gen_questions(name, neptun))

@assignment_bp.route("/assignment/api/grade", methods=["POST"])
def assignment_grade():
    """
    Input JSON:
    { "name":"...", "neptun":"...", "qa":[{"id":"Q01","question":"...","answer":"..."}] }
    Output JSON:
    {
      "per_question":[{"id":"Q01","score":0-10,"feedback":"..."}],
      "overall_pct":0-100,"pass":true/false,"summary":"..."
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    neptun = (data.get("neptun") or "").strip().upper()
    qa = data.get("qa") or []

    # If no key: heuristic fallback (length + symbols)
    if not OPENAI_API_KEY or not qa:
        perq, total = [], 0
        for item in qa:
            ans = (item.get("answer") or "").strip()
            # Base on length (roughly 2–6 sentences)
            base = min(10, max(0, len(ans)//160))
            # Bonus if uses set symbols or names
            bonus = 0
            if any(sym in ans for sym in ["∩","∪","\\","Δ","U"]): bonus += 1
            if any(s in ans for s in ["Igneous","Sedimentary","Metamorphic","I ","S ","M "]): bonus += 1
            score = max(0, min(10, base + bonus))
            total += score
            perq.append({"id": item.get("id","?"), "score": score, "feedback": "Heuristic grading used (offline)."})
        overall = round(total / (len(qa) * 10) * 100) if qa else 0
        return jsonify({
            "per_question": perq,
            "overall_pct": overall,
            "pass": overall >= 70,
            "summary": "Offline heuristic result. For rubric-based feedback, set OPENAI_API_KEY."
        })

    # GPT grading
    system_prompt = (
        "You are a concise grader for short, open-ended answers about basic set relations in a geology-themed Venn diagram. "
        "Sets: I (Igneous), S (Sedimentary), M (Metamorphic). Relations: ∩, ∪, \\ , Δ, outside U, triple intersection. "
        "Accept ANY language. Grade each answer 0–10 using this rubric:\n"
        "  - Clarity & relevance (0–3)\n"
        "  - Correct set-theory reasoning (0–4)\n"
        "  - Geology linkage (0–3)\n"
        "Be brief in feedback (1 sentence). Return strict JSON with keys "
        "{per_question:[{id,score,feedback}], overall_pct, pass, summary}."
    )
    user_payload = {
        "student": {"name": name, "neptun": neptun},
        "qa": [{"id": it.get("id","?"),
                "question": (it.get("question") or "")[:400],
                "answer": (it.get("answer") or "")[:4000]} for it in qa]
    }
    try:
        content = _chat_request(MODEL_GRADING, system_prompt, json.dumps(user_payload, ensure_ascii=False))
        obj = _safe_json(content)
        perq = obj.get("per_question", [])
        # Sanitize and compute overall if needed
        total, clean = 0, []
        for item in perq:
            sid = item.get("id","?")
            sc = int(item.get("score", 0))
            sc = max(0, min(10, sc))
            fb = (item.get("feedback") or "").strip()
            total += sc
            clean.append({"id": sid, "score": sc, "feedback": fb})
        overall = obj.get("overall_pct")
        if overall is None:
            overall = round(total / (len(clean) * 10) * 100) if clean else 0
        passed = bool(obj.get("pass", overall >= 70))
        summary = obj.get("summary", "—")
        return jsonify({
            "per_question": clean,
            "overall_pct": int(overall),
            "pass": passed,
            "summary": summary
        })
    except Exception:
        # Fallback if API fails
        perq, total = [], 0
        for item in qa:
            ans = (item.get("answer") or "").strip()
            base = min(10, max(0, len(ans)//160))
            bonus = 1 if any(sym in ans for sym in ["∩","∪","\\","Δ","U"]) else 0
            score = max(0, min(10, base + bonus))
            total += score
            perq.append({"id": item.get("id","?"), "score": score, "feedback": "Heuristic grading (API error)."})
        overall = round(total / (len(qa) * 10) * 100) if qa else 0
        return jsonify({
            "per_question": perq,
            "overall_pct": overall,
            "pass": overall >= 70,
            "summary": "Heuristic used due to API error."
        })
