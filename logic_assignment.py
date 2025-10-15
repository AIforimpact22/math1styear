# logic_assignment.py
from __future__ import annotations

import itertools
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Tuple

from flask import Blueprint, jsonify, render_template, request

# =========================
# Blueprint
# =========================
logic_assignment_bp = Blueprint("logic_assignment", __name__)

# =========================
# OpenAI client (uses env OPENAI_API_KEY)
# =========================
try:
    from openai import OpenAI  # openai>=1.0
    _openai_client = OpenAI()  # will read OPENAI_API_KEY from environment
    _OPENAI_OK = True
except Exception:
    _openai_client = None
    _OPENAI_OK = False

_GRADING_MODEL = os.getenv("GRADING_MODEL", "gpt-4o-mini")

# =========================
# Course operators parser (, ` ~)
# =========================
_ALLOWED_VARS = set(list("pqroiy"))
_ALLOWED_TOKENS = set(list("pqroiy(),`~")) | {","}
_ALIAS_MAP = {"¬": ",", "∧": "`", "∨": "~"}

Token = Literal["VAR", "NOT", "AND", "OR", "LPAREN", "RPAREN"]


def _normalize_expr(expr: str) -> str:
    s = (expr or "").strip()
    for bad, good in _ALIAS_MAP.items():
        s = s.replace(bad, good)
    s = re.sub(r"\s+", "", s.lower())
    if not s:
        return s
    if not set(s) <= _ALLOWED_TOKENS:
        raise ValueError("Use only: , (NOT), ` (AND), ~ (OR), variables, and parentheses.")
    return s


def _tokenize(s: str) -> List[Tuple[Token, str]]:
    out: List[Tuple[Token, str]] = []
    for c in s:
        if c in _ALIAS_MAP:  # defense-in-depth
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
    return out


_PRECEDENCE = {"OR": 1, "AND": 2, "NOT": 3}
_ASSOC = {"OR": "L", "AND": "L", "NOT": "R"}


def _to_rpn(tokens: List[Tuple[Token, str]]) -> List[Tuple[Token, str]]:
    output: List[Tuple[Token, str]] = []
    ops: List[Tuple[Token, str]] = []
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
            ops.pop()
    while ops:
        if ops[-1][0] in ("LPAREN", "RPAREN"):
            raise ValueError("Mismatched parentheses.")
        output.append(ops.pop())
    return output


def _eval_rpn(rpn: List[Tuple[Token, str]], env: Dict[str, bool]) -> bool:
    st: List[bool] = []
    for tok, val in rpn:
        if tok == "VAR":
            st.append(env[val])
        elif tok == "NOT":
            if not st:
                raise ValueError("Missing operand for NOT.")
            st.append(not st.pop())
        elif tok in ("AND", "OR"):
            if len(st) < 2:
                raise ValueError("Missing operands for binary operator.")
            b = st.pop()
            a = st.pop()
            st.append(a and b if tok == "AND" else a or b)
    if len(st) != 1:
        raise ValueError("Malformed expression.")
    return st[0]


def eval_expr(expr: str, env: Dict[str, bool]) -> bool:
    s = _normalize_expr(expr)
    rpn = _to_rpn(_tokenize(s))
    return _eval_rpn(rpn, env)


def equivalent(expr_a: str, expr_b: str, vars_used: List[str]) -> Tuple[bool, Optional[Dict[str, bool]]]:
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


def _tt_rows(varnames: List[str]) -> List[Dict[str, bool]]:
    return [{v: val for v, val in zip(varnames, vals)} for vals in itertools.product([True, False], repeat=len(varnames))]

