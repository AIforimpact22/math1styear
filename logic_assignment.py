from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from flask import Blueprint, jsonify, render_template, request

logic_assignment_bp = Blueprint("logic_assignment", __name__)


@dataclass
class Check:
    keywords: List[str]
    hint: str


@dataclass
class Question:
    id: str
    title: str
    text: str
    checks: List[Check]
    praise: str = "Excellent work — you captured every required idea."
    coach: str = "Revisit the notes and respond to each bullet explicitly."
    length_hint: int = 80


QUESTIONS: List[Question] = [
    Question(
        id="Q01",
        title="A) Core ideas — fill in the blanks (geoscience flavored)",
        text=(
            "An and statement is true when, and only when, both components are ________.\n"
            "An or statement is false when, and only when, both components are ________.\n"
            "Two statement forms are logically equivalent when, and only when, they always have ________ truth values.\n"
            "De Morgan’s laws say (1) the negation of an and statement is equivalent to an or statement in which each component is ________, and (2) the negation of an or statement is equivalent to an and statement in which each component is ________.\n"
            "A tautology is a statement that is always ________.\n"
            "A contradiction is a statement that is always ________."
        ),
        checks=[
            Check(["both components are true", "both parts are true"], "say an ∧ statement needs both parts true"),
            Check(["both components are false", "both parts are false"], "note that ∨ is only false when both parts are false"),
            Check(["the same truth values", "matching truth values"], "mention matching/same truth values"),
            Check(["each component is negated", "negated", "both components are negated"], "state that De Morgan negates each part"),
            Check(["always true", "true in every case", "true no matter"], "describe a tautology as always true"),
            Check(["always false", "false in every case", "false no matter"], "describe a contradiction as always false"),
        ],
        praise="Perfect — all six blanks are addressed.",
        coach="Answer each blank directly (true/false, same values, negated, tautology/contradiction).",
        length_hint=90,
    ),
    Question(
        id="Q02",
        title="B1) Modus ponens pattern",
        text=(
            "(a) If all basalt flows are mafic, then Flow A is mafic.\n"
            "All basalt flows are mafic.\n"
            "Therefore, Flow A is mafic.\n"
            "Form: If p then q; p; therefore q.\n\n"
            "(b) If all cross-beds can be described in plan-view, then ________.\n"
            "________.\n"
            "Therefore, Cross-bed set X can be described in plan-view."
        ),
        checks=[
            Check(
                [
                    "then cross-bed set x can be described in plan-view",
                    "then x can be described in plan-view",
                    "then cross bed set x can be described in plan view",
                ],
                "complete the conditional with X in the consequent",
            ),
            Check(
                [
                    "all cross-beds can be described in plan-view",
                    "all cross beds can be described in plan view",
                ],
                "repeat the universal premise for cross-beds",
            ),
        ],
        praise="Great — you matched the modus ponens structure.",
        coach="Match the exact structure: restate the conditional and the universal premise.",
        length_hint=50,
    ),
    Question(
        id="Q03",
        title="B2) Modus tollens pattern",
        text=(
            "(a) If all seismic lines have some noise, then Line 12 has noise.\n"
            "Line 12 does not have noise.\n"
            "Therefore, not all seismic lines have noise.\n"
            "Form: If p then q; ¬q; therefore ¬p.\n\n"
            "(b) If ________, then primes are odd.\n"
            "2 is not odd.\n"
            "Therefore, ________."
        ),
        checks=[
            Check(
                [
                    "if all primes are odd, then 2 is odd",
                    "if all primes are odd then 2 is odd",
                ],
                "state the conditional tying all primes to 2",
            ),
            Check(
                [
                    "not all primes are odd",
                    "therefore not all primes are odd",
                ],
                "finish with ¬p: not all primes are odd",
            ),
        ],
        praise="Nice — the conditional and conclusion line up with modus tollens.",
        coach="Spell out the conditional about all primes and end with ¬p (not all primes are odd).",
        length_hint=50,
    ),
    Question(
        id="Q04",
        title="B3) Disjunctive syllogism pattern",
        text=(
            "(a) This rock is limestone or this rock is dolomite.\n"
            "This rock is not limestone.\n"
            "Therefore, this rock is dolomite.\n"
            "Form: p ∨ q; ¬p; therefore q.\n\n"
            "(b) Quartz occurs or logic is confusing.\n"
            "My mind is not shot.\n"
            "Therefore, ________."
        ),
        checks=[
            Check(
                ["logic is confusing"],
                "end with the remaining disjunct: logic is confusing",
            )
        ],
        praise="Exactly — you concluded that logic is confusing.",
        coach="Use the disjunctive syllogism form: conclude with the remaining option (logic is confusing).",
        length_hint=30,
    ),
    Question(
        id="Q05",
        title="B4) Hypothetical syllogism pattern",
        text=(
            "(a) If the core description is faulty, then the lab will flag an error.\n"
            "If the lab flags an error, then the report won’t be released.\n"
            "Therefore, if the core description is faulty, then the report won’t be released.\n"
            "Form: If p then q; if q then r; therefore if p then r.\n\n"
            "(b) If this sandstone has high quartz content, then it is mature.\n"
            "If this sandstone is mature, then it has well-rounded grains.\n"
            "Therefore, if this sandstone has high quartz content, then ________."
        ),
        checks=[
            Check(
                [
                    "it has well-rounded grains",
                    "then it has well-rounded grains",
                    "has well rounded grains",
                ],
                "finish with the grains being well-rounded",
            )
        ],
        praise="Great — you chained to well-rounded grains.",
        coach="Complete the last clause with the final implication: it has well-rounded grains.",
        length_hint=40,
    ),
    Question(
        id="Q06",
        title="C) Which are statements?",
        text=(
            "Decide which of the following are statements (truth-evaluable):\n"
            "a) “Many beach sands show ripple marks.”\n"
            "b) “Measure the thickness of Bed 4.”\n"
            "c) “Porosity ≥ 0.25.”\n"
            "d) “Depth = d₀.”"
        ),
        checks=[
            Check(
                ["a", "many beach sands"],
                "mark option a as a statement",
            ),
            Check(
                ["c", "porosity ≥ 0.25", "porosity >= 0.25"],
                "include option c as a statement",
            ),
            Check(
                ["d", "depth = d₀", "depth = d0"],
                "include option d as a statement",
            ),
            Check(
                ["not b", "b is not", "command"],
                "explain that b) is a command, not a statement",
            ),
        ],
        praise="Correct — you picked a, c, d and excluded b.",
        coach="List the letters: a, c, d are statements; b is a command (not statement).",
        length_hint=40,
    ),
    Question(
        id="Q07",
        title="D1) Translate (fossils + sandstone)",
        text=(
            "Let o = “the outcrop contains fossils”, s = “the sample is sandstone”.\n"
            "Translate: (i) “The outcrop contains fossils and the sample is sandstone.”\n"
            "(ii) “Neither does the outcrop contain fossils nor is the sample sandstone.”"
        ),
        checks=[
            Check(["o ∧ s", "o and s"], "write o ∧ s for the conjunction"),
            Check(["¬o ∧ ¬s", "not o and not s", "¬(o ∨ s)"], "show the double negation result (¬o ∧ ¬s)"),
        ],
        praise="Both symbolic forms look good (o ∧ s, ¬o ∧ ¬s).",
        coach="Express each sentence with o and s: the conjunction and the negated conjunction.",
        length_hint=60,
    ),
    Question(
        id="Q08",
        title="D2) Carbonate vs dolomite",
        text="Let c = “core is carbonate”, d = “core is dolomite”. Translate “The core is carbonate but not dolomite.”",
        checks=[
            Check(["c ∧ ¬d", "c and not d"], "use c ∧ ¬d"),
        ],
        praise="Exactly — c ∧ ¬d.",
        coach="Use c for carbonate and negate d to show it is not dolomite.",
        length_hint=25,
    ),
    Question(
        id="Q09",
        title="D3) Horizon properties",
        text=(
            "Let h = “the horizon is hydrocarbon-bearing”, t = “the horizon is thick”, q = “the horizon is high quality”.\n"
            "Provide symbolic forms for: (a) “H is hydrocarbon-bearing and thick but not high-quality.”\n"
            "(b) “H is not thick but it is hydrocarbon-bearing and high-quality.”\n"
            "(c) “H is neither hydrocarbon-bearing, thick, nor high-quality.”\n"
            "(d) “H is neither thick nor high-quality, but it is hydrocarbon-bearing.”\n"
            "(e) “H is high-quality, but it is not both hydrocarbon-bearing and thick.”"
        ),
        checks=[
            Check(["h ∧ t ∧ ¬q", "h and t and not q"], "capture h ∧ t ∧ ¬q"),
            Check(["¬t ∧ h ∧ q", "not t and h and q"], "show ¬t ∧ h ∧ q"),
            Check(["¬h ∧ ¬t ∧ ¬q", "not h and not t and not q"], "include the full negation ¬h ∧ ¬t ∧ ¬q"),
            Check(["h ∧ ¬t ∧ ¬q", "h and not t and not q"], "handle the “neither thick nor high-quality” but hydrocarbon-bearing"),
            Check(["q ∧ ¬(h ∧ t)", "q and not (h and t)", "q ∧ ¬h ∨?"], "express q ∧ ¬(h ∧ t)"),
        ],
        praise="Great coverage of all five horizon statements.",
        coach="Write each combination with ∧/¬. Include the distribution cases like q ∧ ¬(h ∧ t).",
        length_hint=120,
    ),
    Question(
        id="Q10",
        title="D4) Grain-size ranges",
        text=(
            "Let p = “grain size > 0.5 mm”, q = “grain size = 0.5 mm”, r = “grain size < 2 mm”.\n"
            "Translate: (a) “grain size ≥ 0.5 mm”\n"
            "(b) “2 mm > grain size > 0.5 mm”\n"
            "(c) “2 mm ≥ grain size ≥ 0.5 mm.”"
        ),
        checks=[
            Check(["p ∨ q", "p or q"], "show ≥ 0.5 mm as p ∨ q"),
            Check(["r ∧ p", "r and p"], "capture the open interval with r ∧ p"),
            Check(["(r ∨", "≤ 2", "<= 2"], "show the upper bound (≤2) combined with ≥0.5"),
        ],
        praise="Nice handling of the grain-size ranges.",
        coach="Use p/q/r to show ≥0.5, the open interval, and include the ≤2 upper bound for part (c).",
        length_hint=90,
    ),
    Question(
        id="Q11",
        title="E) Inclusive or exclusive?",
        text="In “A sample passes screening if it has rounded grains or sorting ≥ ‘moderate’,” decide if the “or” is inclusive or exclusive.",
        checks=[
            Check(["inclusive", "inclusive or"], "note that the disjunction is inclusive"),
        ],
        praise="Correct — it’s the inclusive ‘or’.",
        coach="Indicate that both traits could be present, so the ‘or’ is inclusive.",
        length_hint=20,
    ),
    Question(
        id="Q12",
        title="F) Truth-table ideas",
        text=(
            "Respond concisely:\n"
            "• When is ¬p ∧ q true?\n"
            "• Is ¬(p ∧ q) ∨ (p ∨ q) always true?\n"
            "• When is p ∧ (q ∧ r) true?\n"
            "• When is p ∧ (¬q ∨ r) true?"
        ),
        checks=[
            Check(["p is false and q is true", "p false q true"], "state p must be false and q true"),
            Check(["tautology", "always true"], "label the compound as a tautology"),
            Check(["all three", "p q r are true", "when p, q, r are all true"], "require all of p, q, r"),
            Check(["p is true and", "q is false or r is true", "either q is false or r is true"], "explain the condition for p ∧ (¬q ∨ r)"),
        ],
        praise="Great — you summarized each truth-table scenario accurately.",
        coach="Answer each bullet: (F,T), tautology, all true, and p true with (¬q or r).",
        length_hint=80,
    ),
    Question(
        id="Q13",
        title="G) Logical equivalence calls",
        text=(
            "For each pair, say whether they are logically equivalent and give a short justification (absorption, De Morgan, etc.).\n"
            "Use the list from the prompt (p ∨ (p ∧ q) vs p, ¬(p ∧ q) vs ¬p ∨ ¬q, … , (p ∨ q) ∨ (p ∧ r) vs (p ∨ q) ∧ r)."
        ),
        checks=[
            Check(["absorption", "p ∨ (p ∧ q)"], "mention absorption for the first pair"),
            Check(["de morgan", "¬p ∨ ¬q"], "cite De Morgan"),
            Check(["tautology", "t"], "note that p ∨ t ≡ t"),
            Check(["p ∧ t", "equivalent"], "explain p ∧ t ≡ p"),
            Check(["not equivalent", "∧ is stronger", "p ∧ c"], "point out p ∧ c vs p ∨ c not equivalent"),
            Check(["associative", "associativity"], "reference associativity"),
            Check(["distribution", "distributive"], "reference distribution"),
            Check(["not equivalent", "counterexample", "p = f", "r = t"], "note p ∧ (q ∨ r) vs (p ∧ q) ∨ (p ∧ r) equivalence and contrast with the others"),
        ],
        praise="Nice job referencing the right laws for each equivalence/non-equivalence.",
        coach="Walk through each bullet and name the law or counterexample that applies.",
        length_hint=140,
    ),
    Question(
        id="Q14",
        title="H) De Morgan negations in geology wording",
        text=(
            "Provide the negation for each geology-flavoured sentence in De Morgan style (push ¬ inside)."
        ),
        checks=[
            Check(["layer a is not sandstone", "layer a isn’t sandstone"], "negate the first component for Layer A/B"),
            Check(["layer b is not shale", "layer b isn’t shale"], "negate the Layer B clause"),
            Check(["sample is not carbonate", "sample isn’t carbonate"], "negate the carbonate clause"),
            Check(["porosity is not high", "porosity isn’t high"], "negate the porosity clause"),
            Check(["core is not broken", "core isn’t broken"], "negate the core clause"),
            Check(["scanner is not mis-calibrated", "scanner isn’t mis-calibrated"], "negate the scanner clause"),
            Check(["tide is not in", "tide isn’t in"], "negate the tide"),
            Check(["watch is not fast", "watch isn’t fast"], "negate the watch"),
            Check(["no logical error in the first ten lines", "no logical error"], "negate the program clause"),
            Check(["dataset is complete", "dataset is not incomplete"], "affirm the dataset completeness"),
            Check(["quartz content is not at an all-time high", "quartz content isn’t at an all-time high"], "negate the quartz clause"),
            Check(["feldspar is not at a record low", "feldspar isn’t at a record low"], "negate the feldspar clause"),
        ],
        praise="Solid — you pushed the negations inside each geology sentence.",
        coach="Write each negation explicitly: “not sandstone or not shale”, “core not broken and scanner not mis-calibrated”, etc.",
        length_hint=160,
    ),
    Question(
        id="Q15",
        title="I) Range/inequality negations",
        text=(
            "Provide the negation for each inequality statement in the list (porosity φ, grain size d)."
        ),
        checks=[
            Check(["φ ≤ -2", "phi ≤ -2", "phi <= -2"], "include φ ≤ -2"),
            Check(["φ ≥ 0.35", "phi ≥ 0.35", "phi >= 0.35"], "include φ ≥ 0.35"),
            Check(["d ≤ -10", "d <= -10"], "include d ≤ -10"),
            Check(["d ≥ 2", "d >= 2"], "include d ≥ 2"),
            Check(["0.0625 ≤ d ≤ 2", "0.0625 <= d <= 2"], "describe the closed interval for sand/gravel"),
            Check(["0.10 < φ ≤ 0.25", "0.10 < phi ≤ 0.25", "0.10 < phi <= 0.25"], "show the mid-porosity band"),
            Check(["d ≥ 1", "d >= 1"], "include d ≥ 1"),
            Check(["d < 0.25"], "include d < 0.25"),
            Check(["φ ≥ 0", "phi ≥ 0", "phi >= 0"], "include φ ≥ 0"),
            Check(["φ < -0.07", "phi < -0.07"], "include φ < -0.07"),
        ],
        praise="Great — you described each negated range precisely.",
        coach="State each negation explicitly (≤/≥ switched).",
        length_hint=140,
    ),
    Question(
        id="Q16",
        title="J) Data-filter negations",
        text=(
            "Rewrite the data-filter expressions with negations pushed inside (using ∧/∨)."
        ),
        checks=[
            Check(["n_samples ≤ 100", "n samples ≤ 100", "n_samples <= 100"], "include n_samples ≤ 100"),
            Check(["n_valid > 500", "n valid > 500"], "include n_valid > 500"),
            Check(["n_valid ≥ 200", "n_valid >= 200"], "require n_valid ≥ 200"),
            Check(["depth ≥ 50", "depth >= 50"], "include depth ≥ 50"),
            Check(["porosity ≤ 0.25", "porosity <= 0.25"], "include porosity ≤ 0.25"),
            Check(["depth < 50", "depth <50"], "include depth < 50"),
            Check(["depth ≥ 75", "depth >= 75"], "include depth ≥ 75"),
            Check(["porosity ≤ 0.30", "porosity <= 0.30"], "include porosity ≤ 0.30"),
        ],
        praise="Well done — both negated filters are written correctly.",
        coach="Spell out each clause after the negation (≤/≥ swapped, distribute ¬ over ∨).",
        length_hint=140,
    ),
    Question(
        id="Q17",
        title="K) Tautology or contradiction?",
        text="Classify each expression (tautology/contradiction/contingent) using the provided reasoning.",
        checks=[
            Check(["tautology", "covers all cases"], "label (p ∧ q) ∨ (¬p ∨ (p ∧ ¬q)) as a tautology"),
            Check(["contradiction", "requires p and ¬p"], "label (p ∧ ¬q) ∧ (¬p ∨ q) as a contradiction"),
            Check(["implication", "always true", "tautology"], "note the third expression is always true"),
            Check(["law of excluded middle", "tautology", "always true"], "state the last expression is a tautology"),
        ],
        praise="Great classifications for each expression.",
        coach="Name whether each is a tautology or contradiction and justify briefly.",
        length_hint=100,
    ),
    Question(
        id="Q18",
        title="L) Geologic code strings",
        text=(
            "Let positions be {S,L,B} × {F,X}. Identify the code sets for the given expressions (31a–31c)."
        ),
        checks=[
            Check(["sf", "sx", "lf", "lx"], "list SF, SX, LF, LX"),
            Check(["bf", "bx"], "list BF, BX"),
            Check(["bf", "lf"], "include BF and LF"),
        ],
        praise="Perfect — you mapped each logical condition to the correct code list.",
        coach="List the code pairs explicitly (e.g., SF, SX, LF, LX).",
        length_hint=80,
    ),
    Question(
        id="Q19",
        title="M) Natural-language equivalence?",
        text=(
            "Decide whether statements (a) and (b) are logically equivalent and justify with a short counter-scenario or explanation."
        ),
        checks=[
            Check(["not equivalent", "different", "scope"], "state they are not equivalent"),
            Check(["layer a", "layer b"], "mention the roles of Layer A and Layer B"),
        ],
        praise="Good — you explained why the wording is not logically equivalent.",
        coach="State that the sentences are not equivalent and reference the roles of Layer A/B.",
        length_hint=70,
    ),
]

