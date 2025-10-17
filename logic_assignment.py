# functions_assignment.py
from __future__ import annotations

import copy
import json
import os
from typing import Any, Dict, List, Tuple, Optional

from flask import Blueprint, jsonify, render_template, request

# --- OpenAI SDK (only used for qualitative items; symbol-builder is rule-graded) ---
try:
    from openai import OpenAI
    _OPENAI_AVAILABLE = True
except Exception:
    _OPENAI_AVAILABLE = False

functions_assignment_bp = Blueprint(
    "functions_assignment", __name__, url_prefix="/assignment-3"
)

OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")


# ======================
# Helpers & bilingual bits
# ======================
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

def BIL(en: str, hu: str) -> str:
    return f"EN: {en} • HU: {hu}"

def _get_openai_client() -> Optional["OpenAI"]:
    if not _OPENAI_AVAILABLE:
        return None
    try:
        return OpenAI()
    except Exception:
        return None


# ======================
# Qualitative LLM grading (kept for your non-symbol items)
# ======================
_BASE_SYSTEM = (
    "You are a precise, fair geology TA. Grade student answers concisely.\n"
    "Return STRICT JSON with keys: score (integer 0..MAX), "
    "feedback_en (<=2 short sentences in English), "
    "feedback_hu (<=2 short sentences in Hungarian).\n"
    "Never reveal the solution. Provide hints only."
)

def _grade_text_llm(rubric: str, student_text: str, max_points: int = 10) -> Tuple[int, str]:
    client = _get_openai_client()
    if not client:
        return 0, BIL(
            "Automated evaluation unavailable. Please justify with the context.",
            "Az automatikus értékelés nem elérhető. Indokolj a kontextussal."
        )
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _BASE_SYSTEM},
                {"role": "user", "content": f"MAX={max_points}\nRubric:\n{rubric}\n\nStudent answer:\n{(student_text or '').strip()}"},
            ],
        )
        data = json.loads(resp.choices[0].message.content or "{}")
        score = max(0, min(max_points, int(data.get("score", 0))))
        en = (data.get("feedback_en") or "Evaluated.").strip()
        hu = (data.get("feedback_hu") or "Értékelve.").strip()
        return score, BIL(en, hu)
    except Exception:
        return 0, BIL("Evaluation error. Tie your explanation to the context.", "Értékelési hiba. Kösd a magyarázatot a kontextushoz.")


# ======================
# Objective graders (existing)
# ======================
def _grade_mcq(item: Dict[str, Any], ans: Dict[str, Any]) -> Tuple[int, str]:
    picked = (ans or {}).get("choice", "")
    ok = str(picked) == str(item.get("expected"))
    return (10 if ok else 0), (BIL("Correct.", "Helyes.") if ok else
                               BIL("Not correct — revisit the definition.", "Nem helyes — nézd át a definíciót."))

def _grade_yesno(item: Dict[str, Any], ans: Dict[str, Any]) -> Tuple[int, str]:
    yn = (ans or {}).get("yes", "")
    correct = bool(item.get("expected_yes", False))
    ok = yn.lower() in ("yes", "y", "true", "t", "igen", "i") if correct else yn.lower() in ("no", "n", "false", "f", "nem")
    return (10 if ok else 0), (BIL("Correct.", "Helyes.") if ok else
                               BIL("Not correct — check the rule.", "Nem helyes — ellenőrizd a szabályt."))

def _grade_yesno_plus_text_llm(item: Dict[str, Any], ans: Dict[str, Any]) -> Tuple[int, str]:
    yn_score_full, _ = _grade_yesno(item, ans)
    yn_points = 6 if yn_score_full == 10 else 0
    text_points, _fb = _grade_text_llm(item.get("llm_rubric", ""), (ans or {}).get("text", ""), max_points=4)
    total = min(10, yn_points + text_points)
    if yn_points == 6 and text_points >= 3:
        fb = BIL("Correct and well-justified.", "Helyes és jól indokolt.")
    else:
        fb = BIL("Re-check the rule and strengthen your justification.", "Ellenőrizd a szabályt, és erősíts az indokláson.")
    return total, fb

