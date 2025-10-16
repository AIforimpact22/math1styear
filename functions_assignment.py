# functions_assignment.py
from __future__ import annotations

import copy
import json
import os
from typing import Any, Dict, List, Tuple

from flask import Blueprint, jsonify, render_template, request

# --- OpenAI SDK (uses OPENAI_API_KEY from env) ---
try:
    from openai import OpenAI
    _OPENAI_AVAILABLE = True
except Exception:
    _OPENAI_AVAILABLE = False

functions_assignment_bp = Blueprint(
    "functions_assignment", __name__, url_prefix="/assignment-3"
)

OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")

# -----------------------
# Helpers
# -----------------------
def _get_openai_client() -> "OpenAI|None":
    if not _OPENAI_AVAILABLE:
        return None
    try:
        return OpenAI()  # will pick up OPENAI_API_KEY from environment
    except Exception:
        return None

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
            pass
    return vals

# -----------------------
# Bilingual helper
# -----------------------
def BIL(en: str, hu: str) -> str:
    return f"EN: {en} • HU: {hu}"

# -----------------------
# LLM grading (bilingual, no spoilers)
# -----------------------
_BASE_SYSTEM = (
    "You are a precise, fair geology TA. Grade student answers concisely.\n"
    "Return STRICT JSON with keys: score (integer 0..MAX), "
    "feedback_en (<=2 short sentences in English), "
    "feedback_hu (<=2 short sentences in Hungarian).\n"
    "Never reveal the solution, numbers, or exact pairs. Provide hints only."
)

def _grade_text_llm(rubric: str, student_text: str, max_points: int = 10) -> Tuple[int, str]:
    client = _get_openai_client()
    if not client:
        return 0, BIL(
            "Automated evaluation unavailable. Please justify with clear references to the context.",
            "Az automatikus értékelés nem elérhető. Kérjük, indokolj világosan a kontextusra hivatkozva."
        )
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _BASE_SYSTEM},
                {"role": "user", "content": (
                    f"MAX={max_points}\n"
                    f"Rubric:\n{rubric}\n\n"
                    f"Student answer:\n{student_text.strip()}"
                )},
            ],
        )
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        score = int(data.get("score", 0))
        score = max(0, min(max_points, score))
        feedback_en = str(data.get("feedback_en", "")).strip() or "Evaluated."
        feedback_hu = str(data.get("feedback_hu", "")).strip() or "Értékelve."
        # belt-and-braces: avoid spoiler phrasing
        for bad in ("Expected", "expected", "Correct is", "The answer is"):
            feedback_en = feedback_en.replace(bad, "Hint")
            feedback_hu = feedback_hu.replace(bad, "Tipp")
        return score, BIL(feedback_en, feedback_hu)
    except Exception:
        return 0, BIL(
            "Evaluation error. Make your explanation concrete and tied to the context.",
            "Értékelési hiba. Legyen a magyarázat konkrét és a kontextushoz kötött."
        )

# -----------------------
# Objective graders (bilingual, hint-only)
# -----------------------
def _grade_mcq(item: Dict[str, Any], ans: Dict[str, Any]) -> Tuple[int, str]:
    picked = (ans or {}).get("choice", "")
    ok = str(picked) == str(item.get("expected"))
    return (10 if ok else 0), (BIL("Correct.", "Helyes.") if ok else
                               BIL("Not correct — revisit the definition (no spoilers).",
                                   "Nem helyes — nézd át a definíciót (spoilerek nélkül)."))

def _grade_yesno(item: Dict[str, Any], ans: Dict[str, Any]) -> Tuple[int, str]:
    yn = (ans or {}).get("yes", "")
    correct = bool(item.get("expected_yes", False))
    ok = yn.lower() in ("yes", "y", "true", "t", "igen", "i") if correct else yn.lower() in ("no", "n", "false", "f", "nem")
    return (10 if ok else 0), (BIL("Correct.", "Helyes.") if ok else
                               BIL("Not correct — check the rule (no spoilers).",
                                   "Nem helyes — ellenőrizd a szabályt (spoilerek nélkül)."))