QUESTION_LOOKUP: Dict[str, Question] = {q.id: q for q in QUESTIONS}


QUESTION_HU: Dict[str, str] = {
    "Q01": (
        "Az „és” állítás akkor és csak akkor igaz, ha mindkét része ________.\n"
        "Az „vagy” állítás akkor és csak akkor hamis, ha mindkét része ________.\n"
        "Két állításforma akkor és csak akkor logikailag ekvivalens, ha mindig ________ igazságértékeik vannak.\n"
        "De Morgan törvényei szerint (1) egy „és” állítás tagadása ekvivalens egy „vagy” állítással, amelyben mindegyik rész ________,"
        " és (2) egy „vagy” állítás tagadása ekvivalens egy „és” állítással, amelyben mindegyik rész ________.\n"
        "Tautológia az az állítás, amely mindig ________.\n"
        "Kontradikció az az állítás, amely mindig ________."
    ),
    "Q02": (
        "(a) Ha minden bazaltfolyam mafikus, akkor az A folyás mafikus.\n"
        "Minden bazaltfolyam mafikus.\n"
        "Ezért az A folyás mafikus.\n"
        "Forma: Ha p akkor q; p; tehát q.\n\n"
        "(b) Ha minden keresztágy tervnézetben leírható, akkor ________.\n"
        "________.\n"
        "Ezért az X keresztágy-készlet tervnézetben leírható."
    ),
    "Q03": (
        "(a) Ha minden szeizmikus szelvényben van valamilyen zaj, akkor a 12-es szelvény zajos.\n"
        "A 12-es szelvény nem zajos.\n"
        "Ezért nem igaz, hogy minden szeizmikus szelvény zajos.\n"
        "Forma: Ha p akkor q; ¬q; tehát ¬p.\n\n"
        "(b) Ha ________, akkor a prímek páratlanok.\n"
        "A 2 nem páratlan.\n"
        "Ezért ________."
    ),
    "Q04": (
        "(a) Ez a kő mészkő vagy ez a kő dolomit.\n"
        "Ez a kő nem mészkő.\n"
        "Ezért ez a kő dolomit.\n"
        "Forma: p ∨ q; ¬p; tehát q.\n\n"
        "(b) Vagy kvarc fordul elő, vagy a logika zavaros.\n"
        "Az elmém nincs kikészülve.\n"
        "Ezért ________."
    ),
    "Q05": (
        "(a) Ha a magleírás hibás, akkor a labor hibát jelez.\n"
        "Ha a labor hibát jelez, akkor a jelentés nem kerül kiadásra.\n"
        "Ezért ha a magleírás hibás, akkor a jelentés nem kerül kiadásra.\n"
        "Forma: Ha p akkor q; ha q akkor r; tehát ha p akkor r.\n\n"
        "(b) Ha ez a homokkő magas kvarctartalmú, akkor érett.\n"
        "Ha ez a homokkő érett, akkor jól kerekített szemcséi vannak.\n"
        "Ezért ha ez a homokkő magas kvarctartalmú, akkor ________."
    ),
    "Q06": (
        "Döntsd el, hogy az alábbiak közül melyek kijelentések (igazságértékkel bírnak):\n"
        "a) „Sok tengerparti homok mutat hullámnyomokat.”\n"
        "b) „Mérd meg a 4. réteg vastagságát!”\n"
        "c) „Porozitás ≥ 0,25.”\n"
        "d) „Mélység = d₀.”"
    ),
    "Q07": (
        "Legyen o = „a feltárásban fosszíliák vannak”, s = „a minta homokkő”.\n"
        "Fordítsd le: (i) „A feltárásban fosszíliák vannak, és a minta homokkő.”\n"
        "(ii) „Sem a feltárásban nincsenek fosszíliák, sem a minta nem homokkő.”"
    ),
    "Q08": "Legyen c = „a mag karbonát”, d = „a mag dolomit”. Fordítsd le: „A mag karbonát, de nem dolomit.”",
    "Q09": (
        "Legyen h = „a réteg szénhidrogént tartalmaz”, t = „a réteg vastag”, q = „a réteg jó minőségű”.\n"
        "Add meg a szimbólumos alakokat: (a) „H szénhidrogéntartalmú és vastag, de nem jó minőségű.”\n"
        "(b) „H nem vastag, de szénhidrogéntartalmú és jó minőségű.”\n"
        "(c) „H sem szénhidrogéntartalmú, sem vastag, sem jó minőségű.”\n"
        "(d) „H sem vastag, sem jó minőségű, de szénhidrogéntartalmú.”\n"
        "(e) „H jó minőségű, de nem mind szénhidrogéntartalmú és vastag.”"
    ),
    "Q10": (
        "Legyen p = „a szemcseméret > 0,5 mm”, q = „a szemcseméret = 0,5 mm”, r = „a szemcseméret < 2 mm”.\n"
        "Fordítsd le: (a) „a szemcseméret ≥ 0,5 mm”\n"
        "(b) „2 mm > szemcseméret > 0,5 mm”\n"
        "(c) „2 mm ≥ szemcseméret ≥ 0,5 mm.”"
    ),
    "Q11": "Döntsd el, hogy a „Minta átmegy a szűrésen, ha kerek szemcséi vannak vagy a szemcsesorrend ≥ ‘közepes’” mondatban az „vagy” inkluzív vagy exkluzív.",
    "Q12": (
        "Válaszolj tömören:\n"
        "• Mikor igaz a ¬p ∧ q?\n"
        "• Mindig igaz-e a ¬(p ∧ q) ∨ (p ∨ q)?\n"
        "• Mikor igaz a p ∧ (q ∧ r)?\n"
        "• Mikor igaz a p ∧ (¬q ∨ r)?"
    ),
    "Q13": (
        "Döntsd el minden párnál, hogy logikailag ekvivalensek-e, és adj rövid indoklást (abszorpció, De Morgan stb.).\n"
        "Használd a felsorolást a feladatban (p ∨ (p ∧ q) vs p, ¬(p ∧ q) vs ¬p ∨ ¬q, … , (p ∨ q) ∨ (p ∧ r) vs (p ∨ q) ∧ r)."
    ),
    "Q14": "Add meg a geológiai példamondatok negációját De Morgan szabályai szerint (vidd be a tagadást a mondatokba).",
    "Q15": "Add meg az egyes egyenlőtlenségek negációját (porozitás φ, szemcseméret d).",
    "Q16": "Írd át az adatszűrő kifejezéseket úgy, hogy a negációk a belső részekre kerüljenek (∧/∨ használatával).",
    "Q17": "Osztályozd az egyes kifejezéseket (tautológia/ellentmondás/esetleges) a megadott érvelés alapján.",
    "Q18": "Legyenek a pozíciók {S,L,B} × {F,X}. Azonosítsd a kódhalmazokat a megadott kifejezésekhez (31a–31c).",
    "Q19": "Döntsd el, hogy az (a) és (b) állítás logikailag ekvivalens-e, és indokold rövid ellenpéldával vagy magyarázattal.",
}