def _grade_short_number(item: Dict[str, Any], ans: Dict[str, Any]) -> Tuple[int, str]:
    try:
        got = float((ans or {}).get("value", ""))
    except Exception:
        return 0, BIL("Enter a number (e.g., 0.24).", "Adj meg számot (pl. 0,24).")
    ok = _float_eq(got, float(item.get("expected")))
    return (10 if ok else 0), (BIL("Correct.", "Helyes.") if ok else
                               BIL("Not correct — check the mapping (no spoilers).", "Nem helyes — nézd át a hozzárendelést (spoiler nélkül)."))

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
        fb = BIL("Some values look missing/extra — compare with context.", "Hiányzó vagy felesleges értékek — vessd össze a kontextussal.")
    return score, fb

def _grade_integer(item: Dict[str, Any], ans: Dict[str, Any]) -> Tuple[int, str]:
    try:
        got = int((ans or {}).get("value", ""))
    except Exception:
        return 0, BIL("Enter an integer.", "Adj meg egész számot.")
    ok = (got == int(item.get("expected", 0)))
    return (10 if ok else 0), (BIL("Correct.", "Helyes.") if ok else
                               BIL("Hint: |A×B| = |A| · |B|.", "Tipp: |A×B| = |A| · |B|."))


# ======================
# NEW: Symbol Builder — parser + robust equality
# ======================
TOKENS = {"S", "F", "M", "¬", "∧", "∨", "→", "↔", "(", ")"}

class Node:
    def __init__(self, kind: str, *kids):
        self.kind = kind  # 'var','not','and','or','imp','iff'
        self.kids = list(kids)  # for var: name in kids[0]
    def __repr__(self):  # debug
        return f"{self.kind}({','.join(repr(k) for k in self.kids)})"

def _tokstream(s: str) -> List[str]:
    s = (s or "").replace(" ", "")
    out: List[str] = []
    i = 0
    while i < len(s):
        ch = s[i]
        # single-char tokens and unicode arrows
        if ch in TOKENS:
            out.append(ch); i += 1; continue
        # try two-byte UTF-8 already captured; fallback (shouldn't happen)
        # Allow ASCII aliases (optional): !, &, |, ->, <-> if student typed manually
        if s.startswith("->", i):
            out.append("→"); i += 2; continue
        if s.startswith("<->", i):
            out.append("↔"); i += 3; continue
        if ch in "!~":
            out.append("¬"); i += 1; continue
        if ch in "&∧^":
            out.append("∧"); i += 1; continue
        if ch in "|∨vV":
            out.append("∨"); i += 1; continue
        if ch in "SFM()":
            out.append(ch); i += 1; continue
        # ignore unknown whitespace-like chars
        i += 1
    return out

# Pratt-style recursive descent with precedence: ¬ > ∧ > ∨ > → > ↔
class Parser:
    def __init__(self, toks: List[str]):
        self.toks = toks; self.i = 0
    def peek(self) -> Optional[str]:
        return self.toks[self.i] if self.i < len(self.toks) else None
    def eat(self, t: str) -> bool:
        if self.peek() == t: self.i += 1; return True
        return False
    def parse(self) -> Node:
        n = self.parse_iff()
        if self.peek() is not None:
            # trailing junk -> just return parsed prefix
            pass
        return n
    def parse_iff(self) -> Node:
        n = self.parse_imp()
        while self.eat("↔"):
            rhs = self.parse_imp()
            n = Node("iff", n, rhs)
        return n
    def parse_imp(self) -> Node:
        n = self.parse_or()
        while self.eat("→"):
            rhs = self.parse_or()
            n = Node("imp", n, rhs)
        return n
    def parse_or(self) -> Node:
        n = self.parse_and()
        while self.eat("∨"):
            rhs = self.parse_and()
            n = Node("or", n, rhs)
        return n
    def parse_and(self) -> Node:
        n = self.parse_not()
        while self.eat("∧"):
            rhs = self.parse_not()
            n = Node("and", n, rhs)
        return n
    def parse_not(self) -> Node:
        cnt = 0
        while self.eat("¬"):
            cnt += 1
        atom = self.parse_atom()
        while cnt > 0:
            atom = Node("not", atom); cnt -= 1
        return atom
    def parse_atom(self) -> Node:
        t = self.peek()
        if t in ("S", "F", "M"):
            self.i += 1
            return Node("var", t)
        if self.eat("("):
            n = self.parse_iff()
            self.eat(")")
            return n
        # fallback: unknown -> variable 'S' to avoid crash (won't match)
        return Node("var", "S?")