def _grade_yesno_plus_text_llm(item: Dict[str, Any], ans: Dict[str, Any]) -> Tuple[int, str]:
    # yes/no component (6 pts)
    yn_score_full, _yn_fb = _grade_yesno(item, ans)
    yn_points = 6 if yn_score_full == 10 else 0
    # LLM justification (4 pts)
    rubric = item.get("llm_rubric", "Explain briefly and correctly using the provided context; avoid vague claims.")
    text = (ans or {}).get("text", "")
    text_points, text_fb = _grade_text_llm(rubric, text, max_points=4)
    total = min(10, yn_points + text_points)
    if yn_points == 6 and text_points >= 3:
        fb = BIL("Correct and well-justified.", "Helyes és jól indokolt.")
    else:
        bits_en, bits_hu = [], []
        if yn_points < 6:
            bits_en.append("Y/N seems off — re-check the function rule.")
            bits_hu.append("A igen/nem rész hibás — ellenőrizd a függvény definícióját.")
        if text_points < 3:
            bits_en.append("Justification needs clearer reference to the context.")
            bits_hu.append("Az indoklás legyen konkrétabb és hivatkozzon a kontextusra.")
        fb = BIL(" ".join(bits_en) or "Good.", " ".join(bits_hu) or "Jó.")
    return total, fb

def _grade_short_number(item: Dict[str, Any], ans: Dict[str, Any]) -> Tuple[int, str]:
    try:
        got = float((ans or {}).get("value", ""))
    except Exception:
        return 0, BIL("Enter a number (e.g., 0.24).", "Adj meg számot (pl. 0,24).")
    ok = _float_eq(got, float(item.get("expected")))
    return (10 if ok else 0), (BIL("Correct.", "Helyes.") if ok else
                               BIL("Not correct — re-check the mapping table (no spoilers).",
                                   "Nem helyes — nézd át a hozzárendelést (spoilerek nélkül)."))

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
    if score == 10:
        fb = BIL("Your set looks consistent.", "A megadott halmaz konzisztens.")
    else:
        fb = BIL("Some values seem missing or extra — compare with the context (no spoilers).",
                 "Hiányzó vagy felesleges értékek lehetnek — vessd össze a kontextussal (spoiler nélkül).")
    return score, fb

def _grade_pairgrid(item: Dict[str, Any], ans: Dict[str, Any]) -> Tuple[int, str]:
    expected_pairs: List[List[float]] = item.get("expected_pairs", [])
    got_pairs: List[List[float]] = (ans or {}).get("pairs", [])
    def _norm_pair(p): return (str(p[0]), str(p[1]))
    expected_set = {_norm_pair(p) for p in expected_pairs}
    got_set = {_norm_pair(p) for p in got_pairs if isinstance(p, (list, tuple)) and len(p) == 2}
    correct = len(expected_set & got_set)
    extra = len(got_set - expected_set)
    n = max(1, len(expected_set))
    score = max(0, min(10, round(10 * (correct - 0.5 * extra) / n)))
    if score == 10:
        fb = BIL("Your selected pairs are consistent.", "A kiválasztott párok konzisztensnek tűnnek.")
    else:
        fb = BIL("Some pairs seem missing or extra — re-check the relation rule (no spoilers).",
                 "Hiányzó vagy felesleges párok lehetnek — ellenőrizd a reláció szabályát (spoiler nélkül).")
    return score, fb

def _grade_integer(item: Dict[str, Any], ans: Dict[str, Any]) -> Tuple[int, str]:
    try:
        got = int((ans or {}).get("value", ""))
    except Exception:
        return 0, BIL("Enter an integer.", "Adj meg egész számot.")
    ok = (got == int(item.get("expected", 0)))
    return (10 if ok else 0), (BIL("Correct.", "Helyes.") if ok else
                               BIL("Hint: |A×B| = |A| · |B|.", "Tipp: |A×B| = |A| · |B|."))

