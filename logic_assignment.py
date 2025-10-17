# logic_assignment.py  — Lecture 3 autograder (lenient, robust)
# - Gentle OpenAI text grading (mercy floor; friendly fallbacks)
# - Accepts ¬ ∧ ∨ and also →, ↔ (and ASCII ->, <->)
# - Handles truth_table_plus_yesno
# - Deduplicates answers by id (keep last)
# - Truth-table inputs accept T/F/1/0/true/false

from __future__ import annotations

import itertools
import json
import os
import re
from typing import Any, Dict, List, Literal, Optional, Tuple

from flask import Blueprint, jsonify, render_template, request

# ---------- OpenAI (Responses API) ----------
try:
    from openai import OpenAI  # pip install openai
    _OPENAI_CLIENT: Optional[OpenAI] = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
except Exception:
    _OPENAI_CLIENT = None  # graceful fallback when SDK/env not available

logic_assignment_bp = Blueprint("logic_assignment", __name__)

# ======================================================
# Core logic parsing/evaluation
# ======================================================

# Course vars allowed (lowercase)
_ALLOWED_VARS = set(list("pqroiy"))

# Accept these characters directly; multi-char aliases normalized first.
_ALLOWED_TOKENS = set(list("pqroiy(),`~¬∧∨→↔"))

# Common aliases (single-char). Multi-char handled in _normalize_expr().
_ALIAS_MAP = {
    "¬": ",",   # NOT
    "∧": "`",   # AND
    "∨": "~",   # OR
    # → and ↔ are parsed as dedicated tokens, then evaluated directly
}

Token = Literal["VAR", "NOT", "AND", "OR", "IMP", "IFF", "LPAREN", "RPAREN"]

def _normalize_expr(expr: str) -> str:
    """
    Normalize user input:
    - strip spaces
    - lowercase vars
    - translate known aliases (¬, ∧, ∨)
    - convert ASCII '->' to '→' and '<->' to '↔'
    - validate allowed character set (we tolerate → and ↔)
    """
    s = (expr or "").strip()
    if not s:
        return s
    # ASCII implication/equivalence to unicode
    s = s.replace("<->", "↔").replace("->", "→")
    # Remove whitespace, lowercase
    s = re.sub(r"\s+", "", s).lower()
    # Map simple aliases
    for bad, good in _ALIAS_MAP.items():
        s = s.replace(bad, good)
    # Quick check: only expected token characters
    if not set(s) <= _ALLOWED_TOKENS:
        raise ValueError("Use only the on‑screen symbols or these: , (NOT), ` (AND), ~ (OR), parentheses, variables (p,q,r,o,i,y). "
                         "Implication (→) and equivalence (↔) are also accepted.")
    return s

def _tokenize(s: str) -> List[Tuple[Token, str]]:
    """Turn normalized string into tokens."""
    out: List[Tuple[Token, str]] = []
    for c in s:
        if c in _ALIAS_MAP:
            c = _ALIAS_MAP[c]  # already normalized, but safe
        if c in _ALLOWED_VARS:
            out.append(("VAR", c))
        elif c == ",":
            out.append(("NOT", c))
        elif c == "`":
            out.append(("AND", c))
        elif c == "~":
            out.append(("OR", c))
        elif c == "→":
            out.append(("IMP", c))
        elif c == "↔":
            out.append(("IFF", c))
        elif c == "(":
            out.append(("LPAREN", c))
        elif c == ")":
            out.append(("RPAREN", c))
        else:
            raise ValueError(f"Unexpected character: {c!r}")
    return out

_PRECEDENCE = {"IFF": 1, "IMP": 2, "OR": 3, "AND": 4, "NOT": 5}
_ASSOC = {"IFF": "R", "IMP": "R", "OR": "L", "AND": "L", "NOT": "R"}