# =========================
# Manifest (Lecture 3) — WITH Q2 REMOVED; no explanation fields
# =========================
def _manifest_lecture3() -> Dict[str, Any]:
    q3_vars = ["p", "q", "r"]
    q3_cols = [
        {"label": "p ~ q", "expr": "p ~ q"},
        {"label": ",r", "expr": ",r"},
        {"label": "(p ~ q) ` ,r", "expr": "(p ~ q) ` ,r"},
    ]
    q4_vars = ["p", "q"]
    q4_cols = [{"label": ",p", "expr": ",p"}, {"label": ",p ~ q", "expr": ",p ~ q"}]
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
        "allowed_ops": "Use only the course operators: , (NOT), ` (AND), ~ (OR). / Csak ezeket: , (NEM), ` (ÉS), ~ (VAGY).",
        "items": [
            # 1) Translate to symbols (formulas only)
            {"id": "L3Q1a", "kind": "formula", "vars": ["p", "q", "r"],
             "title": "1a) If sandstone and fossils, then shallow marine.",
             "expected": ",(p ` q) ~ r"},
            {"id": "L3Q1b", "kind": "formula", "vars": ["p", "q"],
             "title": "1b) Not sandstone, but fossils.",
             "expected": ",p ` q"},
            {"id": "L3Q1c", "kind": "formula", "vars": ["p", "q", "r"],
             "title": "1c) If not shallow, then not sandstone or not fossils.",
             "expected": ",(,r) ~ (,p ~ ,q)"},
            {"id": "L3Q1d", "kind": "formula", "vars": ["p", "q"],
             "title": "1d) Sandstone exactly when fossils.",
             "expected": "(p ` q) ~ (,p ` ,q)"},

            # 3) Truth table — three variables
            {"id": "L3Q3", "kind": "truth_table", "title": "3) (p ~ q) ` ,r",
             "vars": q3_vars, "rows": _tt_rows(q3_vars), "columns": q3_cols},

            # 4) Implication via helper column
            {"id": "L3Q4", "kind": "truth_table", "title": "4) p→q as ,p ~ q",
             "vars": q4_vars, "rows": _tt_rows(q4_vars), "columns": q4_cols},

            # 5) Biconditional identity
            {"id": "L3Q5", "kind": "truth_table", "title": "5) (p ` q) ~ (,p ` ,q) ≡ (p ↔ q)",
             "vars": q5_vars, "rows": _tt_rows(q5_vars), "columns": q5_cols},

            # 6) XOR + one-sentence (kept)
            {"id": "L3Q6", "kind": "truth_table_plus_text", "title": "6) XOR: (p ` ,q) ~ (,p ` q)",
             "vars": q6_vars, "rows": _tt_rows(q6_vars), "columns": q6_cols,
             "text_prompt_en": "In one sentence: when is XOR true?"},

            # 7) De Morgan tautologies (yes/no)
            {"id": "L3Q7a", "kind": "yesno", "title": "7a) ,(p ~ q) ↔ (,p ` ,q) — tautology?", "expected_yes": True},
            {"id": "L3Q7b", "kind": "yesno", "title": "7b) ,(p ` q) ↔ (,p ~ ,q) — tautology?", "expected_yes": True},

            # 8) NAND (table + yes/no)
            {"id": "L3Q8", "kind": "truth_table_plus_yesno", "title": "8) NAND: ,(p ` q)",
             "vars": q8_vars, "rows": _tt_rows(q8_vars), "columns": q8_cols,
             "yesno_prompt": "Is NAND true in all cases except when both p and q are true?",
             "expected_yes": True},

            # 9) NOR (table + text)
            {"id": "L3Q9", "kind": "truth_table_plus_text", "title": "9) NOR: ,(p ~ q)",
             "vars": q9_vars, "rows": _tt_rows(q9_vars), "columns": q9_cols,
             "text_prompt_en": "In which single row(s) is NOR true? (e.g., p=F, q=F)"},

            # 10) Applied geoscience (formulas only)
            {"id": "L3Q10a", "kind": "formula", "vars": ["o", "y", "i"],
             "title": "10a) If (olivine or pyroxene) then igneous.", "expected": ",(o ~ y) ~ i"},
            # (Removed the bilingual explanation fields)
            {"id": "L3Q10b", "kind": "formula", "vars": ["o", "y", "i"],
             "title": "10b) Contrapositive (formula only).", "expected": ",(,i) ~ (,o ` ,y)"},
            {"id": "L3Q10c", "kind": "yesno_plus_text",
             "title": "10c) Is 'Porosity > 0.25 ` Porosity < 0.10' contradictory?", "expected_yes": True},

            # Text entries (formulas only)
            {"id": "L3T1", "kind": "formula", "vars": ["p"], "title": "Text‑Entry 1 (¬p)", "expected": ",p"},
            {"id": "L3T2", "kind": "formula", "vars": ["q"], "title": "Text‑Entry 2 (¬q)", "expected": ",q"},
            {"id": "L3T3", "kind": "formula", "vars": ["p", "q"], "title": "Text‑Entry 3 (p ∧ ¬q)", "expected": "p ` ,q"},
            {"id": "L3T4", "kind": "formula", "vars": ["p", "q"], "title": "Text‑Entry 4 (¬p ∧ q)", "expected": ",p ` q"},
            {"id": "L3T5", "kind": "formula", "vars": ["p", "q"], "title": "Text‑Entry 5 (XOR disjunction)",
             "expected": "(p ` ,q) ~ (,p ` q)"},
        ],
    }

# =========================
# Helpers to prepare GPT grading inputs
# =========================
def _compute_truth_table_columns(item: Dict[str, Any]) -> Dict[str, List[str]]:
    cols_truth: Dict[str, List[str]] = {}
    for col in item.get("columns", []):
        label, expr = col["label"], col["expr"]
        vals: List[str] = []
        for r in item.get("rows", []):
            env = {v: bool(r[v]) for v in item["vars"]}
            vals.append("T" if eval_expr(expr, env) else "F")
        cols_truth[label] = vals
    return cols_truth


