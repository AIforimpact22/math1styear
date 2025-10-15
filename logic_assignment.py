# logic_assignment.py
from __future__ import annotations

import itertools
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from flask import Blueprint, jsonify, render_template, request

# --- OpenAI SDK (uses OPENAI_API_KEY from environment) ---
# Docs (current SDK): https://platform.openai.com/docs/api-reference/chat/create
# Install: pip install openai
try:
    from openai import OpenAI  # SDK v1.x
    _openai_available = True
except Exception:  # pragma: no cover
    OpenAI = None
    _openai_available = False

logic_assignment_bp = Blueprint("logic_assignment", __name__)

# ------------- Logic helpers (course operators: ,  `  ~) -------------

Token = str  # "VAR" | "NOT" | "AND" | "OR" | "LPAREN" | "RPAREN"

_ALLOWED_VARS = set(list("pqroiy"))
_ALIAS_MAP = {"¬": ",", "∧": "`", "∨": "~"}  # tolerate common math symbols
_PRECEDENCE = {"OR": 1, "AND": 2, "NOT": 3}
_ASSOC = {"OR": "L", "AND": "L", "NOT": "R"}


def _normalize_expr(expr: str) -> str:
    s = (expr or "").strip().lower()
    for bad, good in _ALIAS_MAP.items():
        s = s.replace(bad, good)
    return "".join(c for c in s if not c.isspace())


def _tokenize(s: str) -> List[Tuple[Token, str]]:
    out: List[Tuple[Token, str]] = []
    for c in s:
        if c in _ALIAS_MAP:  # should not happen after normalize, but safe-guard
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
            # ignore unknown characters so GPT-equivalent answers with prose still pass sanity
            pass
    return out


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
            if ops and ops[-1][0] == "LPAREN":
                ops.pop()
    while ops:
        output.append(ops.pop())
    return output


def _eval_rpn(rpn: List[Tuple[Token, str]], env: Dict[str, bool]) -> bool:
    st: List[bool] = []
    for tok, val in rpn:
        if tok == "VAR":
            st.append(bool(env.get(val, False)))
        elif tok == "NOT":
            st.append(not st.pop())
        elif tok in ("AND", "OR"):
            b = st.pop(); a = st.pop()
            st.append((a and b) if tok == "AND" else (a or b))
    return st[-1] if st else False


def eval_expr(expr: str, env: Dict[str, bool]) -> bool:
    s = _normalize_expr(expr)
    rpn = _to_rpn(_tokenize(s))
    return _eval_rpn(rpn, env)


def _tt_rows(varnames: List[str]) -> List[Dict[str, bool]]:
    return [{v: val for v, val in zip(varnames, vals)}
            for vals in itertools.product([True, False], repeat=len(varnames))]

# ------------- Manifest (Lecture 3) -------------

@dataclass(frozen=True)
class Item:
    id: str
    title: str
    en: str
    hu: str


