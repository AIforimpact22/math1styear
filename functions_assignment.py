# functions_assignment.py
from __future__ import annotations

import copy
import json
import os
from typing import Any, Dict, List, Tuple

from flask import Blueprint, jsonify, render_template, request

# OpenAI SDK — uses OPENAI_API_KEY env var
# Official usage pattern: OpenAI() picks up OPENAI_API_KEY automatically.  :contentReference[oaicite:2]{index=2}
try:
    from openai import OpenAI
    _OPENAI_AVAILABLE = True
except Exception:
    _OPENAI_AVAILABLE = False

functions_assignment_bp = Blueprint(
    "functions_assignment", __name__, url_prefix="/assignment-3"
)

# -----------------------
# Config
# -----------------------
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")  # model name per OpenAI docs. :contentReference[oaicite:3]{index=3}

def _get_openai_client() -> OpenAI | None:
    if not _OPENAI_AVAILABLE:
        return None
    try:
        return OpenAI()  # uses OPENAI_API_KEY automatically. :contentReference[oaicite:4]{index=4}
    except Exception:
        return None

# -----------------------
# Helpers — parsing & safe equality
# -----------------------
def _float_eq(a: float, b: float, eps: float = 1e-6) -> bool:
    return abs(a - b) <= eps

def _as_float_list(text: str) -> List[float]:
    vals: List[float] = []
    for chunk in (text or "").replace(";", ",").split(","):
        s = chunk.strip()
        if not s:
            continue
        try:
            vals.append(float(s))
        except ValueError:
            # ignore unparsable tokens
            pass
    return vals

# -----------------------
# LLM grading
# -----------------------
_BASE_SYSTEM = (
    "You are a precise, fair geology TA. Grade student answers concisely.\n"
    "Return STRICT JSON with keys: score (integer 0..MAX), feedback (<=2 short sentences).\n"
    "Do NOT reveal solutions, numbers, or pairs. Provide hints only."
)

def _grade_text_llm(rubric: str, student_text: str, max_points: int = 10) -> Tuple[int, str]:
    """
    Uses OpenAI Chat Completions with JSON structured output.
    Falls back safely if API is unavailable or errors out.
    """
    client = _get_openai_client()
    if not client:
        # LLM unavailable: give neutral feedback with zero points (safe fallback)
        return 0, "Automated evaluation unavailable. Provide clearer, evidence‑based justification."

    # We request JSON output explicitly. The official SDK supports chat completions with response_format. :contentReference[oaicite:5]{index=5}
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _BASE_SYSTEM},
                {"role": "user", "content": (
                    f"MAX={max_points}\n"
                    f"Rubric (grade on content accuracy, clarity, use of context; 0..MAX):\n{rubric}\n\n"
                    f"Student answer:\n{student_text.strip()}"
                )},
            ],
        )
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        score = int(data.get("score", 0))
        score = max(0, min(max_points, score))
        feedback = str(data.get("feedback", "")).strip() or "Evaluated."
        # Safety: no spoilers
        feedback = feedback.replace("Expected", "Hint").replace("expected", "hint")
        return score, feedback
    except Exception:
        return 0, "Evaluation error. Your explanation should reference the context and definitions."

# -----------------------
# Objective graders (no spoilers)
# -----------------------
def _grade_mcq(item: Dict[str, Any], ans: Dict[str, Any]) -> Tuple[int, str]:
    picked = (ans or {}).get("choice", "")
    ok = str(picked) == str(item.get("expected"))
    return (10 if ok else 0), ("Correct." if ok else "Not correct — revisit the definition (no spoilers).")

def _grade_yesno(item: Dict[str, Any], ans: Dict[str, Any]) -> Tuple[int, str]:
    yn = (ans or {}).get("yes", "")
    correct = bool(item.get("expected_yes", False))
    ok = yn.lower() in ("yes", "y", "true", "t", "igen", "i") if correct else yn.lower() in ("no", "n", "false", "f", "nem")
    return (10 if ok else 0), ("Correct." if ok else "Not correct — check the rule (no spoilers).")

