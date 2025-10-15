# logic_assignment.py
from __future__ import annotations

import itertools
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Tuple

from flask import Blueprint, jsonify, render_template, request

logic_assignment_bp = Blueprint("logic_assignment", __name__)

# -----------------------
# Core parsing & eval
# -----------------------

# Course operators: ',' (NOT), '`' (AND), '~' (OR)
_ALLOWED_VARS = set(list("pqroiy"))
_ALLOWED_TOKENS = set(list("pqroiy(),`~")) | {","}
# Allow common math symbols as aliases (students sometimes type these)
_ALIAS_MAP = {
    "¬": ",",  # NOT
    "∧": "`",  # AND
    "∨": "~",  # OR
}

Token = Literal["VAR", "NOT", "AND", "OR", "LPAREN", "RPAREN"]


def _normalize_expr(expr: str) -> str:
    s = (expr or "").strip()
    # Map aliases to course tokens
    for bad, good in _ALIAS_MAP.items():
        s = s.replace(bad, good)
    # Lowercase variables for consistency
    s = s.lower()
    # Remove spaces
    s = re.sub(r"\s+", "", s)
    # Quick sanity: only allowed characters
    if not s:
        return s
    if not set(s) <= _ALLOWED_TOKENS:
        # If disallowed characters appear, fail fast with a safe placeholder
        # so the grader can give constructive feedback.
        raise ValueError("Use only the course operators: , (NOT), ` (AND), ~ (OR), plus (), and variables.")
    return s


def _tokenize(s: str) -> List[Tuple[Token, str]]:
    out: List[Tuple[Token, str]] = []
    i = 0
    while i < len(s):
        c = s[i]
        if c in _ALIAS_MAP:  # Shouldn't remain after normalize, but safe-guard
            c = _ALIAS_MAP[c]
        if c in _ALLOWED_VARS:
            out.append(("VAR", c))
        elif c == ",":
            out.append(("NOT", c))
        elif c == "`":
            out.append(("AND", c))
        elif c == "~":
            out.append(("OR", c))
        elif c == "(":
            out.append(("LPAREN", c))
        elif c == ")":
            out.append(("RPAREN", c))
        else:
            raise ValueError(f"Unexpected character: {c!r}")
        i += 1
    return out


# Shunting-yard for unary NOT + binary AND/OR
_PRECEDENCE = {"OR": 1, "AND": 2, "NOT": 3}
_ASSOC = {"OR": "L", "AND": "L", "NOT": "R"}  # NOT is right-associative (prefix)


def _to_rpn(tokens: List[Tuple[Token, str]]) -> List[Tuple[Token, str]]:
    output: List[Tuple[Token, str]] = []
    ops: List[Tuple[Token, str]] = []
    prev: Optional[Token] = None
    for tok, val in tokens:
        if tok == "VAR":
            output.append((tok, val))
        elif tok == "NOT":
            ops.append((tok, val))
        elif tok in ("AND", "OR"):
            while ops and ops[-1][0] not in ("LPAREN",):
                top = ops[-1][0]
                if (_ASSOC[tok] == "L" and _PRECEDENCE[top] >= _PRECEDENCE[tok]) or (
                    _ASSOC[tok] == "R" and _PRECEDENCE[top] > _PRECEDENCE[tok]
                ):
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
            ops.pop()  # discard LPAREN
        prev = tok

    while ops:
        if ops[-1][0] in ("LPAREN", "RPAREN"):
            raise ValueError("Mismatched parentheses.")
        output.append(ops.pop())
    return output


def _eval_rpn(rpn: List[Tuple[Token, str]], env: Dict[str, bool]) -> bool:
    st: List[bool] = []
    for tok, _ in rpn:
        if tok == "VAR":
            st.append(env[_])
        elif tok == "NOT":
            if not st:
                raise ValueError("Missing operand for NOT.")
            st.append(not st.pop())
        elif tok in ("AND", "OR"):
            if len(st) < 2:
                raise ValueError("Missing operands for binary operator.")
            b = st.pop()
            a = st.pop()
            st.append((a and b) if tok == "AND" else (a or b))
    if len(st) != 1:
        raise ValueError("Malformed expression.")
    return st[0]


def eval_expr(expr: str, env: Dict[str, bool]) -> bool:
    """Evaluate a course-operator boolean expression safely."""
    s = _normalize_expr(expr)
    tokens = _tokenize(s)
    rpn = _to_rpn(tokens)
    return _eval_rpn(rpn, env)