VARIANT_HINTS: Sequence[Tuple[str, str]] = (
    ("Highlight the logical connectors you rely on.", "Emeld ki, mely logikai kötőszavakat használod."),
    ("State any assumptions explicitly in one sentence.", "Egy mondatban írd le a felhasznált feltevéseidet."),
    ("Give at least one example or mini-scenario to illustrate your answer.", "Adj legalább egy példát vagy rövid szituációt a válasz szemléltetésére."),
    ("Keep your notation consistent throughout the response.", "Ügyelj rá, hogy a jelöléseid következetesek legyenek a teljes válaszban."),
    ("Mention the key law (modus ponens, De Morgan, etc.) by name.", "Nevezd meg a kulcsfontosságú szabályt (modus ponens, De Morgan stb.)."),
    ("Conclude with a short check that your result matches the form.", "Zárásként ellenőrizd röviden, hogy az eredmény megfelel-e a formának."),
    ("Underline, metaphorically, the term that changes in your variant.", "Hangsúlyozd, hogy a változatban melyik kifejezés módosul."),
    ("List the sub-clauses in the same order as you interpret them.", "Sorold fel az alciklusokat abban a sorrendben, ahogyan értelmezed őket."),
)


TITLE_VARIANTS: Sequence[Tuple[str, str]] = (
    ("Variant A", "Változat A"),
    ("Variant B", "Változat B"),
    ("Variant C", "Változat C"),
    ("Variant D", "Változat D"),
    ("Variant E", "Változat E"),
    ("Variant F", "Változat F"),
    ("Variant G", "Változat G"),
    ("Variant H", "Változat H"),
)


