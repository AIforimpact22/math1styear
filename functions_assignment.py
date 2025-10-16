# functions_assignment.py
from __future__ import annotations

from typing import Any, Dict, List, Tuple
from flask import Blueprint, jsonify, render_template, request

functions_assignment_bp = Blueprint("functions_assignment", __name__)

# -----------------------
# Helpers
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

def _grade_mcq(item: Dict[str, Any], ans: Dict[str, Any]) -> Tuple[int, str]:
    picked = (ans or {}).get("choice", "")
    ok = str(picked) == str(item.get("expected"))
    return (10 if ok else 0), ("Correct." if ok else "Not correct.")

def _grade_yesno(item: Dict[str, Any], ans: Dict[str, Any]) -> Tuple[int, str]:
    yn = (ans or {}).get("yes", "")
    correct = bool(item.get("expected_yes", False))
    ok = yn.lower() in ("yes", "y", "true", "t", "igen", "i") if correct else yn.lower() in ("no", "n", "false", "f", "nem")
    return (10 if ok else 0), ("Correct." if ok else "Not correct.")

def _grade_yesno_plus_text(item: Dict[str, Any], ans: Dict[str, Any]) -> Tuple[int, str]:
    s, f = _grade_yesno(item, ans)
    txt = (ans or {}).get("text", "").strip()
    # Small bonus for giving any justification
    bonus = 2 if txt else 0
    return min(10, s + bonus), (f if txt else f + " • Add a brief reason.")

def _grade_short_number(item: Dict[str, Any], ans: Dict[str, Any]) -> Tuple[int, str]:
    expected = float(item.get("expected"))
    try:
        got = float((ans or {}).get("value", ""))
    except Exception:
        return 0, "Enter a number."
    ok = _float_eq(got, expected)
    return (10 if ok else 0), ("Correct." if ok else f"Expected {expected:g}.")

def _grade_csv_float_set(item: Dict[str, Any], ans: Dict[str, Any]) -> Tuple[int, str]:
    expected: List[float] = item.get("expected", [])
    got_list = _as_float_list((ans or {}).get("values", ""))
    # set‑like comparison with tolerance
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
    missing = [e for i, e in enumerate(expected) if not used[i]]
    fb_bits = []
    if missing:
        fb_bits.append("Missing: " + ", ".join(f"{m:g}" for m in missing))
    if extras:
        fb_bits.append(f"{extras} extra value(s).")
    return score, ("All correct." if not fb_bits else " | ".join(fb_bits))

def _grade_pairgrid(item: Dict[str, Any], ans: Dict[str, Any]) -> Tuple[int, str]:
    """
    Student sends: {"pairs": [[a,b], [a,b], ...]}
    We compare against item["expected_pairs"] (same shape), order‑insensitive.
    """
    expected_pairs: List[List[float]] = item.get("expected_pairs", [])
    got_pairs: List[List[float]] = (ans or {}).get("pairs", [])
    # normalize to tuples of strings for comparison
    def _norm_pair(p):
        return (str(p[0]), str(p[1]))
    expected_set = {_norm_pair(p) for p in expected_pairs}
    got_set = {_norm_pair(p) for p in got_pairs if isinstance(p, (list, tuple)) and len(p) == 2}

    correct = len(expected_set & got_set)
    missing = expected_set - got_set
    extra = got_set - expected_set

    n = max(1, len(expected_set))
    score = max(0, min(10, round(10 * (correct - 0.5 * len(extra)) / n)))
    fb = []
    if missing:
        fb.append("Missing: " + ", ".join([f"({a},{b})" for a, b in sorted(missing)]))
    if extra:
        fb.append("Extra: " + ", ".join([f"({a},{b})" for a, b in sorted(extra)]))
    return score, ("All pairs correct." if not fb else " | ".join(fb))

def _grade_integer(item: Dict[str, Any], ans: Dict[str, Any]) -> Tuple[int, str]:
    try:
        got = int((ans or {}).get("value", ""))
    except Exception:
        return 0, "Enter an integer."
    ok = (got == int(item.get("expected", 0)))
    return (10 if ok else 0), ("Correct." if ok else f"Expected {int(item.get('expected', 0))}.")

# -----------------------
# Manifest (content)
# -----------------------