def _lecture3_items() -> List[Item]:
    # NOTE: 2a/2b/2c REMOVED per request.
    items: List[Item] = [
        Item("L3Q1a", "1a) Translate to symbols",
             "If the rock is sandstone and contains fossils, then it formed in a shallow marine environment.",
             "Ha a kőzet homokkő és fosszíliákat tartalmaz, akkor sekély tengeri környezetben képződött."),
        Item("L3Q1b", "1b) Translate to symbols",
             "The rock is not sandstone, but it contains fossils.",
             "A kőzet nem homokkő, de fosszíliákat tartalmaz."),
        Item("L3Q1c", "1c) Translate to symbols",
             "If it did not form in a shallow marine environment, then it is not sandstone or it does not contain fossils.",
             "Ha nem sekély tengeri környezetben képződött, akkor nem homokkő, vagy nem tartalmaz fosszíliákat."),
        Item("L3Q1d", "1d) Translate to symbols",
             "The rock is sandstone exactly when it contains fossils.",
             "A kőzet akkor és csak akkor homokkő, ha fosszíliákat tartalmaz."),

        # 3) Truth table three-variable compound
        Item("L3Q3", "3) Truth table — (p ~ q) ` ,r",
             "Provide the full truth table or a clear description for (p ~ q) ` ,r.",
             "Add meg az (p ~ q) ` ,r teljes igazságtábláját vagy egyértelmű leírását."),

        # 4) Implication via helper equivalence
        Item("L3Q4", "4) Use p→q ≡ ,p ~ q",
             "Build the table or describe when p→q is true using the equivalence ,p ~ q.",
             "Állítsd fel a táblát vagy írd le, mikor igaz a p→q a ,p ~ q egyenértékűség alapján."),

        # 5) Biconditional identity
        Item("L3Q5", "5) (p ` q) ~ (,p ` ,q) ≡ (p ↔ q)",
             "Show (by table or reasoning) that (p ` q) ~ (,p ` ,q) is equivalent to (p ↔ q).",
             "Mutasd meg (táblával vagy érveléssel), hogy (p ` q) ~ (,p ` ,q) ekvivalens a (p ↔ q)-val."),

        # 6) XOR
        Item("L3Q6", "6) XOR",
             "Give the table for (p ` ,q) ~ (,p ` q) and one sentence: when is XOR true?",
             "Add meg a (p ` ,q) ~ (,p ` q) táblát és egy mondatban: mikor igaz a kizáró VAGY?"),

        # 7) De Morgan laws check
        Item("L3Q7a", "7a) De Morgan",
             "Is ,(p ~ q) ↔ (,p ` ,q) a tautology? Justify briefly.",
             "Tautológia‑e a ,(p ~ q) ↔ (,p ` ,q)? Indokold röviden."),
        Item("L3Q7b", "7b) De Morgan",
             "Is ,(p ` q) ↔ (,p ~ ,q) a tautology? Justify briefly.",
             "Tautológia‑e a ,(p ` q) ↔ (,p ~ ,q)? Indokold röviden."),

        # 8) NAND
        Item("L3Q8", "8) NAND",
             "Complete/describe ,(p ` q). Is it true in all cases except p=T and q=T?",
             "Egészítsd ki/írd le a ,(p ` q) táblát. Igaz‑e minden esetben, kivéve p=T és q=T?"),

        # 9) NOR
        Item("L3Q9", "9) NOR",
             "Complete/describe ,(p ~ q). In which row(s) is NOR true?",
             "Egészítsd ki/írd le a ,(p ~ q) táblát. Mely sor(ok)ban igaz a NOR?"),

        # 10) Applied reasoning
        Item("L3Q10a", "10a) Field rule",
             "If (olivine or pyroxene) then igneous. Use o, y, i.",
             "Ha (olivin vagy piroxén), akkor magmás. Használd az o, y, i jeleket."),
        Item("L3Q10b", "10b) Contrapositive",
             "Write the contrapositive in symbols and words (EN or HU).",
             "Írd le a kontrapozíciót szimbólumokkal és szöveggel (EN vagy HU)."),
        Item("L3Q10c", "10c) Contradiction check",
             "Is “Porosity > 0.25 ` Porosity < 0.10” contradictory? Explain briefly.",
             "Ellentmondás‑e a „Porozitás > 0.25 ` Porozitás < 0.10”? Röviden indokold."),

        # Text entries (symbols only allowed but students may answer in words; GPT will judge)
        Item("L3T1", "Text‑Entry 1 (¬p)", "Symbolic form of “The rock is not sandstone.”", "Szimbólumok: „A kőzet nem homokkő.”"),
        Item("L3T2", "Text‑Entry 2 (¬q)", "Symbolic form of “The sample does not contain fossils.”", "Szimbólumok: „A minta nem tartalmaz fosszíliákat.”"),
        Item("L3T3", "Text‑Entry 3 (p ∧ ¬q)", "Symbolic form of “Sandstone and no fossils.”", "Szimbólumok: „Homokkő és nincsenek fosszíliák.”"),
        Item("L3T4", "Text‑Entry 4 (¬p ∧ q)", "Symbolic form of “Not sandstone and fossils.”", "Szimbólumok: „Nem homokkő és fosszíliák vannak.”"),
        Item("L3T5", "Text‑Entry 5 (XOR as OR of two ANDs)",
             "Symbolic form of “(p ∧ ¬q) OR (¬p ∧ q)”.",
             "Szimbólumok: „(p ∧ ¬q) VAGY (¬p ∧ q)”"),
    ]
    return items