def _to_rpn(tokens: List[Tuple[Token, str]]) -> List[Tuple[Token, str]]:
    """Shunting-yard to Reverse Polish Notation."""
    output: List[Tuple[Token, str]] = []
    ops: List[Tuple[Token, str]] = []
    for tok, val in tokens:
        if tok == "VAR":
            output.append((tok, val))
        elif tok == "NOT":
            ops.append((tok, val))
        elif tok in ("AND", "OR", "IMP", "IFF"):
            while ops and ops[-1][0] not in ("LPAREN",):
                top = ops[-1][0]
                if (_ASSOC[tok] == "L" and _PRECEDENCE[top] >= _PRECEDENCE[tok]) or \
                   (_ASSOC[tok] == "R" and _PRECEDENCE[top] >  _PRECEDENCE[tok]):
                    output.append(ops.pop())
                else:
                    break
            ops.append((tok, val))
        elif tok == "LPAREN":
            ops.append((tok, val))
        elif tok == "RPAREN":
            while ops and ops[-1][0] != "LPAREN":
                output.append(ops.pop())
            if not ops:
                raise ValueError("Mismatched parentheses.")
            ops.pop()
    while ops:
        if ops[-1][0] in ("LPAREN", "RPAREN"):
            raise ValueError("Mismatched parentheses.")
        output.append(ops.pop())
    return output

def _eval_rpn(rpn: List[Tuple[Token, str]], env: Dict[str, bool]) -> bool:
    """Evaluate RPN with env for variables."""
    st: List[bool] = []
    for tok, sym in rpn:
        if tok == "VAR":
            st.append(env[sym])
        elif tok == "NOT":
            if not st:
                raise ValueError("Missing operand for NOT.")
            st.append(not st.pop())
        elif tok in ("AND", "OR", "IMP", "IFF"):
            if len(st) < 2:
                raise ValueError("Missing operands for binary operator.")
            b = st.pop(); a = st.pop()
            if tok == "AND":
                st.append(a and b)
            elif tok == "OR":
                st.append(a or b)
            elif tok == "IMP":
                st.append((not a) or b)  # a → b ≡ ¬a ∨ b
            elif tok == "IFF":
                st.append((a and b) or ((not a) and (not b)))  # a ↔ b
    if len(st) != 1:
        raise ValueError("Malformed expression.")
    return st[0]

def eval_expr(expr: str, env: Dict[str, bool]) -> bool:
    s = _normalize_expr(expr)
    tokens = _tokenize(s)
    rpn = _to_rpn(tokens)
    return _eval_rpn(rpn, env)

def equivalent(expr_a: str, expr_b: str, vars_used: List[str]) -> Tuple[bool, Optional[Dict[str, bool]]]:
    """Return (equivalent?, counterexample_env_or_None)."""
    for values in itertools.product([True, False], repeat=len(vars_used)):
        env = {v: val for v, val in zip(vars_used, values)}
        try:
            va = eval_expr(expr_a, env)
            vb = eval_expr(expr_b, env)
        except Exception:
            return False, env
        if va != vb:
            return False, env
    return True, None

# ======================================================
# Manifest — Lecture 3
# ======================================================

def _tt_rows(varnames: List[str]) -> List[Dict[str, bool]]:
    return [{v: t for v, t in zip(varnames, vals)}
            for vals in itertools.product([True, False], repeat=len(varnames))]

