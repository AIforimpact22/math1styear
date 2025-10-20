# logic_playground.py — Bilingual geology logic playground (symbols ⇄ sentences)
# Drop-in Flask blueprint with GPT-powered conversions and robust offline fallbacks.
#
# Requires: Flask; optional OpenAI SDK (pip install openai). If OPENAI_API_KEY is not set,
#            the endpoints still work with rule-based fallbacks.
#
# Endpoints:
#   GET  /logic-playground                     -> HTML UI (use render_template or serve the provided .html file)
#   POST /logic-playground/api/explain         -> {"expr": str, "lang": "en"|"hu", "vars": {...}} -> NL gloss
#   POST /logic-playground/api/parse           -> {"text": str, "lang": "en"|"hu", "vars": {...}} -> {"expr": str}
#   POST /logic-playground/api/truth-table     -> {"expr": str, "vars": ["p","q",...]} -> rows of T/F
#   GET  /logic-playground/api/examples        -> starter examples (EN/HU)
#
# Notes:
# - Variables allowed: p,q,r,o,i,y (same as assignment).
# - Operators: ASCII ',', '`', '~' and unicode ¬ ∧ ∨ → ↔; also ASCII -> and <-> normalized.
# - The parser/normalizer mirrors your assignment autograder for consistency.
# - NL↔symbols uses GPT when available; otherwise uses compact rule-based heuristics.
#
from __future__ import annotations

import itertools
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from flask import Blueprint, jsonify, render_template, request

# ---------- Optional OpenAI (Responses API) ----------
try:
    from openai import OpenAI  # pip install openai
    _OPENAI_CLIENT: Optional[OpenAI] = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
except Exception:
    _OPENAI_CLIENT = None  # graceful fallback when SDK/env not available

logic_playground_bp = Blueprint("logic_playground", __name__)

# ======================================================
# Core logic parsing/evaluation (mirrors assignment)
# ======================================================

_ALLOWED_VARS = set(list("pqroiy"))
_ALLOWED_TOKENS = set(list("pqroiy(),`~¬∧∨→↔"))
_ALIAS_MAP = {"¬": ",", "∧": "`", "∨": "~"}  # normalize to ASCII commas/backtick/tilde
_PRECEDENCE = {"IFF": 1, "IMP": 2, "OR": 3, "AND": 4, "NOT": 5}
_ASSOC = {"IFF": "R", "IMP": "R", "OR": "L", "AND": "L", "NOT": "R"}

Token = str  # one of: VAR, NOT, AND, OR, IMP, IFF, LPAREN, RPAREN

def _normalize_expr(expr: str) -> str:
    s = (expr or "").strip()
    if not s:
        return s
    s = s.replace("<->", "↔").replace("->", "→")
    s = re.sub(r"\s+", "", s).lower()
    for bad, good in _ALIAS_MAP.items():
        s = s.replace(bad, good)
    if not set(s) <= _ALLOWED_TOKENS:
        raise ValueError("Use only the on‑screen symbols or these: , (NOT), ` (AND), ~ (OR), parentheses, variables (p,q,r,o,i,y). Implication (→) and equivalence (↔) are also accepted.")
    return s

def _tokenize(s: str) -> List[Tuple[Token, str]]:
    out: List[Tuple[Token, str]] = []
    for c in s:
        if c in _ALIAS_MAP:
            c = _ALIAS_MAP[c]
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

def _to_rpn(tokens: List[Tuple[Token, str]]) -> List[Tuple[Token, str]]:
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
                st.append((a and b) or ((not a) and (not b)))
    if len(st) != 1:
        raise ValueError("Malformed expression.")
    return st[0]

def eval_expr(expr: str, env: Dict[str, bool]) -> bool:
    s = _normalize_expr(expr)
    tokens = _tokenize(s)
    rpn = _to_rpn(tokens)
    return _eval_rpn(rpn, env)