# Build expected key for GPT rubric (we compute truth-table references server-side)
def _expected_key() -> Dict[str, Any]:
    # compact notation reminders for the model
    expected: Dict[str, Any] = {
        "L3Q1a": ",(p ` q) ~ r",
        "L3Q1b": ",p ` q",
        "L3Q1c": ",(,r) ~ (,p ~ ,q)",
        "L3Q1d": "(p ` q) ~ (,p ` ,q)",  # biconditional
        "L3Q10a": ",(o ~ y) ~ i",
        "L3Q10b": ",(,i) ~ (,o ` ,y)",  # (¬i) → (¬o ∧ ¬y) expressed with course ops
        "L3T1": ",p",
        "L3T2": ",q",
        "L3T3": "p ` ,q",
        "L3T4": ",p ` q",
        "L3T5": "(p ` ,q) ~ (,p ` q)"
    }

    # tables: compute server-side correct rows so GPT can compare reliably
    def rows_for(vars_: List[str], exprs: Dict[str, str]) -> List[Dict[str, Any]]:
        rows = _tt_rows(vars_)
        out: List[Dict[str, Any]] = []
        for r in rows:
            entry = {"env": {k: ("T" if v else "F") for k, v in r.items()}}
            for label, e in exprs.items():
                entry[label] = "T" if eval_expr(e, r) else "F"
            out.append(entry)
        return out

    # Q3: (p ~ q) ` ,r
    expected["L3Q3"] = rows_for(["p", "q", "r"], {"(p ~ q) ` ,r": "(p ~ q) ` ,r"})

    # Q4: p→q ≡ ,p ~ q (also include helper ,p)
    expected["L3Q4"] = rows_for(["p", "q"], {",p": ",p", ",p ~ q": ",p ~ q"})

    # Q5: show equivalence (p ` q) ~ (,p ` ,q) == (p ↔ q)
    # We'll provide the truth column of each part so GPT can verify
    expected["L3Q5"] = rows_for(
        ["p", "q"],
        {"(p ` q) ~ (,p ` ,q)": "(p ` q) ~ (,p ` ,q)", "(p↔q)": "(p ` q) ~ (,p ` ,q)"}
    )

    # Q6: XOR
    expected["L3Q6"] = rows_for(
        ["p", "q"],
        {"(p ` ,q) ~ (,p ` q)": "(p ` ,q) ~ (,p ` q)"}
    )

    # Q8: NAND
    expected["L3Q8"] = rows_for(["p", "q"], {",(p ` q)": ",(p ` q)"})

    # Q9: NOR
    expected["L3Q9"] = rows_for(["p", "q"], {",(p ~ q)": ",(p ~ q)"})

    # Q7a/b: both tautologies
    expected["L3Q7a"] = "tautology"
    expected["L3Q7b"] = "tautology"

    # Q10c contradiction
    expected["L3Q10c"] = "contradiction"

    return expected


# ---------------- Routes ----------------

@logic_assignment_bp.route("/logic-assignment")
def logic_assignment_home():
    return render_template("assignment_logic.html")