def _manifest_lecture3() -> Dict[str, Any]:
    q3_vars = ["p", "q", "r"]
    q3_cols = [
        {"label": "p ~ q", "expr": "p ~ q"},
        {"label": ",r", "expr": ",r"},
        {"label": "(p ~ q) ` ,r", "expr": "(p ~ q) ` ,r"},
    ]
    q4_vars = ["p", "q"]
    q4_cols = [
        {"label": ",p", "expr": ",p"},
        {"label": ",p ~ q", "expr": ",p ~ q"},
    ]
    q5_vars = ["p", "q"]
    q5_cols = [
        {"label": "p ` q", "expr": "p ` q"},
        {"label": ",p", "expr": ",p"},
        {"label": ",q", "expr": ",q"},
        {"label": ",p ` ,q", "expr": ",p ` ,q"},
        {"label": "(p ` q) ~ (,p ` ,q)", "expr": "(p ` q) ~ (,p ` ,q)"},
        {"label": "(p ↔ q)", "expr": "(p ` q) ~ (,p ` ,q)"},
    ]
    q6_vars = ["p", "q"]
    q6_cols = [
        {"label": ",p", "expr": ",p"},
        {"label": ",q", "expr": ",q"},
        {"label": "p ` ,q", "expr": "p ` ,q"},
        {"label": ",p ` q", "expr": ",p ` q"},
        {"label": "(p ` ,q) ~ (,p ` q)", "expr": "(p ` ,q) ~ (,p ` q)"},
    ]
    q8_vars = ["p", "q"]
    q8_cols = [{"label": "p ` q", "expr": "p ` q"}, {"label": ",(p ` q)", "expr": ",(p ` q)"}]
    q9_vars = ["p", "q"]
    q9_cols = [{"label": "p ~ q", "expr": "p ~ q"}, {"label": ",(p ~ q)", "expr": ",(p ~ q)"}]

    return {
        "assignment": "Assignment / Feladatlap — Lecture 3",
        "allowed_ops": "Use the on‑screen symbols: ¬ ∧ ∨ → ↔, parentheses, and variables (p,q,r,o,i,y). ASCII ',', '`', '~', ->, <-> also accepted.",
        "items": [
            # 1) Translate to symbols — now answered via on‑screen picker in the UI
            {"id": "L3Q1a", "kind": "formula", "vars": ["p", "q", "r"],
             "title": "1a) Translate to symbols",
             "en": "If the rock is sandstone and contains fossils, then it formed in a shallow marine environment.",
             "hu": "Ha a kőzet homokkő és fosszíliákat tartalmaz, akkor sekély tengeri környezetben képződött.",
             "expected": ",(p ` q) ~ r"},
            {"id": "L3Q1b", "kind": "formula", "vars": ["p", "q"],
             "title": "1b) Translate to symbols",
             "en": "The rock is not sandstone, but it contains fossils.",
             "hu": "A kőzet nem homokkő, de fosszíliákat tartalmaz.",
             "expected": ",p ` q"},
            {"id": "L3Q1c", "kind": "formula", "vars": ["p", "q", "r"],
             "title": "1c) Translate to symbols",
             "en": "If it did not form in a shallow marine environment, then it is not sandstone or it does not contain fossils.",
             "hu": "Ha nem sekély tengeri környezetben képződött, akkor nem homokkő, vagy nem tartalmaz fosszíliákat.",
             "expected": ",(,r) ~ (,p ~ ,q)"},
            {"id": "L3Q1d", "kind": "formula", "vars": ["p", "q"],
             "title": "1d) Translate to symbols",
             "en": "The rock is sandstone exactly when it contains fossils.",
             "hu": "A kőzet akkor és csak akkor homokkő, ha fosszíliákat tartalmaz.",
             "expected": "(p ` q) ~ (,p ` ,q)"},

            # 3) Truth table — (p ~ q) ` ,r
            {"id": "L3Q3", "kind": "truth_table", "title": "3) Truth table — (p ~ q) ` ,r",
             "vars": q3_vars, "rows": _tt_rows(q3_vars), "columns": q3_cols},

            # 4) Implication via helper column: p→q ≡ ,p ~ q
            {"id": "L3Q4", "kind": "truth_table",
             "title": "4) Implication via helper column — build p→q as ,p ~ q",
             "vars": q4_vars, "rows": _tt_rows(q4_vars), "columns": q4_cols},

            # 5) Biconditional identity
            {"id": "L3Q5", "kind": "truth_table",
             "title": "5) (p ` q) ~ (,p ` ,q) is equivalent to (p ↔ q)",
             "vars": q5_vars, "rows": _tt_rows(q5_vars), "columns": q5_cols},

            # 6) XOR table + one sentence (text graded by GPT or fallback)
            {"id": "L3Q6", "kind": "truth_table_plus_text",
             "title": "6) XOR: (p ` ,q) ~ (,p ` q)",
             "vars": q6_vars, "rows": _tt_rows(q6_vars), "columns": q6_cols,
             "text_prompt_en": "In one sentence: when is XOR true?",
             "text_prompt_hu": "Egy mondatban: mikor igaz a kizáró VAGY?"},

            # 7) De Morgan — tautology checks
            {"id": "L3Q7a", "kind": "yesno",
             "title": "7a) ,(p ~ q) ↔ (,p ` ,q) — tautology?", "expected_yes": True},
            {"id": "L3Q7b", "kind": "yesno",
             "title": "7b) ,(p ` q) ↔ (,p ~ ,q) — tautology?", "expected_yes": True},

            # 8) NAND table + yes/no
            {"id": "L3Q8", "kind": "truth_table_plus_yesno",
             "title": "8) NAND: ,(p ` q)",
             "vars": q8_vars, "rows": _tt_rows(q8_vars), "columns": q8_cols,
             "yesno_prompt": "Is NAND true in all cases except when both p and q are true?",
             "expected_yes": True},

            # 9) NOR table + text
            {"id": "L3Q9", "kind": "truth_table_plus_text",
             "title": "9) NOR: ,(p ~ q)",
             "vars": q9_vars, "rows": _tt_rows(q9_vars), "columns": q9_cols,
             "text_prompt_en": "In which single row(s) is NOR true? (e.g., 'p=F, q=F')",
             "text_prompt_hu": "Mely egyetlen sor(ok)ban igaz a NOR? (pl. „p=F, q=F”)"},
            
            # 10) Applied reasoning
            {"id": "L3Q10a", "kind": "formula", "vars": ["o", "y", "i"],
             "title": "10a) Field rule: If (olivine or pyroxene) then igneous.",
             "en": "Use o: olivine, y: pyroxene, i: igneous.",
             "hu": "o: olivin, y: piroxén, i: magmás.",
             "expected": ",(o ~ y) ~ i"},
            {"id": "L3Q10c", "kind": "yesno_plus_text",
             "title": "10c) Is 'Porosity > 0.25 ` Porosity < 0.10' contradictory?",
             "expected_yes": True,
             "text_prompt_en": "Briefly explain why.",
             "text_prompt_hu": "Röviden indokold meg miért."},

            # Text‑Entry 1–5 (symbols only)
            {"id": "L3T1", "kind": "formula", "vars": ["p"], "title": "Text‑Entry 1 (¬p)", "expected": ",p"},
            {"id": "L3T2", "kind": "formula", "vars": ["q"], "title": "Text‑Entry 2 (¬q)", "expected": ",q"},
            {"id": "L3T3", "kind": "formula", "vars": ["p", "q"], "title": "Text‑Entry 3 (p ∧ ¬q)", "expected": "p ` ,q"},
            {"id": "L3T4", "kind": "formula", "vars": ["p", "q"], "title": "Text‑Entry 4 (¬p ∧ q)", "expected": ",p ` q"},
            {"id": "L3T5", "kind": "formula", "vars": ["p", "q"], "title": "Text‑Entry 5 (XOR disjunction)",
             "expected": "(p ` ,q) ~ (,p ` q)"},
        ],
    }