# ---------- AST builder (from RPN) for readable phrasing ----------
class Node:
    __slots__ = ("op","val","left","right")
    def __init__(self, op:str, val:str="", left:'Node|None'=None, right:'Node|None'=None):
        self.op=op; self.val=val; self.left=left; self.right=right

def _rpn_to_ast(rpn: List[Tuple[Token,str]]) -> Node:
    st: List[Node] = []
    for tok, sym in rpn:
        if tok == "VAR":
            st.append(Node("VAR", sym))
        elif tok == "NOT":
            if not st: raise ValueError("Missing operand for NOT.")
            st.append(Node("NOT", left=st.pop()))
        else:  # binary
            if len(st) < 2: raise ValueError("Missing operands for binary operator.")
            b=st.pop(); a=st.pop()
            st.append(Node(tok, left=a, right=b))
    if len(st)!=1: raise ValueError("Malformed expression.")
    return st[0]

def _expr_to_ast(expr:str) -> Node:
    tokens = _tokenize(_normalize_expr(expr))
    return _rpn_to_ast(_to_rpn(tokens))

# ======================================================
# Defaults and bilingual strings
# ======================================================
DEFAULT_VARS_EN = {
    "p": "the rock is sandstone",
    "q": "it contains fossils",
    "r": "it formed in a shallow marine environment",
    "o": "the sample contains olivine",
    "y": "the sample contains pyroxene",
    "i": "the rock is igneous",
}
DEFAULT_VARS_HU = {
    "p": "a kőzet homokkő",
    "q": "fossziliákat tartalmaz",
    "r": "sekély tengeri környezetben képződött",
    "o": "a minta olivint tartalmaz",
    "y": "a minta piroxént tartalmaz",
    "i": "a kőzet magmás",
}

CONN_EN = {
    "NOT": "not {x}",
    "AND": "{a} and {b}",
    "OR" : "{a} or {b}",
    "IMP": "if {a}, then {b}",
    "IFF": "{a} if and only if {b}",
}
CONN_HU = {
    "NOT": "nem {x}",
    "AND": "{a} és {b}",
    "OR" : "{a} vagy {b}",
    "IMP": "ha {a}, akkor {b}",
    "IFF": "{a} akkor és csak akkor, ha {b}",
}

def _pick_lang_dict(lang:str):
    return (DEFAULT_VARS_EN, CONN_EN) if lang=="en" else (DEFAULT_VARS_HU, CONN_HU)

# ======================================================
# Phrasing (rule-based) with light parentheses for clarity
# ======================================================
def _prec(op:str)->int:
    return {"IFF":1,"IMP":2,"OR":3,"AND":4,"NOT":5,"VAR":6}.get(op,0)

def _phrase(node:Node, var_defs:Dict[str,str], lang:str, parent_op:str="", side:str="")->str:
    if node.op=="VAR":
        return var_defs.get(node.val, node.val)
    if node.op=="NOT":
        x=_phrase(node.left, var_defs, lang, "NOT","")
        s=(CONN_EN if lang=="en" else CONN_HU)["NOT"].format(x=x)
        # add parens if child is not VAR
        if node.left.op!="VAR":
            s = "(" + s + ")"
        return s
    left=None; right=None
    if node.left:  left=_phrase(node.left, var_defs, lang, node.op, "L")
    if node.right: right=_phrase(node.right, var_defs, lang, node.op, "R")
    conn=(CONN_EN if lang=="en" else CONN_HU)
    text=conn[node.op].format(a=left,b=right)
    # parentheses if child precedence lower than parent (for clarity on nested)
    def maybe_paren(ch:Node, frag:str)->str:
        if ch.op=="VAR": return frag
        if _prec(ch.op) < _prec(node.op):  # child binds weaker
            return "(" + frag + ")"
        return frag
    if node.left:  left = maybe_paren(node.left, left)
    if node.right: right = maybe_paren(node.right, right)
    text=conn[node.op].format(a=left,b=right)
    return text