def parse_formula(s: str) -> Node:
    return Parser(_tokstream(s)).parse()

def _flatten(kind: str, n: Node) -> List[Node]:
    # associate (A ∧ (B ∧ C)) -> [A,B,C]
    if n.kind == kind:
        out = []
        for k in n.kids:
            out.extend(_flatten(kind, k))
        return out
    return [n]

def _canon(n: Node) -> str:
    # canonical string; commutative+associative for and/or; ↔ treated commutative
    if n.kind == "var":
        return n.kids[0]
    if n.kind == "not":
        return f"not({_canon(n.kids[0])})"
    if n.kind in ("and", "or"):
        items = [_canon(k) for k in _flatten(n.kind, n)]
        items.sort()
        return f"{n.kind}(" + ",".join(items) + ")"
    if n.kind == "imp":
        return f"imp({_canon(n.kids[0])},{_canon(n.kids[1])})"
    if n.kind == "iff":
        # symmetric children order
        a, b = _canon(n.kids[0]), _canon(n.kids[1])
        if a > b: a, b = b, a
        return f"iff({a},{b})"
    return "?"

def _expand_imp(n: Node) -> Node:
    # A→B === (¬A ∨ B)
    if n.kind == "imp":
        A, B = _expand_imp(n.kids[0]), _expand_imp(n.kids[1])
        return Node("or", Node("not", A), B)
    return Node(n.kind, *[_expand_imp(k) for k in n.kids]) if n.kids else Node(n.kind, *n.kids)

def _expand_iff(n: Node) -> Node:
    # A↔B === (A→B) ∧ (B→A)
    if n.kind == "iff":
        A = _expand_iff(n.kids[0]); B = _expand_iff(n.kids[1])
        return Node("and", Node("imp", A, B), Node("imp", B, A))
    return Node(n.kind, *[_expand_iff(k) for k in n.kids]) if n.kids else Node(n.kind, *n.kids)

def _equivalent(student: str, expected: str) -> bool:
    # direct canonical compare
    s_ast = parse_formula(student); e_ast = parse_formula(expected)
    if _canon(s_ast) == _canon(e_ast):
        return True
    # compare after expanding ↔ then →
    s2 = _canon(_expand_imp(_expand_iff(s_ast)))
    e2 = _canon(_expand_imp(_expand_iff(e_ast)))
    return s2 == e2

def _grade_symbol_builder(item: Dict[str, Any], ans: Dict[str, Any]) -> Tuple[int, str]:
    got = (ans or {}).get("formula", "").strip()
    if not got:
        return 0, BIL("Build a formula from the palette.", "Állíts össze képletet a palettából.")
    expected_forms: List[str] = item.get("expected_forms", [])
    # Allow simple commutative flips without full parser by trying all listed forms
    ok = any(_equivalent(got, exp) for exp in expected_forms)
    if ok:
        return 10, BIL("Looks correct.", "Helyesnek tűnik.")
    # Hint only — no spoilers
    return 0, BIL(
        "Check placement of ¬ and parentheses; ensure you used the correct connective (→, ∧, ∨, ↔).",
        "Ellenőrizd a ¬ jelet és a zárójeleket; használd a megfelelő kötőjeleket (→, ∧, ∨, ↔)."
    )