def _grade_yesno_plus_text_llm(item: Dict[str, Any], ans: Dict[str, Any]) -> Tuple[int, str]:
    """
    Weighted: yes/no correctness up to 6 pts; LLM justification up to 4 pts.
    """
    # yes/no (6 pts max)
    yn_score_full, yn_fb = _grade_yesno(item, ans)
    yn_points = 6 if yn_score_full == 10 else 0

    # explanation (4 pts max) via LLM
    rubric = item.get("llm_rubric", "Explain briefly and correctly using the provided context; avoid vague claims.")
    text = (ans or {}).get("text", "")
    text_points, text_fb = _grade_text_llm(rubric, text, max_points=4)

    total = min(10, yn_points + text_points)
    # Combine hint-only feedback
    if yn_points == 6 and text_points >= 3:
        fb = "Correct and well-justified."
    else:
        bits = []
        if yn_points < 6: bits.append("Y/N is off — re-check the definition.")
        if text_points < 3: bits.append("Justification needs clearer reference to the context.")
        fb = " ".join(bits) or "Good."
    return total, fb

def _grade_short_number(item: Dict[str, Any], ans: Dict[str, Any]) -> Tuple[int, str]:
    try:
        got = float((ans or {}).get("value", ""))
    except Exception:
        return 0, "Enter a number (e.g., 0.24)."
    ok = _float_eq(got, float(item.get("expected")))
    return (10 if ok else 0), ("Correct." if ok else "Not correct — re-check the mapping table (no spoilers).")

def _grade_csv_float_set(item: Dict[str, Any], ans: Dict[str, Any]) -> Tuple[int, str]:
    expected: List[float] = item.get("expected", [])
    got_list = _as_float_list((ans or {}).get("values", ""))
    used = [False] * len(expected)
    correct = 0
    for g in got_list:
        for i, e in enumerate(expected):
            if not used[i] and _float_eq(g, float(e)):
                used[i] = True
                correct += 1
                break
    n = max(1, len(expected))
    extras = max(0, len(got_list) - correct)
    score = max(0, min(10, round(10 * (correct - 0.5 * extras) / n)))
    # Hint-only feedback, no values
    if score == 10:
        fb = "All set values look good."
    else:
        fb = "Set looks off — some values are missing or extra. Compare with the context (no spoilers)."
    return score, fb

def _grade_pairgrid(item: Dict[str, Any], ans: Dict[str, Any]) -> Tuple[int, str]:
    """
    Student sends: {"pairs": [[a,b], [a,b], ...]}
    Compare to item["expected_pairs"] (order-insensitive).
    """
    expected_pairs: List[List[float]] = item.get("expected_pairs", [])
    got_pairs: List[List[float]] = (ans or {}).get("pairs", [])
    # normalize
    def _norm_pair(p):
        return (str(p[0]), str(p[1]))
    expected_set = {_norm_pair(p) for p in expected_pairs}
    got_set = {_norm_pair(p) for p in got_pairs if isinstance(p, (list, tuple)) and len(p) == 2}

    correct = len(expected_set & got_set)
    extra = len(got_set - expected_set)

    n = max(1, len(expected_set))
    score = max(0, min(10, round(10 * (correct - 0.5 * extra) / n)))

    if score == 10:
        fb = "Your selection of pairs is consistent."
    else:
        fb = "Some pairs are missing or extra — re-check the relation rule (no spoilers)."
    return score, fb

def _grade_integer(item: Dict[str, Any], ans: Dict[str, Any]) -> Tuple[int, str]:
    try:
        got = int((ans or {}).get("value", ""))
    except Exception:
        return 0, "Enter an integer."
    ok = (got == int(item.get("expected", 0)))
    return (10 if ok else 0), ("Correct." if ok else "Not correct — hint: |A×B| = |A| · |B|.")