def explain_expr(expr:str, lang:str="en", var_defs:Optional[Dict[str,str]]=None)->Dict[str,Any]:
    if not expr or not expr.strip():
        return {"ok": False, "origin": "rule", "text": ""}
    var_defs = (var_defs or {})
    defaults,_ = _pick_lang_dict(lang)
    merged = {**defaults, **var_defs}
    try:
        ast=_expr_to_ast(expr)
        literal=_phrase(ast, merged, lang)
    except Exception as e:
        return {"ok": False, "origin": "rule", "error": str(e)}
    # Optional GPT paraphrase
    if _OPENAI_CLIENT:
        try:
            schema = {
                "name":"explanation_payload",
                "schema":{
                    "type":"object",
                    "properties":{
                        "sentence":{"type":"string"},
                        "short":{"type":"string"}
                    },
                    "required":["sentence"],
                    "additionalProperties":False
                }
            }
            conn_map = {"NOT":"¬", "AND":"∧", "OR":"∨", "IMP":"→", "IFF":"↔"}
            prompt = (f"Language: {'English' if lang=='en' else 'Hungarian'}.\n"
                      f"Variables meanings:\n" + "\n".join(f"{k}: {v}" for k,v in merged.items()) + "\n\n"
                      f"Symbolic formula (normalized): { _normalize_expr(expr) }\n"
                      f"Task: Paraphrase the logic formula into a single clear, student-friendly sentence using the variable meanings. "
                      f"Keep it concise and faithful to the logic. Avoid extra symbols. "
                      f"If helpful, include a 3–7 word short version as well.")
            resp=_OPENAI_CLIENT.responses.create(
                model=os.environ.get("OPENAI_GPT_MODEL","gpt-4o-mini"),
                instructions="You are a friendly bilingual (EN/HU) logic tutor for geology students. Return compact JSON per schema.",
                input=prompt,
                response_format={"type":"json_schema","json_schema":schema},
            )
            payload=json.loads(resp.output_text)
            sent = payload.get("sentence","").strip()
            short = payload.get("short","").strip()
            text = sent or literal
            if short: text += f"  — {short}"
            return {"ok": True, "origin":"gpt", "text": text, "literal": literal}
        except Exception:
            pass
    return {"ok": True, "origin":"rule", "text": literal}

# ======================================================
# Natural language → symbols
# ======================================================
def _heuristic_parse_nl(text:str, lang:str, var_defs:Dict[str,str])->str:
    # extremely compact, handles a few common patterns (EN/HU)
    t = (text or "").strip().lower()
    if not t: return ""
    # map variable phrases → letters (simple contains)
    # Longer keys first to avoid partial overlaps
    mapping = sorted(var_defs.items(), key=lambda kv: -len(kv[1]))
    for v, phrase in mapping:
        if not phrase: continue
        # loose match: remove articles (en: the, a, an; hu: a, az, egy)
        p = phrase.lower()
        for art in [" the "," a "," an "," az "," egy "]:
            p = p.replace(art, " ")
        p = re.sub(r"\s+", " ", p).strip()
        # replace occurrences with the variable letter
        t = re.sub(re.escape(phrase.lower()), v, t)
        t = re.sub(re.escape(p), v, t)
    # unify connectors
    t = t.replace(" iff ", " ↔ ").replace(" if and only if ", " ↔ ")
    t = t.replace(" akkor és csak akkor, ha ", " ↔ ")
    t = t.replace(" akkor és csak akkor ha ", " ↔ ")
    # if ... then ...
    t = t.replace(" if ", " IF ").replace(" then ", " THEN ")
    t = t.replace(" ha ", " IF ").replace(" akkor ", " THEN ")
    # neither ... nor ...
    t = t.replace(" neither ", " NEITHER ").replace(" nor ", " NOR ")
    t = t.replace(" sem ", " SEM ").replace(" se ", " SEM ")
    # and/or/not
    t = re.sub(r"\b(and|és)\b", "`", t)
    t = re.sub(r"\b(or|vagy)\b", "~", t)
    t = re.sub(r"\b(not|nem|no)\b", ",", t)

    # Patterns
    # NEITHER A NOR B -> ,(A ~ B)
    if "NEITHER" in t and ("NOR" in t or "SEM" in t):
        parts = re.split(r"NEITHER|NOR|SEM", t)
        vars_in = [s.strip() for s in parts if s.strip() and len(s.strip())==1 and s.strip() in _ALLOWED_VARS]
        if len(vars_in)>=2:
            a,b = vars_in[0], vars_in[1]
            return f",({a} ~ {b})"

    # IF A THEN B (EN/HU)
    if "IF" in t and "THEN" in t:
        a = t.split("IF",1)[1].split("THEN",1)[0].strip()
        b = t.split("THEN",1)[1].strip()
        a = re.sub(r"[^pqroiy,`~()]", "", a)
        b = re.sub(r"[^pqroiy,`~()]", "", b)
        if a and b:
            return f"({a}) → ({b})"

    # Simple ↔
    if "↔" in t:
        a,b = t.split("↔",1)
        a = re.sub(r"[^pqroiy,`~()]", "", a).strip()
        b = re.sub(r"[^pqroiy,`~()]", "", b).strip()
        if a and b:
            return f"({a}) ↔ ({b})"

    # Otherwise just keep variable/connectors we recognize
    core = re.sub(r"[^pqroiy,`~()]", "", t)
    return core