# ======================
# Manifest (bilingual), incl. new symbol-builder items
# ======================
def _manifest_functions() -> Dict[str, Any]:
    """
    Full assignment with Symbolic Logic (L1a–L1d) + Geology items.
    The symbol-builder items are auto-graded (exact/equivalent), no LLM involved.
    """
    logic_legend = {
        "S": "EN) Sandstone • HU) Homokkő",
        "F": "EN) Contains fossils • HU) Fosszíliákat tartalmaz",
        "M": "EN) Formed in shallow marine env. • HU) Sekély tengeri környezetben képződött",
    }
    palette = ["S","F","M","¬","∧","∨","→","↔","(",")"]

    return {
        "assignment": "Assignment — Functions & Relations (Geology) + Symbolic Logic / Feladat — Függvények & Relációk + Logika",
        "context": (
            "EN: Background • You analyze a clean sandstone interval in Well A (1195–1208 m). Porosity φ is from density/neutron logs; "
            "typical noise ±0.02; duplicates may occur. A = depths, B = porosity; A×B = all (depth,φ). Relation = TRUE pairs; "
            "Function = each depth has exactly one φ.\n"
            "HU: Háttér • Tiszta homokkő szakaszt elemzel az A kútban (1195–1208 m). A porozitás φ sűrűség/neutron szelvényből származik; "
            "tipikus zaj ±0,02; duplikátum előfordulhat. A = mélységek, B = porozitás; A×B = összes (mélység,φ). Reláció = IGAZ párok; "
            "Függvény = minden mélységhez pontosan egy φ."
        ),
        "hint": "Symbols: ¬ not • ∧ and • ∨ or • → if...then • ↔ iff. Vars: S,F,M (see legend). / Jelek: ¬ nem • ∧ és • ∨ vagy • → ha...akkor • ↔ akkor és csak akkor.",
        "items": [
            # ---------- New: Symbol Builder block ----------
            {
                "id": "L1a",
                "kind": "symbol_builder",
                "title": "1a) Translate: If the rock is sandstone and contains fossils, then it formed in a shallow marine environment. / "
                         "Fordítás: Ha a kőzet homokkő és fosszíliákat tartalmaz, akkor sekély tengeri környezetben képződött.",
                "legend": logic_legend,
                "palette": palette,
                # internal only
                "expected_forms": ["(S ∧ F) → M"]
            },
            {
                "id": "L1b",
                "kind": "symbol_builder",
                "title": "1b) Translate: The rock is not sandstone, but it contains fossils. / "
                         "Fordítás: A kőzet nem homokkő, de fosszíliákat tartalmaz.",
                "legend": logic_legend,
                "palette": palette,
                "expected_forms": ["(¬S) ∧ F", "¬S ∧ F", "F ∧ ¬S"]  # allow commutative flip / optional parens
            },
            {
                "id": "L1c",
                "kind": "symbol_builder",
                "title": "1c) Translate: If it did not form in a shallow marine environment, then it is not sandstone or it does not contain fossils. / "
                         "Fordítás: Ha nem sekély tengeri környezetben képződött, akkor nem homokkő, vagy nem tartalmaz fosszíliákat.",
                "legend": logic_legend,
                "palette": palette,
                "expected_forms": ["¬M → (¬S ∨ ¬F)", "¬M → (¬F ∨ ¬S)"]
            },
            {
                "id": "L1d",
                "kind": "symbol_builder",
                "title": "1d) Translate: The rock is sandstone exactly when it contains fossils. / "
                         "Fordítás: A kőzet akkor és csak akkor homokkő, ha fosszíliákat tartalmaz.",
                "legend": logic_legend,
                "palette": palette,
                "expected_forms": ["S ↔ F", "F ↔ S"]  # treat ↔ as symmetric
            },

            # ---------- Keep a compact Geology block (examples; you can keep all your prior items) ----------
            {
                "id": "FQ1",
                "kind": "mcq",
                "title": "2) Which best describes a relation A→B? / 2) Mi írja le legjobban az A→B relációt?",
                "options": [
                    {"id": "A", "label": "EN) All imaginable pairs (A×B). • HU) Minden elképzelhető pár (A×B)."},
                    {"id": "B", "label": "EN) The TRUE pairs selected from A×B. • HU) Az A×B-ből kiválasztott IGAZ párok."},
                    {"id": "C", "label": "EN) Only one-to-one pairings. • HU) Csak kölcsönösen egyértelmű párosítások."},
                    {"id": "D", "label": "EN) Just the list of B-values. • HU) Csak a B-értékek listája."},
                ],
                "expected": "B",
            },
            {
                "id": "FQ2",
                "kind": "mcq",
                "title": "3) When is “depth → porosity” a function? / 3) Mikor függvény a „mélység → porozitás”?",
                "options": [
                    {"id": "A", "label": "EN) Every depth has exactly one porosity. • HU) Minden mélységhez pontosan egy porozitás tartozik."},
                    {"id": "B", "label": "EN) A depth may have two porosities. • HU) Egy mélységhez két porozitás is tartozhat."},
                    {"id": "C", "label": "EN) Only when porosity > 0.20. • HU) Csak ha a porozitás > 0,20."},
                    {"id": "D", "label": "EN) Only if all wells use the same tool. • HU) Csak ha minden kút azonos műszert használ."},
                ],
                "expected": "A",
            },
            {
                "id": "FQ4",
                "kind": "short_number",
                "title": "4) If F(1198)=0.19, F(1200)=0.24, F(1203)=0.21, what is F(1200)? / "
                         "4) Ha F(1198)=0,19, F(1200)=0,24, F(1203)=0,21, mennyi F(1200)?",
                "expected": 0.24,
            },
            {
                "id": "FQ6",
                "kind": "yesno",
                "title": "5) Is R_close (|φ1 − φ2| ≤ 0.02) necessarily transitive? / "
                         "5) A R_close (|φ1 − φ2| ≤ 0,02) szükségképpen tranzitív?",
                "expected_yes": False,
            },
            {
                "id": "FQ9",
                "kind": "integer",
                "title": "6) If |A|=3 and |B|=4, how many pairs in A×B? / "
                         "6) Ha |A|=3 és |B|=4, hány pár van A×B-ben?",
                "expected": 12,
            },
        ],
    }


