from __future__ import annotations
import os, json, time, hashlib, random, re
from typing import List, Dict, Any
from flask import Blueprint, render_template, request, jsonify

assignment_bp = Blueprint("assignment", __name__)

# =========================
# Config (lenient grading)
# =========================
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
MODEL_GRADING  = os.environ.get("ASSIGNMENT_GRADING_MODEL", "gpt-4o-mini")
PASS_THRESHOLD = 70  # keep requirement: ≥ 70% to unlock PDF

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

def _chat_request(model: str, system_prompt: str, user_payload: dict) -> str:
    """Return assistant content (JSON string)."""
    if not OPENAI_API_KEY:
        raise RuntimeError("Missing OPENAI_API_KEY")
    if USE_OFFICIAL:
        client = _client()
        resp = client.chat.completions.create(
            model=model,
            temperature=0.3,  # low temp for consistent, lenient rubric
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
        )
        return resp.choices[0].message.content
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ]
    }
    r = requests.post(url, headers=headers, json=payload, timeout=60)
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

# =========================
# Example-aligned content
# =========================
SET_LABELS = {"I": "Igneous", "S": "Sedimentary", "M": "Metamorphic"}
PAIRS = [("I","S"), ("I","M"), ("S","M")]

REG_MINERALS = {
    "I": ["Olivine","Pyroxene","Plagioclase Feldspar","Amphibole","Biotite","Ilmenite"],
    "S": ["Gypsum","Halite","Kaolinite","Opal","Galena","Hematite"],
    "M": ["Garnet","Kyanite","Staurolite","Sillimanite","Chlorite","Graphite"],
    "I∩S": ["Zeolite"],
    "I∩M": ["Serpentine","Hornblende","Muscovite"],
    "S∩M": ["Calcite","Dolomite","Talc"],
    "I∩S∩M": ["Quartz"],
}

MINERAL_KEYWORDS = set(sum(REG_MINERALS.values(), []))  # flatten

# Simple, short, concept-check templates (10 will be sampled)
TEMPLATES = [
    lambda rng, A, B: {"text": f"In your own words, what does set {A} ({SET_LABELS[A]}) represent? Give one mineral typically in {A} and say why."},
    lambda rng, A, B: {"text": f"Explain the intersection {A} ∩ {B}. Name one mineral that could lie in {A} ∩ {B} and justify briefly."},
    lambda rng, A, B: {"text": f"Explain the difference {A} \\ {B}. Give one mineral you expect in {A} but not in {B} and why."},
    lambda rng, A, B: {"text": f"What does the symmetric difference {A} Δ {B} capture? Give one mineral included and one excluded; explain."},
    lambda rng, A, B: {"text": f"What does the union {A} ∪ {B} represent? Give one mineral only in {A} and one only in {B}."},
    lambda rng, A, B: {"text": "What does the triple intersection I ∩ S ∩ M represent? Use Quartz as your example (2–4 sentences)."},
    lambda rng, A, B: {"text": "What is the 'Outside all sets' region U \\ (I ∪ S ∪ M)? Propose one plausible item and explain briefly."},
    lambda rng, A, B: {"text": "Calcite is in S ∩ M in our example. Explain in 2–3 sentences why that makes sense."},
    lambda rng, A, B: {"text": f"If a mineral belongs to {B} but not {A}, write one sentence in set notation and give a fitting mineral."},
    lambda rng, A, B: {"text": f"Compare {A} ∩ {B} vs {A} Δ {B} in your own words. When would you use each?"},
    lambda rng, A, B: {"text": "Does Zeolite belong to I ∩ S in the example? Answer in 1–2 sentences and justify."},
    lambda rng, A, B: {"text": "Pick any mineral and state which of {I,S,M} it belongs to (possibly multiple). Justify briefly."},
]

def _seed_from_identity(name: str, neptun: str) -> int:
    today = time.strftime("%Y-%m-%d")
    key = f"{name}|{neptun}|{today}"
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return int(h, 16) % (2**31 - 1)

def _gen_questions(name: str, neptun: str) -> Dict[str, Any]:
    rng = random.Random(_seed_from_identity(name, neptun))
    chosen_idx = rng.sample(range(len(TEMPLATES)), 10)
    def pick_pair():
        return rng.choice(PAIRS)
    qlist = []
    for i, ti in enumerate(chosen_idx, start=1):
        A, B = pick_pair()
        q = TEMPLATES[ti](rng, A, B)
        qlist.append({"id": f"Q{i:02d}", "text": q["text"]})
    return {"seed": str(_seed_from_identity(name, neptun)), "questions": qlist}

# =========================
# Lenient heuristic (offline)
# =========================
SYM_RE = re.compile(r"[∩∪Δ\\U]")
SET_RE = re.compile(r"\b(I|S|M|Igneous|Sedimentary|Metamorphic)\b", re.IGNORECASE)