def parse_nl_to_symbols(text:str, lang:str="en", var_defs:Optional[Dict[str,str]]=None)->Dict[str,Any]:
    var_defs = (var_defs or {})
    defaults,_ = _pick_lang_dict(lang)
    merged = {**defaults, **var_defs}
    # GPT path
    if _OPENAI_CLIENT:
        try:
            schema = {
                "name":"symbolization_payload",
                "schema":{
                    "type":"object",
                    "properties":{
                        "expr":{"type":"string"},
                        "confidence":{"type":"number"},
                        "notes":{"type":"string"}
                    },
                    "required":["expr"],
                    "additionalProperties":False
                }
            }
            guide = (
                f"Language: {'English' if lang=='en' else 'Hungarian'}.\n"
                f"Allowed variables: {', '.join(sorted(merged.keys()))}.\n"
                f"Meanings:\n" + "\n".join(f"  {k}: {v}" for k,v in merged.items()) + "\n\n"
                "Convert the user's sentence into a propositional logic formula using only these variables and operators:\n"
                "¬ (NOT), ∧ (AND), ∨ (OR), → (implies), ↔ (iff), parentheses. ASCII ',', '`', '~', ->, <-> are also fine.\n"
                "Be faithful to the meaning. Prefer inclusive OR unless the sentence clearly says 'exactly one'.\n"
                "Return JSON per schema, keep it short."
            )
            resp=_OPENAI_CLIENT.responses.create(
                model=os.environ.get("OPENAI_GPT_MODEL","gpt-4o-mini"),
                instructions="You are a careful bilingual symbolization assistant for geology examples. Return ONLY JSON.",
                input=guide + "\n\nUser sentence:\n" + (text or ""),
                response_format={"type":"json_schema","json_schema":schema},
            )
            payload=json.loads(resp.output_text)
            expr = payload.get("expr","")
            if expr:
                # validate/normalize
                expr = _normalize_expr(expr)
                # quick dry run on a tiny env for mentioned vars
                used = sorted(set([c for c in expr if c in _ALLOWED_VARS]))
                test_env = {v: (i%2==0) for i,v in enumerate(used)}
                _ = eval_expr(expr, test_env)  # may raise if malformed
                return {"ok": True, "origin":"gpt", "expr": expr, "confidence": payload.get("confidence")}
        except Exception:
            pass
    # Heuristic fallback
    expr = _heuristic_parse_nl(text, lang, merged)
    if not expr:
        return {"ok": False, "origin":"rule", "error":"Could not parse sentence."}
    try:
        # validate
        used = sorted(set([c for c in expr if c in _ALLOWED_VARS]))
        test_env = {v: (i%2==0) for i,v in enumerate(used)}
        _ = eval_expr(expr, test_env)
        return {"ok": True, "origin":"rule", "expr": _normalize_expr(expr)}
    except Exception as e:
        return {"ok": False, "origin":"rule", "error": str(e)}