def _seed_from_identifiers(name: str, neptun: str) -> int:
    key = f"{name.strip().lower()}|{neptun.strip().upper()}"
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def _format_bilingual_text(qid: str, english: str, hint_pair: Tuple[str, str]) -> str:
    base_hu = QUESTION_HU.get(qid, "")
    extra_en, extra_hu = hint_pair
    sections = [english.strip(), "", "Magyarul:", base_hu.strip()]
    if extra_en:
        sections.extend(
            [
                "",
                f"Variant prompt: {extra_en}",
                "Magyar változat:",
                f"{extra_hu}",
            ]
        )
    return "\n".join(section for section in sections if section)


def _personalize_questions(name: str, neptun: str) -> List[Dict[str, str]]:
    seed = _seed_from_identifiers(name, neptun)
    rng = random.Random(seed)
    shuffled = list(QUESTIONS)
    rng.shuffle(shuffled)

    hint_choices = list(VARIANT_HINTS)
    rng.shuffle(hint_choices)
    if not hint_choices:
        hint_choices = [("", "")]

    title_variants = list(TITLE_VARIANTS)
    rng.shuffle(title_variants)
    if not title_variants:
        title_variants = [("Variant", "Változat")]

    personalized: List[Dict[str, str]] = []

    for idx, question in enumerate(shuffled):
        hint_pair = hint_choices[idx % len(hint_choices)]
        title_variant_en, title_variant_hu = title_variants[idx % len(title_variants)]
        bilingual_title = f"{question.title} — {title_variant_en} / {title_variant_hu}"
        bilingual_text = _format_bilingual_text(question.id, question.text, hint_pair)
        personalized.append({"id": question.id, "title": bilingual_title, "text": bilingual_text})

    return personalized