# -----------------------
# Manifest (content) — with background context
# -----------------------
def _manifest_functions() -> Dict[str, Any]:
    """
    Assignment: Functions & Relations (Geology) — Revamped
    - Includes detailed background context.
    - 10 items, with 5 qualitative (LLM-graded).
    """
    return {
        "assignment": "Assignment — Functions & Relations (Geology)",
        "context": (
            "Background • You are a junior petrophysicist analyzing a clean sandstone interval "
            "in Well A from 1195–1208 m. Porosity φ (fraction, e.g., 0.24) is measured from logs "
            "(density/neutron combo). Measurement noise is about ±0.02 due to tool calibration and "
            "borehole conditions. Duplicate readings may occur at the same depth from repeat passes. "
            "We study relations on two sets:\n"
            "A = {depths in meters},  B = {porosity values}.  A×B is all possible (depth, φ) pairs. "
            "A relation is the subset of pairs that are TRUE in the data; a function requires each "
            "depth in A to map to exactly one φ in B."
        ),
        "hint": "Units: depth in meters; porosity is a fraction. R_close uses |φ1−φ2| ≤ 0.02; R_shallow uses x<y.",
        "items": [
            # Q1) Qualitative — definition in own words
            {
                "id": "FQ1",
                "kind": "long_text",
                "title": "1) In your own words, what is a relation A→B in this geological setting? (2–3 sentences)",
                "llm_rubric": (
                    "Award 8–10 if the answer: (a) states a relation is a set of TRUE (depth, φ) pairs picked from A×B, "
                    "(b) ties to log-derived porosity with context, (c) avoids calling it one‑to‑one. "
                    "Award 4–7 if partially correct but vague. 0–3 if incorrect or off-topic."
                ),
            },
            # Q2) MCQ — definition of function
            {
                "id": "FQ2",
                "kind": "mcq",
                "title": "2) When is “depth → porosity” a function?",
                "options": [
                    {"id": "A", "label": "Every depth has exactly one porosity value."},
                    {"id": "B", "label": "A depth may have two porosity values."},
                    {"id": "C", "label": "Only when porosity is > 0.20."},
                    {"id": "D", "label": "Only if all wells use the same tool."},
                ],
                "expected": "A",
            },
            # Q3) Pairgrid — measured relation (true pairs M)
            {
                "id": "FQ3",
                "kind": "pairgrid",
                "title": "3) Mark the true measurement pairs M (depth, porosity).",
                "A": [1198, 1200, 1203],
                "B": [0.19, 0.21, 0.24],
                "note": "Tick the pairs that appear in your log.",
                "expected_pairs": [[1198, 0.19], [1200, 0.24], [1203, 0.21]],
            },
            # Q4) Qualitative — interpret a value
            {
                "id": "FQ4",
                "kind": "long_text",
                "title": "4) Interpret F(1200)=0.24 in plain language. What does this mean physically?",
                "llm_rubric": (
                    "Look for clarity that 1200 m depth is associated with porosity 0.24 (24%), "
                    "ties to sandstone interval, measurement context, and no overclaiming. "
                    "10 = crisp, correct, contextualized; 5–8 = mostly correct; 0–4 = confused."
                ),
            },
            # Q5) Pairgrid — depth→depth 'shallower than'
            {
                "id": "FQ5",
                "kind": "pairgrid",
                "title": "5) Depth relation R_shallow: tick pairs (x,y) with x is shallower than y.",
                "A": [1198, 1200, 1203],
                "B": [1200, 1203, 1205],
                "expected_pairs": [[1198, 1200], [1198, 1203], [1198, 1205], [1200, 1203], [1200, 1205], [1203, 1205]],
            },
            # Q6) Qualitative — properties of R_close
            {
                "id": "FQ6",
                "kind": "long_text",
                "title": "6) R_close on porosity: |φ1 − φ2| ≤ 0.02. Is it reflexive, symmetric, transitive? Explain briefly.",
                "llm_rubric": (
                    "Expected reasoning: reflexive (|φ−φ|=0≤0.02), symmetric (|a−b|=|b−a|), "
                    "not necessarily transitive (counterexample reasoning). "
                    "Score on correctness + clarity, no spoilers of numeric examples."
                ),
            },
            # Q7) Yes/No + brief reason — duplicate depth
            {
                "id": "FQ7",
                "kind": "yesno_plus_text",
                "title": "7) M = {(1600,0.18), (1602,0.22), (1602,0.26), (1605,0.21)} — Is “depth→porosity” a function? Briefly justify.",
                "expected_yes": False,
                "llm_rubric": (
                    "Justification should mention the same input (depth 1602) mapping to two outputs, violating function definition. "
                    "Award 3–4 for clear, concise reason; else 0–2."
                ),
            },
            # Q8) CSV float set — range
            {
                "id": "FQ8",
                "kind": "csv_float_set",
                "title": "8) List the RANGE (values actually seen) for F in Q3/Q4 (comma separated).",
                "hint": "Example format: 0.19, 0.22, 0.24",
                "expected": [0.19, 0.21, 0.24],
            },
            # Q9) Integer — size of A×B
            {
                "id": "FQ9",
                "kind": "integer",
                "title": "9) If |A|=3 depths and |B|=4 porosity values, how many pairs are in A×B?",
                "expected": 12,
            },
            # Q10) Qualitative — cleaning pipeline
            {
                "id": "FQ10",
                "kind": "long_text",
                "title": "10) After de-duplication, propose a simple pipeline to ensure depth→porosity is a function (and note a tradeoff).",
                "llm_rubric": (
                    "Look for: (a) strategy to resolve duplicates (median, quality flag, or choose best tool run), "
                    "(b) ensuring one φ per depth, (c) mention tradeoff (variance loss, bias, uncertainty). "
                    "Score 0–10 by completeness and clarity."
                ),
            },
        ],
    }