# ======================================================
# Truth table utility
# ======================================================
def _tt_rows(varnames: List[str]) -> List[Dict[str, bool]]:
    return [{v: t for v, t in zip(varnames, vals)}
            for vals in itertools.product([True, False], repeat=len(varnames))]

def _tt_for_expr(expr:str, vars_used:List[str]) -> Dict[str,Any]:
    rows=_tt_rows(vars_used)
    col=[]
    for r in rows:
        env={v:bool(r[v]) for v in vars_used}
        try:
            val = eval_expr(expr, env)
            col.append("T" if val else "F")
        except Exception as e:
            col.append("?")
    return {"vars": vars_used, "rows": rows, "values": col}

# ======================================================
# Routes
# ======================================================
@logic_playground_bp.route("/logic-playground")
def logic_playground_home():
    # If using Flask templates, drop this file into your templates/ and render it.
    # Here we try to render a template named 'logic_playground.html' if available.
    try:
        return render_template("logic_playground.html")
    except Exception:
        # fallback text
        return "<h2>Logic Playground</h2><p>Serve the provided logic_playground.html via your static server, or place it in templates/.</p>"

@logic_playground_bp.route("/logic-playground/api/examples")
def logic_playground_examples():
    return jsonify({
        "en":[
            {"text":"If the rock is sandstone and it contains fossils, then it formed in a shallow marine environment.",
             "expr": "(p ` q) → r"},
            {"text":"The rock is sandstone iff it contains fossils.",
             "expr":"p ↔ q"},
            {"text":"If it is not igneous, then it contains neither olivine nor pyroxene.",
             "expr": ",i → (,(o ~ y))"},
        ],
        "hu":[
            {"text":"Ha a kőzet homokkő és fosszíliákat tartalmaz, akkor sekély tengeri környezetben képződött.",
             "expr":"(p ` q) → r"},
            {"text":"A kőzet akkor és csak akkor homokkő, ha fosszíliákat tartalmaz.",
             "expr":"p ↔ q"},
            {"text":"Ha nem magmás, akkor sem olivint, sem piroxént nem tartalmaz.",
             "expr":",i → (,(o ~ y))"},
        ]
    })

@logic_playground_bp.route("/logic-playground/api/explain", methods=["POST"])
def logic_playground_api_explain():
    data = request.get_json(force=True, silent=True) or {}
    expr = data.get("expr","")
    lang = (data.get("lang") or "en").lower()
    var_defs = data.get("vars") or {}
    out = explain_expr(expr, "en" if lang.startswith("en") else "hu", var_defs)
    return jsonify(out)

@logic_playground_bp.route("/logic-playground/api/parse", methods=["POST"])
def logic_playground_api_parse():
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("text","")
    lang = (data.get("lang") or "en").lower()
    var_defs = data.get("vars") or {}
    out = parse_nl_to_symbols(text, "en" if lang.startswith("en") else "hu", var_defs)
    return jsonify(out)

@logic_playground_bp.route("/logic-playground/api/truth-table", methods=["POST"])
def logic_playground_api_tt():
    data = request.get_json(force=True, silent=True) or {}
    expr = data.get("expr","")
    vars_used = data.get("vars") or []
    try:
        expr_n = _normalize_expr(expr)
        if not vars_used:
            # infer by order p,q,r,o,i,y
            vars_used = [v for v in "pqroiy" if v in expr_n]
        tt = _tt_for_expr(expr_n, vars_used)
        return jsonify({"ok": True, "expr": expr_n, "table": tt})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400