def _score_answer(answer: str, question: Question) -> Dict[str, Any]:
    text = (answer or "").strip()
    if not text:
        return {
            "score": 0,
            "feedback": "Please provide an answer that addresses each part of the prompt.",
        }

    lowered = text.lower()
    total_checks = len(question.checks)
    hits = 0
    missing: List[str] = []

    for chk in question.checks:
        if not chk.keywords:
            continue
        if any(keyword.lower() in lowered for keyword in chk.keywords):
            hits += 1
        else:
            if chk.hint:
                missing.append(chk.hint)

    base = 6 if len(text) >= question.length_hint else 4
    bonus = round((hits / total_checks) * 4) if total_checks else 4
    score = max(0, min(10, base + bonus))

    if total_checks and hits == total_checks:
        feedback = question.praise
    elif hits >= max(1, total_checks // 2):
        if missing:
            feedback = f"Nice work. To firm it up, also mention: {', '.join(missing[:2])}."
        else:
            feedback = "Nice work. Add a touch more detail to reach full credit."
    else:
        feedback = question.coach
        if missing:
            feedback += f" Try including: {', '.join(missing[:2])}."

    return {"score": score, "feedback": feedback}


def _summary(overall_pct: int) -> str:
    if overall_pct >= 90:
        return "Outstanding mastery of the logic review — everything lines up."
    if overall_pct >= 75:
        return "Great job. Double-check any hints mentioned in the feedback to polish the last details."
    if overall_pct >= 60:
        return "Good effort. Revisit the sections flagged in feedback (truth tables, negations, etc.)."
    return "Review the answer key carefully and revise each section before exporting the PDF."


@logic_assignment_bp.route("/logic-assignment")
def logic_assignment_home():
    return render_template("assignment_logic.html")


@logic_assignment_bp.route("/logic-assignment/api/generate", methods=["POST"])
def logic_assignment_generate():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    neptun = (data.get("neptun") or "").strip().upper()
    if not name or not neptun:
        return jsonify({"error": "Missing name or Neptun code"}), 400

    personalized = _personalize_questions(name, neptun)

    return jsonify(
        {
            "assignment": "Logic for Geoscience",
            "questions": personalized,
        }
    )


@logic_assignment_bp.route("/logic-assignment/api/grade", methods=["POST"])
def logic_assignment_grade():
    data = request.get_json(force=True, silent=True) or {}
    qa = data.get("qa") or []

    per_question = []
    total = 0
    counted = 0

    for item in qa:
        qid = item.get("id")
        spec = QUESTION_LOOKUP.get(qid)
        if not spec:
            continue
        result = _score_answer(item.get("answer", ""), spec)
        score = int(result["score"])
        feedback = result["feedback"]
        per_question.append({"id": qid, "score": score, "feedback": feedback})
        total += score
        counted += 1

    overall_pct = round(total / (counted * 10) * 100) if counted else 0

    return jsonify(
        {
            "per_question": per_question,
            "overall_pct": overall_pct,
            "pass": overall_pct >= 70,
            "summary": _summary(overall_pct),
        }
    )