def _build_helper_eval(manifest: Dict[str, Any], answers: List[Dict[str, Any]]) -> Dict[str, Any]:
    ans_by_id = {a.get("id"): a for a in answers}
    helpers: Dict[str, Any] = {}
    for it in manifest["items"]:
        qid = it["id"]
        kind = it["kind"]
        helpers[qid] = {"kind": kind}

        if kind in ("truth_table", "truth_table_plus_text", "truth_table_plus_yesno"):
            expected_cols = _compute_truth_table_columns(it)
            submitted = (ans_by_id.get(qid) or {}).get("cols", {})
            # align lengths
            diff: Dict[str, List[bool]] = {}
            for label, exp_col in expected_cols.items():
                got = [str(x).upper() for x in submitted.get(label, [])]
                got += [""] * (len(exp_col) - len(got))
                diff[label] = [g == e for g, e in zip(got, exp_col)]
            helpers[qid]["expected_cols"] = expected_cols
            helpers[qid]["correct_cells"] = diff

        elif kind in ("formula",):
            expected = it.get("expected", "")
            expr = (ans_by_id.get(qid) or {}).get("expr", "")
            vars_used = it.get("vars", [])
            try:
                eq, counter = equivalent(expr, expected, vars_used)
            except Exception:
                eq, counter = False, None
            helpers[qid]["expected"] = expected
            helpers[qid]["student_expr"] = expr
            helpers[qid]["equivalent"] = eq
            helpers[qid]["counterexample"] = counter

        elif kind == "yesno":
            expected_yes = bool(it.get("expected_yes"))
            user_yes = (ans_by_id.get(qid) or {}).get("yes", "")
            helpers[qid]["expected_yes"] = expected_yes
            helpers[qid]["user_yes"] = str(user_yes)

        elif kind == "yesno_plus_text":
            expected_yes = bool(it.get("expected_yes"))
            user_yes = (ans_by_id.get(qid) or {}).get("yes", "")
            helpers[qid]["expected_yes"] = expected_yes
            helpers[qid]["user_yes"] = str(user_yes)
            helpers[qid]["text_len"] = len(((ans_by_id.get(qid) or {}).get("text") or "").strip())

    return helpers

# =========================
# Routes
# =========================
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
    """Grades via GPT using your OPENAI_API_KEY (Render env)."""
    if not _OPENAI_OK:
        return jsonify({"error": "OpenAI client not available. Ensure openai>=1.0 is installed and OPENAI_API_KEY is set."}), 500

    payload = request.get_json(force=True, silent=True) or {}
    answers: List[Dict[str, Any]] = payload.get("answers", [])

    manifest = _manifest_lecture3()
    helpers = _build_helper_eval(manifest, answers)

    # Build a strict JSON output spec (lightweight) via JSON mode.
    system_msg = (
        "You are a precise autograder for a logic course using custom operators: ',' (NOT), '`' (AND), '~' (OR). "
        "Grade each item from 0–10 with short, actionable feedback. "
        "Use the provided helper_evaluations as ground truth for correctness (e.g., equivalence checks and truth-table cell matches). "
        "Return STRICT JSON with keys: per_item (list of {id, score, feedback}), overall_pct (int), pass (bool), summary (string). "
        "Do not include any extra keys or text."
    )

    rubric = {
        "formula": "If helper.equivalent is True → score 10; otherwise 4–6 if close (minor operator/paren slip), else 0–3. Feedback: name the fix.",
        "truth_table": "Score proportional to correct cells (round to nearest int on a 0–10 scale). Feedback: cite first wrong column/row.",
        "truth_table_plus_text": "Same as truth_table plus up to +2 if the text succinctly captures the concept (e.g., XOR = exactly one true). Cap at 10.",
        "yesno": "10 if matches expected, else 0.",
        "yesno_plus_text": "8 if yes/no correct, +0–2 for a brief reason (>=10 chars). Cap at 10."
    }

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": json.dumps({
            "rubric": rubric,
            "manifest_items": [{k: v for k, v in it.items() if k not in ("rows",)} for it in manifest["items"]],
            "answers": answers,
            "helper_evaluations": helpers
        }, ensure_ascii=False)}
    ]

    try:
        resp = _openai_client.chat.completions.create(
            model=_GRADING_MODEL,
            response_format={"type": "json_object"},
            messages=messages,
            temperature=0
        )
        raw = resp.choices[0].message.content or "{}"
        result = json.loads(raw)
    except Exception as e:
        return jsonify({"error": f"Autograder failed: {e}"}), 500

    # Minimal sanity
    per_item = result.get("per_item", [])
    overall_pct = int(result.get("overall_pct", 0))
    passed = bool(result.get("pass", overall_pct >= 70))
    summary = result.get("summary", "Autograde complete.")

    return jsonify(
        {
            "per_item": per_item,
            "overall_pct": overall_pct,
            "pass": passed,
            "summary": summary,
        }
    )