def equivalent(expr_a: str, expr_b: str, vars_used: List[str]) -> Tuple[bool, Optional[Dict[str, bool]]]:
    """Check semantic equivalence over all truth assignments of vars_used.
    Returns (equivalent?, counterexample_env or None)."""
    for values in itertools.product([True, False], repeat=len(vars_used)):
        env = {v: val for v, val in zip(vars_used, values)}
        try:
            va = eval_expr(expr_a, env)
            vb = eval_expr(expr_b, env)
        except Exception:
            # If student's expression is malformed, not equivalent
            return False, env
        if va != vb:
            return False, env
    return True, None


# -----------------------
# Lecture 3 manifest
# -----------------------

def _tt_rows(varnames: List[str]) -> List[Dict[str, bool]]:
    """Standard truth-table order: TTT, TTF, TFT, TFF, FTT, FTF, FFT, FFF for 3 vars; analogous for 2 vars."""
    rows: List[Dict[str, bool]] = []
    for vals in itertools.product([True, False], repeat=len(varnames)):
        rows.append({v: t for v, t in zip(varnames, vals)})
    return rows


def _manifest_lecture3() -> Dict[str, Any]:
    """Return the assignment structure the frontend uses to render inputs."""
    # Helpers defining table columns that students must fill (compute)
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

    # For Q5, we *label* one column (p ↔ q) but compute it with the equivalent course-ops form.
    q5_vars = ["p", "q"]
    q5_cols = [
        {"label": "p ` q", "expr": "p ` q"},
        {"label": ",p", "expr": ",p"},
        {"label": ",q", "expr": ",q"},
        {"label": ",p ` ,q", "expr": ",p ` ,q"},
        {"label": "(p ` q) ~ (,p ` ,q)", "expr": "(p ` q) ~ (,p ` ,q)"},
        {"label": "(p ↔ q)", "expr": "(p ` q) ~ (,p ` ,q)"},  # computed via course-ops equivalence
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
    q8_cols = [
        {"label": "p ` q", "expr": "p ` q"},
        {"label": ",(p ` q)", "expr": ",(p ` q)"},
    ]

    q9_vars = ["p", "q"]
    q9_cols = [
        {"label": "p ~ q", "expr": "p ~ q"},
        {"label": ",(p ~ q)", "expr": ",(p ~ q)"},
    ]

    return {
        "assignment": "Assignment / Feladatlap — Lecture 3",
        "allowed_ops": "Use only the course operators: , (NOT), ` (AND), ~ (OR). / Csak ezeket használd: , (NEM), ` (ÉS), ~ (VAGY).",
        "items": [
            # 1) Translate to symbols
            {
                "id": "L3Q1a",
                "kind": "formula",
                "vars": ["p", "q", "r"],
                "title": "1a) Translate to symbols",
                "en": "If the rock is sandstone and contains fossils, then it formed in a shallow marine environment.",
                "hu": "Ha a kőzet homokkő és fosszíliákat tartalmaz, akkor sekély tengeri környezetben képződött.",
                "expected": ",(p ` q) ~ r",
            },
            {
                "id": "L3Q1b",
                "kind": "formula",
                "vars": ["p", "q"],
                "title": "1b) Translate to symbols",
                "en": "The rock is not sandstone, but it contains fossils.",
                "hu": "A kőzet nem homokkő, de fosszíliákat tartalmaz.",
                "expected": ",p ` q",
            },
            {
                "id": "L3Q1c",
                "kind": "formula",
                "vars": ["p", "q", "r"],
                "title": "1c) Translate to symbols",
                "en": "If it did not form in a shallow marine environment, then it is not sandstone or it does not contain fossils.",
                "hu": "Ha nem sekély tengeri környezetben képződött, akkor nem homokkő, vagy nem tartalmaz fosszíliákat.",
                "expected": ",(,r) ~ (,p ~ ,q)",
            },
            {
                "id": "L3Q1d",
                "kind": "formula",
                "vars": ["p", "q"],
                "title": "1d) Translate to symbols",
                "en": "The rock is sandstone exactly when it contains fossils.",
                "hu": "A kőzet akkor és csak akkor homokkő, ha fosszíliákat tartalmaz.",
                # Equivalence with course operators
                "expected": "(p ` q) ~ (,p ` ,q)",
            },

            # 2) Translate to English/Hungarian (light keyword checks)
            {
                "id": "L3Q2a",
                "kind": "natlang",
                "title": "2a) Translate ,p ~ q",
                "en_target": ["not sandstone", "or", "contains fossils"],
                "hu_target": ["nem homokkő", "vagy", "fossz"],
            },
            {
                "id": "L3Q2b",
                "kind": "natlang",
                "title": "2b) Translate (p ` q) → r",
                "note": "Students may phrase with 'if ... then ...' / 'ha ... akkor ...'.",
                "en_target": ["if", "sandstone", "and", "fossil", "then", "shallow"],
                "hu_target": ["ha", "homokkő", "és", "fossz", "akkor", "sekély"],
            },
            {
                "id": "L3Q2c",
                "kind": "natlang",
                "title": "2c) Translate (p ` r) ~ (,q ` r)",
                "en_target": ["either", "sandstone", "and", "shallow", "or", "not", "fossil", "and", "shallow"],
                "hu_target": ["vagy", "homokkő", "és", "sekély", "vagy", "nem", "fossz", "és", "sekély"],
            },

            # 3) Truth table — three-variable compound: (p ~ q) ` ,r
            {
                "id": "L3Q3",
                "kind": "truth_table",
                "title": "3) Truth table — (p ~ q) ` ,r",
                "vars": q3_vars,
                "rows": _tt_rows(q3_vars),
                "columns": q3_cols,  # columns to be filled (each is T/F per row)
            },

            # 4) Implication via helper column: p→q ≡ ,p ~ q
            {
                "id": "L3Q4",
                "kind": "truth_table",
                "title": "4) Implication via helper column — build p→q as ,p ~ q",
                "vars": q4_vars,
                "rows": _tt_rows(q4_vars),
                "columns": q4_cols,
            },

            # 5) Biconditional identity
            {
                "id": "L3Q5",
                "kind": "truth_table",
                "title": "5) (p ` q) ~ (,p ` ,q) is equivalent to (p ↔ q)",
                "vars": q5_vars,
                "rows": _tt_rows(q5_vars),
                "columns": q5_cols,
            },

            # 6) XOR table + one-sentence condition
            {
                "id": "L3Q6",
                "kind": "truth_table_plus_text",
                "title": "6) XOR: (p ` ,q) ~ (,p ` q)",
                "vars": q6_vars,
                "rows": _tt_rows(q6_vars),
                "columns": q6_cols,
                "text_prompt_en": "In one sentence: when is XOR true?",
                "text_prompt_hu": "Egy mondatban: mikor igaz a kizáró VAGY?",
            },

            # 7) De Morgan laws check — yes/no tautology
            {
                "id": "L3Q7a",
                "kind": "yesno",
                "title": "7a) ,(p ~ q) ↔ (,p ` ,q) — tautology?",
                "expected_yes": True,
            },
            {
                "id": "L3Q7b",
                "kind": "yesno",
                "title": "7b) ,(p ` q) ↔ (,p ~ ,q) — tautology?",
                "expected_yes": True,
            },

            # 8) NAND table + question
            {
                "id": "L3Q8",
                "kind": "truth_table_plus_yesno",
                "title": "8) NAND: ,(p ` q)",
                "vars": q8_vars,
                "rows": _tt_rows(q8_vars),
                "columns": q8_cols,
                "yesno_prompt": "Is NAND true in all cases except when both p and q are true?",
                "expected_yes": True,
            },

            # 9) NOR table + question
            {
                "id": "L3Q9",
                "kind": "truth_table_plus_text",
                "title": "9) NOR: ,(p ~ q)",
                "vars": q9_vars,
                "rows": _tt_rows(q9_vars),
                "columns": q9_cols,
                "text_prompt_en": "In which single row(s) is NOR true? (Describe rows such as 'p=F, q=F'.)",
                "text_prompt_hu": "Mely egyetlen sor(ok)ban igaz a NOR? (Pl.: 'p=F, q=F'.)",
            },

            # 10) Applied reasoning in geoscience
            {
                "id": "L3Q10a",
                "kind": "formula",
                "vars": ["o", "y", "i"],
                "title": "10a) Field rule: If (olivine or pyroxene) then igneous.",
                "en": "Use o: contains olivine, y: contains pyroxene, i: igneous.",
                "hu": "o: olivint tartalmaz, y: piroxént tartalmaz, i: magmás.",
                # implication (o ~ y) → i, expressed with course operators:
                "expected": ",(o ~ y) ~ i",
            },
            {
                "id": "L3Q10b",
                "kind": "formula_plus_text",
                "vars": ["o", "y", "i"],
                "title": "10b) Contrapositive formula and words (EN + HU)",
                "expected": ",(,i) ~ (,o ` ,y)",  # (¬i) → (¬o ∧ ¬y), via course-ops => ¬(¬i) ∨ (¬o ∧ ¬y)
                "text_keywords_en": ["if", "not igneous", "then", "no olivine", "no pyroxene"],
                "text_keywords_hu": ["ha", "nem magmás", "akkor", "nincs olivin", "nincs piroxén"],
            },
            {
                "id": "L3Q10c",
                "kind": "yesno_plus_text",
                "title": "10c) Is 'Porosity > 0.25 ` Porosity < 0.10' contradictory?",
                "expected_yes": True,
                "text_prompt_en": "Briefly explain why.",
                "text_prompt_hu": "Röviden indokold meg miért.",
            },

            # Text-Entry 1–5 (symbols only, course operators)
            {"id": "L3T1", "kind": "formula", "vars": ["p"], "title": "Text‑Entry 1 (¬p)", "expected": ",p"},
            {"id": "L3T2", "kind": "formula", "vars": ["q"], "title": "Text‑Entry 2 (¬q)", "expected": ",q"},
            {"id": "L3T3", "kind": "formula", "vars": ["p", "q"], "title": "Text‑Entry 3 (p ∧ ¬q)", "expected": "p ` ,q"},
            {"id": "L3T4", "kind": "formula", "vars": ["p", "q"], "title": "Text‑Entry 4 (¬p ∧ q)", "expected": ",p ` q"},
            {
                "id": "L3T5",
                "kind": "formula",
                "vars": ["p", "q"],
                "title": "Text‑Entry 5 (XOR as disjunction of two conjunctions)",
                "expected": "(p ` ,q) ~ (,p ` q)",
            },
        ],
    }


# -----------------------
# Grading helpers
# -----------------------

def _grade_truth_table(item: Dict[str, Any], answer: Dict[str, Any]) -> Tuple[int, str]:
    """Compare student's T/F column entries against truth computed from expressions."""
    vars_used: List[str] = item["vars"]
    rows = item["rows"]
    cols = item["columns"]  # list of {label, expr}
    # Student sends: {"cols": {"LABEL": ["T","F",...], ...}}
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

        got_col = [x.upper() for x in submitted.get(label, [])]
        # pad missing entries as blanks
        while len(got_col) < len(expected_col):
            got_col.append("")
        for i, (g, e) in enumerate(zip(got_col, expected_col)):
            if g == e:
                correct += 1
            else:
                if not first_err:
                    # Build a readable row descriptor
                    env = {v: rows[i][v] for v in vars_used}
                    env_str = ", ".join(f"{k}={'T' if v else 'F'}" for k, v in env.items())
                    first_err = f"Column “{label}”, row {i+1} ({env_str}): expected {e}."
    score = round(10 * (correct / total_cells)) if total_cells else 0
    feedback = "Great — all table cells correct." if correct == total_cells else (
        first_err or "Fill each cell with T or F."
    )
    return score, feedback


def _hits(text: str, keywords: List[str]) -> int:
    t = (text or "").lower()
    return sum(1 for k in keywords if k and k.lower() in t)


def _grade_natlang(item: Dict[str, Any], answer: Dict[str, Any]) -> Tuple[int, str]:
    en = (answer or {}).get("en", "")
    hu = (answer or {}).get("hu", "")
    en_hits = _hits(en, item.get("en_target", []))
    hu_hits = _hits(hu, item.get("hu_target", []))
    total_targets = len(item.get("en_target", [])) + len(item.get("hu_target", []))
    got = en_hits + hu_hits
    score = max(0, min(10, round(10 * got / max(1, total_targets))))
    if score == 10:
        feedback = "Nice bilingual phrasing — all key parts present."
    else:
        feedback = "Add the missing connectors/terms (e.g., if/then, és/vagy, negation)."
    return score, feedback


def _grade_yesno(item: Dict[str, Any], answer: Dict[str, Any]) -> Tuple[int, str]:
    yn = (answer or {}).get("yes", "")
    truth = str(item.get("expected_yes", False)).lower()
    correct = yn in ("true", "t", "yes", "y", "igen", "i") if item["expected_yes"] else yn in ("false", "f", "no", "n", "nem")
    return (10 if correct else 0), ("Correct." if correct else "That selection is not correct.")


def _grade_formula(item: Dict[str, Any], answer: Dict[str, Any]) -> Tuple[int, str]:
    expr = (answer or {}).get("expr", "")
    expected = item["expected"]
    vars_used: List[str] = item.get("vars", [])
    if not expr:
        return 0, "Enter a symbolic formula using only , ` ~ and parentheses."
    try:
        eq, counter = equivalent(expr, expected, vars_used)
    except ValueError as e:
        return 0, f"{e}"
    if eq:
        return 10, "Correct symbolic form."
    # Show the first counterexample
    env_str = ", ".join(f"{k}={'T' if v else 'F'}" for k, v in counter.items()) if counter else ""
    return 4, f"Not equivalent; differs for: {env_str}. Use only , (NOT), ` (AND), ~ (OR)."


def _grade_formula_plus_text(item: Dict[str, Any], answer: Dict[str, Any]) -> Tuple[int, str]:
    s1, f1 = _grade_formula(item, answer)
    en = (answer or {}).get("en", "")
    hu = (answer or {}).get("hu", "")
    en_hits = _hits(en, item.get("text_keywords_en", []))
    hu_hits = _hits(hu, item.get("text_keywords_hu", []))
    text_score = 10 if (en_hits >= 3 and hu_hits >= 3) else 6 if (en_hits >= 2 and hu_hits >= 2) else 3 if (en_hits or hu_hits) else 0
    score = round((s1 + text_score) / 2)
    feedback = ("Formula correct; wording looks good." if s1 == 10 and text_score >= 6
                else "Tighten both the formula and the wording (mention antecedent/consequent explicitly).")
    return score, feedback


def _grade_truth_table_plus_text(item: Dict[str, Any], answer: Dict[str, Any]) -> Tuple[int, str]:
    s, f = _grade_truth_table(item, answer)
    text = (answer or {}).get("text", "")
    # For XOR and NOR prompts: accept 'exactly one' / 'pontosan az egyik', or p=F q=F
    ok = any(k in (text or "").lower() for k in [
        "exactly one", "one but not both", "pontosan az egyik", "kizáró", "csak az egyik", "p=f, q=f", "p = f, q = f"
    ])
    extra = " Explanation captures the key idea." if ok else " Add the key condition in words (e.g., “exactly one is true” / “pontosan az egyik igaz”)."
    # Weight text lightly
    score = min(10, s + (2 if ok else 0))
    return score, (f + extra)


def _grade_yesno_plus_text(item: Dict[str, Any], answer: Dict[str, Any]) -> Tuple[int, str]:
    s, f = _grade_yesno(item, answer)
    txt = (answer or {}).get("text", "")
    ok = len((txt or "").strip()) >= 10
    score = min(10, s + (2 if ok else 0))
    return score, (f + (" Thanks for the brief explanation." if ok else " Add a brief one-sentence reason."))


# -----------------------
# Routes
# -----------------------

@logic_assignment_bp.route("/logic-assignment")
def logic_assignment_home():
    # Updated template renders Lecture 3 automatically
    return render_template("assignment_logic.html")


@logic_assignment_bp.route("/logic-assignment/api/generate", methods=["POST"])
def logic_assignment_generate():
    # Keep the old signature, but we only *optionally* use name/neptun now.
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    neptun = (data.get("neptun") or "").strip().upper()
    # We don't fail if name/neptun are missing; the UI can still render.
    manifest = _manifest_lecture3()
    manifest["student"] = {"name": name, "neptun": neptun}
    return jsonify(manifest)


@logic_assignment_bp.route("/logic-assignment/api/grade", methods=["POST"])
def logic_assignment_grade():
    data = request.get_json(force=True, silent=True) or {}
    answers: List[Dict[str, Any]] = data.get("answers", [])
    # Build a lookup for items by id
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
            elif kind == "natlang":
                score, feedback = _grade_natlang(item, a)
            elif kind == "truth_table_plus_text":
                score, feedback = _grade_truth_table_plus_text(item, a)
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
        "Great progress — tighten any truth-table cells flagged in feedback."
        if overall_pct >= 75 else
        "Keep going — revise the symbolic forms and operator use per feedback."
        if overall_pct >= 60 else
        "Revisit the operator rules (only , ` ~) and rebuild the truth tables row by row."
    )

    return jsonify(
        {
            "per_item": per_item,
            "overall_pct": overall_pct,
            "pass": overall_pct >= 70,
            "summary": summary,
        }
    )