@logic_assignment_bp.route("/logic-assignment/api/generate", methods=["POST"])
def logic_assignment_generate():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    neptun = (data.get("neptun") or "").strip()
    items = _lecture3_items()
    return jsonify({
        "assignment": "Assignment / Feladatlap — Lecture 3",
        "allowed_ops": "Use only: , (NOT), ` (AND), ~ (OR). / Csak ezeket: , (NEM), ` (ÉS), ~ (VAGY).",
        "student": {"name": name, "neptun": neptun},
        "items": [{"id": it.id, "title": it.title, "en": it.en, "hu": it.hu} for it in items]
    })


@logic_assignment_bp.route("/logic-assignment/api/grade", methods=["POST"])
def logic_assignment_grade():
    """Send answers to OpenAI for grading; return per-item scores and overall."""
    if not _openai_available:
        return jsonify({"error": "OpenAI SDK not installed on server"}), 500

    data = request.get_json(force=True, silent=True) or {}
    answers: List[Dict[str, Any]] = data.get("answers", [])
    # Normalize to {id, text}
    filtered = [{"id": a.get("id"), "text": (a.get("text") or "").strip()} for a in answers if a.get("id")]

    items = _lecture3_items()
    spec = _expected_key()
    item_map = {it.id: {"title": it.title, "en": it.en, "hu": it.hu} for it in items}

    # Compose grading prompt
    sys_msg = (
        "You are an auto-grader for a logic assignment (Lecture 3) using custom operators: "
        "comma (,) = NOT, backtick (`) = AND, tilde (~) = OR. "
        "Students answer in ENGLISH or HUNGARIAN; grade either language. "
        "Score each item from 0 to 10 (int). Give short, clear feedback in BOTH languages "
        "(feedback_en, feedback_hu). Accept equivalent symbolic forms and clear natural-language "
        "explanations. Truth tables may be provided as rows (e.g., 'p=T q=F r=T => F') or prose."
    )

    rubric = (
        "Rubric:\n"
        "10 = completely correct (symbols/truth or explanation),\n"
        "8 = minor notation or formatting issues but logically correct,\n"
        "6 = partially correct (about half),\n"
        "3 = minimal attempt with some relevant idea,\n"
        "0 = irrelevant or empty.\n"
        "Be tolerant to accents and synonyms (EN/HU)."
    )

    # Provide expected reference (computed tables etc.) so GPT can compare reliably.
    expected_blob = spec  # compact but explicit

    user_payload = {
        "items": item_map,
        "answers": filtered,
        "expected": expected_blob,
        "instructions": rubric,
        "output_contract": {
            "type": "object",
            "properties": {
                "per_item": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "score": {"type": "integer"},
                            "feedback_en": {"type": "string"},
                            "feedback_hu": {"type": "string"}
                        },
                        "required": ["id", "score", "feedback_en", "feedback_hu"]
                    }
                },
                "overall_pct": {"type": "integer"},
                "summary_en": {"type": "string"},
                "summary_hu": {"type": "string"}
            },
            "required": ["per_item", "overall_pct", "summary_en", "summary_hu"]
        }
    }

    # Call OpenAI (Chat Completions with JSON output)
    client = OpenAI()
    try:
        completion = client.chat.completions.create(
            model=os.environ.get("OPENAI_GPT_MODEL", "gpt-4o-mini"),
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)}
            ],
            temperature=0.2,
        )
        content = completion.choices[0].message.content or "{}"
        graded = json.loads(content)
    except Exception as e:
        return jsonify({"error": f"OpenAI grading failed: {e}"}), 502

    # Safety nets
    per_item = graded.get("per_item", [])
    total_score = sum(int(row.get("score", 0)) for row in per_item)
    counted = max(1, len(item_map))
    overall_pct = graded.get("overall_pct")
    if not isinstance(overall_pct, int):
        overall_pct = round(total_score / (counted * 10) * 100)

    return jsonify({
        "per_item": per_item,
        "overall_pct": overall_pct,
        "pass": overall_pct >= 70,
        "summary": {
            "en": graded.get("summary_en", ""),
            "hu": graded.get("summary_hu", "")
        }
    })