def _manifest_functions() -> Dict[str, Any]:
    """
    Assignment: Functions & Relations (Geology)
    - Mirrors the structure/UX of your logic assignment.
    """
    return {
        "assignment": "Assignment — Functions & Relations (Geology)",
        "hint": "Depth → Porosity; Relations are chosen true pairs; A×B lists all possible pairs.",
        "items": [
            # 1) MCQ — definition of relation
            {
                "id": "FQ1",
                "kind": "mcq",
                "title": "1) What is a relation from depths A to porosity values B?",
                "options": [
                    {"id": "A", "label": "All pairs you could imagine between A and B."},
                    {"id": "B", "label": "The pairs that are actually true in your data (picked from A×B)."},
                    {"id": "C", "label": "Only one‑to‑one pairings."},
                    {"id": "D", "label": "Just a list of porosity numbers."},
                ],
                "expected": "B",
            },
            # 2) MCQ — definition of function
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
            # 3) Pairgrid — measured relation (true pairs M)
            {
                "id": "FQ3",
                "kind": "pairgrid",
                "title": "3) Mark the true measurement pairs M (depth, porosity).",
                "A": [1198, 1200, 1203],
                "B": [0.19, 0.21, 0.24],
                "note": "Tick the pairs that appear in your log.",
                "expected_pairs": [[1198, 0.19], [1200, 0.24], [1203, 0.21]],
            },
            # 4) Short number — evaluate F(1200)
            {
                "id": "FQ4",
                "kind": "short_number",
                "title": "4) If F(1198)=0.19, F(1200)=0.24, F(1203)=0.21, what is F(1200)?",
                "expected": 0.24,
            },
            # 5) Pairgrid — depth→depth 'shallower than'
            {
                "id": "FQ5",
                "kind": "pairgrid",
                "title": "5) Depth relation R_shallow: tick pairs (x,y) with x is shallower than y.",
                "A": [1198, 1200, 1203],
                "B": [1200, 1203, 1205],
                "expected_pairs": [[1198, 1200], [1198, 1203], [1198, 1205], [1200, 1203], [1200, 1205], [1203, 1205]],
            },
            # 6) Pairgrid — porosity↔porosity “similar within ±0.02”
            {
                "id": "FQ6",
                "kind": "pairgrid",
                "title": "6) Porosity relation R_close: |φ1 − φ2| ≤ 0.02 (tick all true pairs).",
                "A": [0.19, 0.20, 0.24],
                "B": [0.19, 0.20, 0.24],
                "expected_pairs": [[0.19, 0.19], [0.19, 0.20], [0.20, 0.19], [0.20, 0.20], [0.24, 0.24]],
            },
            # 7) Yes/No + brief reason — duplicate depth
            {
                "id": "FQ7",
                "kind": "yesno_plus_text",
                "title": "7) M = {(1600,0.18), (1602,0.22), (1602,0.26), (1605,0.21)} — Is “depth→porosity” a function?",
                "expected_yes": False,
            },
            # 8) CSV float set — range
            {
                "id": "FQ8",
                "kind": "csv_float_set",
                "title": "8) List the RANGE (values actually seen) for F in Q4 (comma‑separated).",
                "hint": "Example format: 0.19, 0.22, 0.24",
                "expected": [0.19, 0.21, 0.24],
            },
            # 9) Integer — size of A×B
            {
                "id": "FQ9",
                "kind": "integer",
                "title": "9) If |A|=3 depths and |B|=4 porosity values, how many pairs are in A×B?",
                "expected": 12,
            },
            # 10) Yes/No — clean function
            {
                "id": "FQ10",
                "kind": "yesno",
                "title": "10) If every depth has exactly one porosity after cleaning duplicates, is it a function?",
                "expected_yes": True,
            },
        ],
    }

# -----------------------
# Routes
# -----------------------

@functions_assignment_bp.route("/functions-assignment")
def functions_assignment_home():
    return render_template("assignment_functions.html")

@functions_assignment_bp.route("/functions-assignment/api/generate", methods=["POST"])
def functions_assignment_generate():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    neptun = (data.get("neptun") or "").strip().upper()
    manifest = _manifest_functions()
    manifest["student"] = {"name": name, "neptun": neptun}
    return jsonify(manifest)

@functions_assignment_bp.route("/functions-assignment/api/grade", methods=["POST"])
def functions_assignment_grade():
    data = request.get_json(force=True, silent=True) or {}
    answers: List[Dict[str, Any]] = data.get("answers", [])
    manifest = _manifest_functions()
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
                score, fb = _grade_yesno_plus_text(item, a)
            elif kind == "short_number":
                score, fb = _grade_short_number(item, a)
            elif kind == "csv_float_set":
                score, fb = _grade_csv_float_set(item, a)
            elif kind == "pairgrid":
                score, fb = _grade_pairgrid(item, a)
            elif kind == "integer":
                score, fb = _grade_integer(item, a)
            else:
                score, fb = 0, "Unknown item type."
        except Exception as e:
            score, fb = 0, f"Grading error: {e}"

        per_item.append({"id": qid, "score": int(score), "feedback": fb})
        total += int(score)
        count += 1

    overall_pct = round(total / (max(1, count) * 10) * 100)
    summary = (
        "Excellent — solid on functions/relations."
        if overall_pct >= 90 else
        "Good — tighten any pairgrid or range items per feedback."
        if overall_pct >= 75 else
        "Progressing — review function definition (one input → one output) and A×B."
        if overall_pct >= 60 else
        "Revisit the basics: relation vs function, and how we mark true pairs."
    )

    return jsonify({
        "per_item": per_item,
        "overall_pct": overall_pct,
        "pass": overall_pct >= 70,
        "summary": summary,
    })