def _soft_score_and_feedback(ans: str) -> tuple[int, str]:
    """
    Lenient scoring:
      • Baseline 6/10 for any relevant multi-sentence answer (≥ ~60 chars).
      • + up to 2 for length/clarity.
      • +1 if uses set symbols (∩ ∪ \ Δ U).
      • +1 if mentions a valid set (I/S/M or names) or a mineral from the example.
      • Cap at 10. Floor at 4 for very short text.
    """
    txt = (ans or "").strip()
    if not txt:
        return 0, "Please add a short explanation in any language."

    nchar = len(txt)
    nsent = max(1, txt.count(".") + txt.count("!") + txt.count("?"))
    has_sym = bool(SYM_RE.search(txt))
    has_set = bool(SET_RE.search(txt))
    has_mineral = any(m.lower() in txt.lower() for m in MINERAL_KEYWORDS)

    base = 6 if nchar >= 60 else 4
    length_pts = 2 if nchar >= 220 else (1 if nchar >= 120 else 0)
    sym_pts = 1 if has_sym else 0
    set_or_mineral_pts = 1 if (has_set or has_mineral) else 0

    score = min(10, base + length_pts + sym_pts + set_or_mineral_pts)

    # Friendly, actionable feedback
    if score >= 9:
        fb = "Clear and relevant; nice linkage to the set relations."
    elif score >= 7:
        fb = "Good job. You could add one more detail or example for full credit."
    elif score >= 4:
        fb = "Thanks — add a bit more detail and try to use symbols (∩, ∪, Δ, \\) or mineral names."
    else:
        fb = "Please expand your answer (2–4 sentences) and mention the relevant sets/minerals."
    return score, fb

# =========================
# Routes
# =========================
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
    Input:  { "name":"..", "neptun":"..", "qa":[{"id":"Q01","question":"...","answer":"..."}] }
    Output: { "per_question":[..], "overall_pct":int, "pass":bool, "summary":"..." }
    """
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    neptun = (data.get("neptun") or "").strip().upper()
    qa = data.get("qa") or []

    # If no GPT key, use lenient heuristic
    if not OPENAI_API_KEY or not qa:
        perq, total = [], 0
        for item in qa:
            score, fb = _soft_score_and_feedback(item.get("answer",""))
            total += score
            perq.append({"id": item.get("id","?"), "score": score, "feedback": fb})
        overall = round(total / (len(qa) * 10) * 100) if qa else 0
        return jsonify({
            "per_question": perq,
            "overall_pct": overall,
            "pass": overall >= PASS_THRESHOLD,
            "summary": "Lenient offline grading. Aim for 2–4 sentences with symbols and mineral names."
        })

    # GPT grading (lenient rubric + safety floor)
    system_prompt = (
        "You are a supportive grader for short, open-ended answers about set relations in a geology Venn diagram. "
        "Sets: I (Igneous), S (Sedimentary), M (Metamorphic). Relations: ∩, ∪, \\ , Δ, outside U, triple intersection. "
        "Accept ANY language. Be LENIENT:\n"
        "• If the answer is on-topic and multi-sentence (≈2+), award at least 6/10.\n"
        "• Award extra points for correct set reasoning, use of symbols (∩ ∪ Δ \\ U), and geology linkage.\n"
        "Rubric (lenient): baseline relevance/effort (0–6), set reasoning (0–2), geology linkage (0–2) = total 10.\n"
        "Return strict JSON: {per_question:[{id,score,feedback}], overall_pct, pass, summary}. Keep feedback friendly (≤1 sentence)."
    )
    user_payload = {
        "student": {"name": name, "neptun": neptun},
        "qa": [{"id": it.get("id","?"),
                "question": (it.get("question") or "")[:400],
                "answer": (it.get("answer") or "")[:4000]} for it in qa]
    }

    try:
        content = _chat_request(MODEL_GRADING, system_prompt, user_payload)
        obj = _safe_json(content)
        perq = obj.get("per_question", [])
        clean, total = [], 0

        # Apply lenient safety floor post-processing
        for item, src in zip(perq, qa):
            sid = item.get("id","?")
            sc = int(item.get("score", 0))
            ans = (src.get("answer") or "")
            has_relevance = len(ans.strip()) >= 60 and (SYM_RE.search(ans) or SET_RE.search(ans) or any(m.lower() in ans.lower() for m in MINERAL_KEYWORDS))
            if has_relevance and sc < 6:
                sc = 6  # floor for relevant multi-sentence attempts
            sc = max(0, min(10, sc))
            total += sc
            fb = (item.get("feedback") or "Good effort. Add one more detail for full credit.").strip()
            clean.append({"id": sid, "score": sc, "feedback": fb})

        overall = obj.get("overall_pct")
        if overall is None:
            overall = round(total / (len(clean) * 10) * 100) if clean else 0
        passed = bool(obj.get("pass", overall >= PASS_THRESHOLD))
        summary = obj.get("summary", "Supportive grading applied.")

        return jsonify({
            "per_question": clean,
            "overall_pct": int(overall),
            "pass": passed,
            "summary": summary
        })
    except Exception:
        # Fallback to heuristic
        perq, total = [], 0
        for item in qa:
            score, fb = _soft_score_and_feedback(item.get("answer",""))
            total += score
            perq.append({"id": item.get("id","?"), "score": score, "feedback": fb})
        overall = round(total / (len(qa) * 10) * 100) if qa else 0
        return jsonify({
            "per_question": perq,
            "overall_pct": overall,
            "pass": overall >= PASS_THRESHOLD,
            "summary": "GPT error — lenient offline grading used."
        })