# -----------------------
# Manifest (bilingual) — with context
# -----------------------
def _manifest_functions() -> Dict[str, Any]:
    """
    10 items; 5 qualitative (LLM-graded). Bilingual EN–HU.
    """
    return {
        "assignment": "Assignment — Functions & Relations (Geology) / Feladat — Függvények és Relációk (Geológia)",
        "context": (
            "EN: Background • You are a junior petrophysicist analyzing a clean sandstone interval in Well A "
            "(1195–1208 m). Porosity φ (fraction, e.g., 0.24) is measured from density/neutron logs. Typical noise "
            "is ±0.02 due to calibration and borehole effects. Duplicate readings may occur at the same depth on repeat "
            "passes. We study relations on two sets: A = {depths in meters}, B = {porosity values}. A×B is all possible "
            "(depth, φ) pairs. A relation is the subset of TRUE pairs in the data; a function requires each depth in A "
            "to map to exactly one φ in B.\n"
            "HU: Háttér • Kezdő petrofizikus vagy, egy tiszta homokkő szakaszt elemzel az A kútban (1195–1208 m). "
            "A porozitás φ (arány, pl. 0,24) sűrűség/neutron szelvényből származik. A tipikus zaj ±0,02 a kalibráció és "
            "a furatviszonyok miatt. Ismételt futásoknál ugyanazon mélységnél duplikált értékek előfordulhatnak. "
            "Két halmazon vizsgálunk relációkat: A = {mélységek méterben}, B = {porozitásértékek}. A×B az összes lehetséges "
            "(mélység, φ) pár. Egy reláció az igaz párok részhalmaza; függvény esetén A minden eleméhez pontosan egy φ tartozik B-ben."
        ),
        "hint": "Units / Mértékegységek: depth/mélység [m]; porosity/porozitás [0..1]. R_close: |φ1−φ2| ≤ 0.02; R_shallow: x<y.",
        "items": [
            # 1) Qualitative
            {
                "id": "FQ1",
                "kind": "long_text",
                "title": "1) In your own words, what is a relation A→B here? (2–3 sentences) / "
                         "1) Saját szavaiddal: mi a reláció A→B ebben a helyzetben? (2–3 mondat)",
                "llm_rubric": (
                    "8–10 if: (a) a relation is a set of TRUE (depth, φ) pairs picked from A×B, "
                    "(b) tied to log-derived porosity and context, (c) does NOT claim one-to-one. "
                    "4–7 partial; 0–3 off-topic or wrong."
                ),
            },
            # 2) MCQ — definition of function
            {
                "id": "FQ2",
                "kind": "mcq",
                "title": "2) When is “depth → porosity” a function? / 2) Mikor függvény a „mélység → porozitás” leképezés?",
                "options": [
                    {"id": "A", "label": "EN) Every depth has exactly one porosity. • HU) Minden mélységhez pontosan egy porozitás tartozik."},
                    {"id": "B", "label": "EN) A depth may have two porosities. • HU) Egy mélységhez két porozitás is tartozhat."},
                    {"id": "C", "label": "EN) Only when porosity > 0.20. • HU) Csak ha a porozitás > 0,20."},
                    {"id": "D", "label": "EN) Only if all wells use the same tool. • HU) Csak ha minden kút ugyanazt a műszert használja."},
                ],
                "expected": "A",
            },
            # 3) Pairgrid — measured relation
            {
                "id": "FQ3",
                "kind": "pairgrid",
                "title": "3) Mark TRUE measurement pairs M (depth, φ). / 3) Jelöld az IGAZ mérési párokat M (mélység, φ).",
                "A": [1198, 1200, 1203],
                "B": [0.19, 0.21, 0.24],
                "note": "EN) Tick pairs that appear in your log. • HU) Pipáld ki a szelvényben szereplő párokat.",
                "expected_pairs": [[1198, 0.19], [1200, 0.24], [1203, 0.21]],
            },
            # 4) Qualitative — interpret a value
            {
                "id": "FQ4",
                "kind": "long_text",
                "title": "4) Interpret F(1200)=0.24 in plain language. / 4) Magyarázd el közérthetően: F(1200)=0,24.",
                "llm_rubric": (
                    "Look for correct mapping of 1200 m to φ=0.24 (24%), physical meaning, and context; "
                    "no overclaiming. 10 crisp; 5–8 mostly correct; 0–4 confused."
                ),
            },
            # 5) Pairgrid — shallower-than
            {
                "id": "FQ5",
                "kind": "pairgrid",
                "title": "5) R_shallow: tick (x,y) with x is shallower than y. / 5) R_shallow: jelöld az (x,y) párokat, ahol x sekélyebb mint y.",
                "A": [1198, 1200, 1203],
                "B": [1200, 1203, 1205],
                "expected_pairs": [[1198, 1200], [1198, 1203], [1198, 1205], [1200, 1203], [1200, 1205], [1203, 1205]],
            },
            # 6) Qualitative — R_close properties
            {
                "id": "FQ6",
                "kind": "long_text",
                "title": "6) R_close on porosity (|φ1−φ2| ≤ 0.02): reflexive, symmetric, transitive? Explain briefly. / "
                         "6) R_close porozitásra (|φ1−φ2| ≤ 0,02): reflexív, szimmetrikus, tranzitív? Röviden indokold.",
                "llm_rubric": (
                    "Reflexive & symmetric yes; not necessarily transitive. Score by correctness and clarity; no numeric spoilers."
                ),
            },
            # 7) Yes/No + brief reason — duplicate depth
            {
                "id": "FQ7",
                "kind": "yesno_plus_text",
                "title": "7) M = {(1600,0.18), (1602,0.22), (1602,0.26), (1605,0.21)} — Is depth→φ a function? Justify briefly. / "
                         "7) ... — Függvény-e a mélység→φ? Rövid indoklás.",
                "expected_yes": False,
                "llm_rubric": (
                    "Mention same input (depth 1602) mapping to two outputs — violates function definition. 3–4 good; else 0–2."
                ),
            },
            # 8) CSV set — range
            {
                "id": "FQ8",
                "kind": "csv_float_set",
                "title": "8) List the RANGE (values actually seen) for F in Q3/Q4 (comma-separated). / "
                         "8) Sorold fel F ÉRTÉKKÉSZLETÉT Q3/Q4 alapján (vesszővel).",
                "hint": "EN) Example: 0.19, 0.21, 0.24 • HU) Példa: 0,19, 0,21, 0,24",
                "expected": [0.19, 0.21, 0.24],
            },
            # 9) Integer — size of A×B
            {
                "id": "FQ9",
                "kind": "integer",
                "title": "9) If |A|=3 and |B|=4, how many pairs in A×B? / 9) Ha |A|=3 és |B|=4, hány pár van A×B-ben?",
                "expected": 12,
            },
            # 10) Qualitative — cleaning pipeline
            {
                "id": "FQ10",
                "kind": "long_text",
                "title": "10) After de-duplication, propose a simple pipeline to ensure depth→φ is a function (and a tradeoff). / "
                         "10) Duplikátum-szűrés után javasolj egy egyszerű folyamatot, hogy a mélység→φ függvény legyen (és említs kompromisszumot).",
                "llm_rubric": (
                    "One per depth (e.g., median/quality flag/best run), note tradeoff (variance loss/bias/uncertainty)."
                ),
            },
        ],
    }