# -----------------------
# Public manifest (sanitized) — remove answers & rubrics
# -----------------------
def _public_manifest(full: Dict[str, Any]) -> Dict[str, Any]:
    m = copy.deepcopy(full)
    SENSITIVE = {"expected", "expected_pairs", "expected_yes", "llm_rubric"}
    for item in m.get("items", []):
        for key in list(item.keys()):
            if key in SENSITIVE:
                item.pop(key, None)
    return m

# -----------------------
# Routes
# -----------------------
@functions_assignment_bp.route("/")
def functions_assignment_home():
    return render_template("assignment_functions.html")

@functions_assignment_bp.route("/api/generate", methods=["POST"])
def functions_assignment_generate():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    neptun = (data.get("neptun") or "").strip().upper()
    manifest = _manifest_functions()
    public = _public_manifest(manifest)
    public["student"] = {"name": name, "neptun": neptun}
    return jsonify(public)

@functions_assignment_bp.route("/api/grade", methods=["POST"])
def functions_assignment_grade():
    data = request.get_json(force=True, silent=True) or {}
    answers: List[Dict[str, Any]] = data.get("answers", [])
    manifest = _manifest_functions()  # internal copy WITH expected values/rubrics
    item_by_id = {it["id"]: it for it in manifest["items"]}

    per_item: List[Dict[str, Any]] = []
    total = 0
    count = 0

    for a in answers:
        qid = a.get("id")
        item = item_by_id.get(qid)
        if not item:
            continue
        kind = item.get("kind")
        try:
            if kind == "mcq":
                score, fb = _grade_mcq(item, a)
            elif kind == "yesno":
                score, fb = _grade_yesno(item, a)
            elif kind == "yesno_plus_text":
                score, fb = _grade_yesno_plus_text_llm(item, a)
            elif kind == "short_number":
                score, fb = _grade_short_number(item, a)
            elif kind == "csv_float_set":
                score, fb = _grade_csv_float_set(item, a)
            elif kind == "pairgrid":
                score, fb = _grade_pairgrid(item, a)
            elif kind == "integer":
                score, fb = _grade_integer(item, a)
            elif kind == "long_text":
                rubric = item.get("llm_rubric", "Grade for accuracy, clarity, and use of context.")
                text = (a or {}).get("text", "")
                score, fb = _grade_text_llm(rubric, text, max_points=10)
            else:
                score, fb = 0, "Unknown item type."
        except Exception as e:
            score, fb = 0, f"Grading error: {e}"

        per_item.append({"id": qid, "score": int(score), "feedback": fb})
        total += int(score)
        count += 1

    overall_pct = round(total / (max(1, count) * 10) * 100)
    summary = (
        "Excellent — strong grasp of relations/functions and context."
        if overall_pct >= 90 else
        "Good — tighten pair selections and strengthen explanations with context."
        if overall_pct >= 75 else
        "Progressing — review function definition (one input → one output) and relation rules."
        if overall_pct >= 60 else
        "Revisit the basics: relation vs function, A×B, and the scenario context."
    )

    return jsonify({
        "per_item": per_item,
        "overall_pct": overall_pct,
        "pass": overall_pct >= 70,
        "summary": summary,
    })