# ======================================================
# OpenAI grader (text answers) — *gentle*
# ======================================================

def _gpt_grade_text(task_id: str, prompt_en: str, prompt_hu: str,
                    student_text: str, expected_summary_en: str, expected_summary_hu: str) -> Tuple[int, str]:
    """
    Score a short EN/HU answer on 0–10. Always gentle:
    - Empty -> 0 with a nudge
    - Offline/error -> 7/10 fallback
    - Online -> clamp to [6,10] (mercy floor)
    """
    if not student_text or not student_text.strip():
        return 0, "Please add a short explanation. / Kérlek írj egy rövid magyarázatot."

    if not _OPENAI_CLIENT:
        return 7, "(Offline) Provisional score. Be concise and include the key idea. / Ideiglenes pontszám; a lényeget írd le röviden."

    schema = {
        "name": "grade_payload",
        "schema": {
            "type": "object",
            "properties": {
                "score": {"type": "integer", "minimum": 0, "maximum": 10},
                "feedback_en": {"type": "string"},
                "feedback_hu": {"type": "string"},
            },
            "required": ["score", "feedback_en", "feedback_hu"],
            "additionalProperties": False,
        }
    }

    system_instructions = (
        "You are a bilingual (EN/HU) logic TA. Grade gently on a 0–10 scale. "
        "Accept either English or Hungarian. Reward core idea over wording. "
        "Return JSON only per the provided schema."
    )

    context_en = f"Expected essence: {expected_summary_en}"
    context_hu = f"Elvárt lényeg: {expected_summary_hu}"
    user_block = (
        f"Task (EN): {prompt_en}\n"
        f"Feladat (HU): {prompt_hu}\n\n"
        f"Student answer / Hallgatói válasz:\n{student_text}"
    )

    try:
        resp = _OPENAI_CLIENT.responses.create(
            model=os.environ.get("OPENAI_GPT_MODEL", "gpt-4o-mini"),
            instructions=system_instructions,
            input=f"{context_en}\n{context_hu}\n\n{user_block}",
            response_format={"type": "json_schema", "json_schema": schema},
        )
        payload = json.loads(resp.output_text)
        raw = int(payload.get("score", 7))
        # Gentle clamp
        score = max(6, min(10, raw))
        feedback_en = payload.get("feedback_en", "").strip() or "OK."
        feedback_hu = payload.get("feedback_hu", "").strip()
        feedback = feedback_en + ((" / " + feedback_hu) if feedback_hu else "")
        return score, feedback
    except Exception:
        return 7, "(Online grader unreachable) Assigned a friendly fallback. / Barátságos tartalék pontszám."