# ======================
# Public manifest (sanitize: remove all keys revealing answers)
# ======================
def _public_manifest(full: Dict[str, Any]) -> Dict[str, Any]:
    m = copy.deepcopy(full)
    SENSITIVE = {"expected", "expected_pairs", "expected_yes", "llm_rubric", "expected_forms"}
    for item in m.get("items", []):
        for key in list(item.keys()):
            if key in SENSITIVE:
                item.pop(key, None)
    return m


# ======================
# Routes
# ======================
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
    manifest = _manifest_functions()  # internal copy WITH expected values
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
            if kind == "symbol_builder":
                score, fb = _grade_symbol_builder(item, a)
            elif kind == "mcq":
                score, fb = _grade_mcq(item, a)
            elif kind == "yesno":
                score, fb = _grade_yesno(item, a)
            elif kind == "yesno_plus_text":
                score, fb = _grade_yesno_plus_text_llm(item, a)
            elif kind == "short_number":
                score, fb = _grade_short_number(item, a)
            elif kind == "csv_float_set":
                score, fb = _grade_csv_float_set(item, a)
            elif kind == "integer":
                score, fb = _grade_integer(item, a)
            elif kind == "long_text":
                score, fb = _grade_text_llm(item.get("llm_rubric", ""), (a or {}).get("text", ""), max_points=10)
            else:
                score, fb = 0, BIL("Unknown item type.", "Ismeretlen feladattípus.")
        except Exception as e:
            score, fb = 0, BIL(f"Grading error: {e}", f"Értékelési hiba: {e}")

        per_item.append({"id": qid, "score": int(score), "feedback": fb})
        total += int(score); count += 1

    overall_pct = round(total / (max(1, count) * 10) * 100)
    if overall_pct >= 90:
        summary = BIL("Excellent — precise and well‑applied symbols.", "Kiváló — pontos és helyes szimbólumhasználat.")
    elif overall_pct >= 75:
        summary = BIL("Good — tighten symbol placement and definitions.", "Jó — pontosíts a szimbólumokon és a definíciókon.")
    elif overall_pct >= 60:
        summary = BIL("Progressing — review connectors (¬, ∧, ∨, →, ↔) and parentheses.", "Fejlődő — ismételd át a kötőjeleket és a zárójeleket.")
    else:
        summary = BIL("Revisit the basics of translation and function/relational rules.", "Térj vissza a fordítási alapokhoz és a relációs szabályokhoz.")

    return jsonify({
        "per_item": per_item,
        "overall_pct": overall_pct,
        "pass": overall_pct >= 70,
        "summary": summary,
    })