# -----------------------
# Public (sanitized) manifest: remove answers & rubrics
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
    manifest = _manifest_functions()  # internal copy WITH solutions/rubrics
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
                score, fb = 0, BIL("Unknown item type.", "Ismeretlen feladattípus.")
        except Exception as e:
            score, fb = 0, BIL(f"Grading error: {e}", f"Értékelési hiba: {e}")

        per_item.append({"id": qid, "score": int(score), "feedback": fb})
        total += int(score)
        count += 1

    overall_pct = round(total / (max(1, count) * 10) * 100)
    if overall_pct >= 90:
        summary = BIL("Excellent — strong grasp of relations/functions and context.",
                      "Kiváló — erős megértés relációkból/függvényekből és a kontextusból.")
    elif overall_pct >= 75:
        summary = BIL("Good — tighten pair selections and explanations with context.",
                      "Jó — pontosíts a párokon és az indokláson, hivatkozz a kontextusra.")
    elif overall_pct >= 60:
        summary = BIL("Progressing — review the function rule (one input→one output) and relation rules.",
                      "Fejlődő — ismételd át a függvény (egy bemenet→egy kimenet) és relációs szabályokat.")
    else:
        summary = BIL("Revisit the basics: relation vs function, A×B, and the scenario context.",
                      "Térj vissza az alapokhoz: reláció vs függvény, A×B és a feladat kontextusa.")

    return jsonify({
        "per_item": per_item,
        "overall_pct": overall_pct,
        "pass": overall_pct >= 70,
        "summary": summary,
    })