# ======================================================
# Programmatic grading (non-text)
# ======================================================

def _norm_tf_cell(x: Any) -> str:
    """Tolerate T/F/1/0/true/false (case-insensitive)."""
    s = str(x).strip().upper()
    if s in ("T", "TRUE", "1"):
        return "T"
    if s in ("F", "FALSE", "0"):
        return "F"
    return s  # will be compared; empty counts as wrong

def _grade_truth_table(item: Dict[str, Any], answer: Dict[str, Any]) -> Tuple[int, str]:
    vars_used: List[str] = item["vars"]
    rows = item["rows"]; cols = item["columns"]
    submitted: Dict[str, List[str]] = (answer or {}).get("cols", {})
    total_cells = len(rows) * len(cols)
    correct = 0
    first_err: Optional[str] = None

    for col in cols:
        label, expr = col["label"], col["expr"]
        expected_col: List[str] = []
        for r in rows:
            env = {v: bool(r[v]) for v in vars_used}
            truth = eval_expr(expr, env)
            expected_col.append("T" if truth else "F")

        got_col = [_norm_tf_cell(x) for x in submitted.get(label, [])]
        while len(got_col) < len(expected_col):
            got_col.append("")
        for i, (g, e) in enumerate(zip(got_col, expected_col)):
            if g == e:
                correct += 1
            else:
                if not first_err:
                    env = {v: rows[i][v] for v in vars_used}
                    env_str = ", ".join(f"{k}={'T' if v else 'F'}" for k, v in env.items())
                    first_err = f'Column “{label}”, row {i+1} ({env_str}): expected {e}.'
    score = round(10 * (correct / total_cells)) if total_cells else 0
    feedback = "All table cells correct." if correct == total_cells else (first_err or "Fill each cell with T or F.")
    return score, feedback

def _grade_yesno(item: Dict[str, Any], answer: Dict[str, Any]) -> Tuple[int, str]:
    yn = (answer or {}).get("yes", "")
    correct = item.get("expected_yes", False)
    ok = yn.lower() in ("yes", "y", "true", "t", "igen", "i") if correct else yn.lower() in ("no", "n", "false", "f", "nem")
    return (10 if ok else 0), ("Correct." if ok else "Not correct.")

def _grade_formula(item: Dict[str, Any], answer: Dict[str, Any]) -> Tuple[int, str]:
    expr = (answer or {}).get("expr", "")
    expected = item["expected"]; vars_used = item.get("vars", [])
    if not expr:
        return 0, "Build a formula using the on‑screen symbols (or type , ` ~ and parentheses). →, ↔ also accepted."
    try:
        eq, counter = equivalent(expr, expected, vars_used)
    except ValueError as e:
        return 0, f"{e}"
    if eq:
        return 10, "Correct symbolic form."
    env_str = ", ".join(f"{k}={'T' if v else 'F'}" for k, v in (counter or {}).items())
    return 5, f"Not equivalent; differs for: {env_str}. Try rewriting (e.g., p→q ≡ ,p ~ q; p↔q ≡ (p ` q) ~ (,p ` ,q))."

def _grade_formula_plus_text(item: Dict[str, Any], answer: Dict[str, Any]) -> Tuple[int, str]:
    fs, ff = _grade_formula(item, answer)
    text_en = (answer or {}).get("en", "")
    text_hu = (answer or {}).get("hu", "")
    combined_text = (text_en + "\n" + text_hu).strip()
    ts, tf = _gpt_grade_text(
        item["id"],
        "Write the contrapositive in words.",
        "Írd le a kontrapozíciót szavakkal.",
        combined_text,
        expected_summary_en="If it is not igneous, then it contains neither olivine nor pyroxene.",
        expected_summary_hu="Ha nem magmás, akkor sem olivint, sem piroxént nem tartalmaz.",
    )
    score = round((fs + ts) / 2)
    feedback = f"Formula: {ff}  |  Text: {tf}"
    return score, feedback

def _grade_truth_table_plus_text(item: Dict[str, Any], answer: Dict[str, Any]) -> Tuple[int, str]:
    s, f = _grade_truth_table(item, answer)
    text = (answer or {}).get("text", "")
    if item["id"] == "L3Q6":
        ts, tf = _gpt_grade_text(
            item["id"],
            "In one sentence: when is XOR true?",
            "Egy mondatban: mikor igaz a kizáró VAGY?",
            text,
            expected_summary_en="Exactly one of p, q is true (one but not both).",
            expected_summary_hu="Pontosan az egyik igaz (egyik, de nem mindkettő).",
        )
    else:  # L3Q9 NOR text
        ts, tf = _gpt_grade_text(
            item["id"],
            "In which single row(s) is NOR true?",
            "Mely egyetlen sor(ok)ban igaz a NOR?",
            text,
            expected_summary_en="Only when both p and q are false (p=F, q=F).",
            expected_summary_hu="Csak akkor, ha p és q is hamis (p=F, q=F).",
        )
    score = min(10, s + round(ts / 5))  # +0..+2 bonus
    feedback = f"{f}  |  Text: {tf}"
    return score, feedback

def _grade_truth_table_plus_yesno(item: Dict[str, Any], answer: Dict[str, Any]) -> Tuple[int, str]:
    s, f = _grade_truth_table(item, answer)
    ys, yf = _grade_yesno(item, answer)  # expects 'yes' in payload
    # yes/no contributes at most +2
    score = min(10, s + (2 if ys == 10 else 0))
    feedback = f"{f}  |  Yes/No: {yf}"
    return score, feedback

def _grade_yesno_plus_text(item: Dict[str, Any], answer: Dict[str, Any]) -> Tuple[int, str]:
    s, f = _grade_yesno(item, answer)
    txt = (answer or {}).get("text", "")
    ts, tf = _gpt_grade_text(
        item["id"],
        "Is the condition contradictory? Briefly explain why.",
        "Ellentmondásos‑e a feltétel? Röviden indokold meg miért.",
        txt,
        expected_summary_en="Yes; a single porosity value cannot be simultaneously >0.25 and <0.10.",
        expected_summary_hu="Igen; ugyanaz a porozitás nem lehet egyszerre >0,25 és <0,10.",
    )
    score = min(10, s + round(ts / 5))
    feedback = f"{f}  |  Text: {tf}"
    return score, feedback

# ======================================================
# Routes
# ======================================================

@logic_assignment_bp.route("/logic-assignment")
def logic_assignment_home():
    return render_template("assignment_logic.html")

@logic_assignment_bp.route("/logic-assignment/api/generate", methods=["POST"])
def logic_assignment_generate():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    neptun = (data.get("neptun") or "").strip().upper()
    manifest = _manifest_lecture3()
    manifest["student"] = {"name": name, "neptun": neptun}
    return jsonify(manifest)

@logic_assignment_bp.route("/logic-assignment/api/grade", methods=["POST"])
def logic_assignment_grade():
    data = request.get_json(force=True, silent=True) or {}
    answers_in: List[Dict[str, Any]] = data.get("answers", [])

    # --- De-duplicate by id (keep last) ---
    uniq: Dict[str, Dict[str, Any]] = {}
    for a in answers_in:
        qid = a.get("id")
        if qid:
            uniq[qid] = a
    answers: List[Dict[str, Any]] = list(uniq.values())

    manifest = _manifest_lecture3()
    item_by_id = {it["id"]: it for it in manifest["items"]}

    per_item: List[Dict[str, Any]] = []
    total_score = 0
    counted = 0

    for a in answers:
        qid = a.get("id")
        item = item_by_id.get(qid)
        if not item:
            continue
        kind = item["kind"]
        try:
            if kind == "formula":
                score, feedback = _grade_formula(item, a)
            elif kind == "truth_table":
                score, feedback = _grade_truth_table(item, a)
            elif kind == "truth_table_plus_text":
                score, feedback = _grade_truth_table_plus_text(item, a)
            elif kind == "truth_table_plus_yesno":
                score, feedback = _grade_truth_table_plus_yesno(item, a)
            elif kind == "formula_plus_text":
                score, feedback = _grade_formula_plus_text(item, a)
            elif kind == "yesno":
                score, feedback = _grade_yesno(item, a)
            elif kind == "yesno_plus_text":
                score, feedback = _grade_yesno_plus_text(item, a)
            else:
                score, feedback = 0, "Unknown item type."
        except Exception as e:
            score, feedback = 0, f"Grading error: {e}"

        per_item.append({"id": qid, "score": int(score), "feedback": feedback})
        total_score += int(score)
        counted += 1

    overall_pct = round(total_score / (max(1, counted) * 10) * 100)
    summary = (
        "Outstanding — Lecture 3 concepts look solid."
        if overall_pct >= 90 else
        "Great progress — tighten any truth‑table cells flagged in feedback."
        if overall_pct >= 75 else
        "Keep going — revise symbolic forms and the operator rewrites (p→q, p↔q)."
        if overall_pct >= 60 else
        "Revisit the operator rules (, ` ~) and rebuild the tables row by row."
    )

    return jsonify({
        "per_item": per_item,
        "overall_pct": overall_pct,
        "pass": overall_pct >= 70,
        "summary": summary,
    })
