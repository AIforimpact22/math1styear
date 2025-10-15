from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from flask import Blueprint, jsonify, render_template, request


functions_assignment_bp = Blueprint("functions_assignment", __name__)


@dataclass(frozen=True)
class Check:
    keywords: Sequence[str]
    hint: str


@dataclass(frozen=True)
class QuestionSpec:
    id: str
    title_en: str
    title_hu: str
    text_en: str
    text_hu: str
    checks: Sequence[Check]
    praise: str
    coach: str
    length_hint: int = 80

    def payload(self, hint: Tuple[str, str]) -> Dict[str, str]:
        hint_en, hint_hu = hint
        text_en = self.text_en.strip()
        text_hu = self.text_hu.strip()
        if hint_en:
            text_en = f"{text_en}\n\nReflection cue: {hint_en}".strip()
        if hint_hu:
            text_hu = f"{text_hu}\n\nReflexiós tipp: {hint_hu}".strip()
        return {
            "id": self.id,
            "title": f"{self.title_en} / {self.title_hu}",
            "text": _bilingual_block(text_en, text_hu),
        }


REFLECTION_HINTS: Sequence[Tuple[str, str]] = (
    (
        "Reference at least one ordered pair from D when you justify your claim.",
        "Hivatkozz legalább egy rendezett párra a D halmazból, amikor igazolod az állításodat.",
    ),
    (
        "State the mathematical notation (A, B, φ) alongside the plain-language answer.",
        "Írd le a matematikai jelöléseket (A, B, φ) a hétköznapi magyarázat mellett.",
    ),
    (
        "Mention the depth units (metres) at least once to keep the geology context.",
        "Említsd meg legalább egyszer a mélység mértékegységét (méter), hogy megmaradjon a geológiai kontextus.",
    ),
    (
        "Close your answer with a short check that ties back to the dataset D.",
        "Zárd a válaszodat egy rövid ellenőrzéssel, amely visszautal a D adathalmazra.",
    ),
    (
        "Highlight which threshold you used (≥ value or ≤ value) so the grader sees it clearly.",
        "Emeld ki, melyik küszöbértéket használtad (≥ vagy ≤), hogy az értékelő könnyen lássa.",
    ),
)


def _bilingual_block(text_en: str, text_hu: str) -> str:
    return f"{text_en}\n\nMagyarul:\n{text_hu}".strip()


def _seed_from_identifiers(name: str, neptun: str) -> int:
    key = f"{name.strip().lower()}|{neptun.strip().upper()}"
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def _format_phi(value: float) -> str:
    return f"{value:.2f}"


def _format_phi_comma(value: float) -> str:
    return _format_phi(value).replace(".", ",")


def _generate_dataset(rng: random.Random) -> Dict[str, Any]:
    depths = sorted(rng.sample(range(1080, 1420), 5))
    phis = [round(rng.uniform(0.18, 0.35), 2) for _ in depths]
    pairs = list(zip(depths, phis))

    max_pair = max(pairs, key=lambda p: p[1])
    min_pair = min(pairs, key=lambda p: p[1])

    exists_threshold = round(rng.uniform(min_pair[1], max_pair[1]), 2)
    meets_exists = [depth for depth, value in pairs if value >= exists_threshold]
    if not meets_exists:
        exists_threshold = round(max_pair[1], 2)
        meets_exists = [max_pair[0]]

    delta = rng.uniform(0.03, 0.08)
    forall_threshold = round(max_pair[1] - delta, 2)
    if forall_threshold >= max_pair[1]:
        forall_threshold = round(max_pair[1] - 0.02, 2)
    if forall_threshold <= 0:
        forall_threshold = 0.10

    pairs_text = ", ".join(
        f"({depth} m, φ = {_format_phi(phi)})" for depth, phi in pairs
    )
    text_en = f"Measurements D = {{{pairs_text}}}."
    text_hu = f"A D mérési halmaz = {{{pairs_text}}}."

    return {
        "depths": depths,
        "phis": phis,
        "pairs": pairs,
        "max_pair": max_pair,
        "exists_threshold": exists_threshold,
        "exists_threshold_str": _format_phi(exists_threshold),
        "forall_threshold": forall_threshold,
        "forall_threshold_str": _format_phi(forall_threshold),
        "meets_exists": meets_exists,
        "text_en": text_en,
        "text_hu": text_hu,
        "pairs_for_display": [
            {"depth": depth, "phi": _format_phi(phi)} for depth, phi in pairs
        ],
    }


def _build_questions(dataset: Dict[str, Any], rng: random.Random) -> List[QuestionSpec]:
    depths: List[int] = dataset["depths"]
    phis: List[float] = dataset["phis"]
    pairs: List[Tuple[int, float]] = dataset["pairs"]
    max_depth, max_phi = dataset["max_pair"]
    exists_threshold = dataset["exists_threshold_str"]
    forall_threshold = dataset["forall_threshold_str"]
    meets_exists: List[int] = dataset["meets_exists"]

    hints = list(REFLECTION_HINTS)
    rng.shuffle(hints)
    if not hints:
        hints = [("", "")]

    questions: List[QuestionSpec] = []

    q1_checks: List[Check] = [
        Check(["domain", "tartomány", "a ="], "Name the domain A explicitly."),
        Check(["codomain", "céltartomány", "b ="], "State the codomain B."),
        Check(["0 ≤ φ ≤ 1", "0<=φ<=1", "0 <= phi <= 1", "0<=phi<=1"], "Mention the porosity range 0 ≤ φ ≤ 1."),
    ]
    for depth in depths:
        q1_checks.append(
            Check([str(depth)], f"Include the depth {depth} m inside the domain.")
        )
    q1_checks.append(
        Check(
            [_format_phi(phis[0]), _format_phi_comma(phis[0])],
            f"Quote at least one porosity value such as {_format_phi(phis[0])}.",
        )
    )
    questions.append(
        QuestionSpec(
            id="FQ01",
            title_en="1) Domain, codomain, ordered pairs",
            title_hu="1) Értelmezési tartomány, céltartomány, rendezett párok",
            text_en=(
                "Use the porosity log D above. (a) List the domain A by naming every depth. "
                "(b) State a codomain B that matches porosity measurements (0 ≤ φ ≤ 1). "
                "(c) Write two ordered pairs taken directly from D."
            ),
            text_hu=(
                "Használd a fenti D porozitás-görbét. (a) Sorold fel az A értelmezési tartományt minden mélységgel. "
                "(b) Add meg a B céltartományt, amely illik a porozitás méréseihez (0 ≤ φ ≤ 1). "
                "(c) Írj fel két rendezett párt közvetlenül D-ből."
            ),
            checks=q1_checks,
            praise="Excellent — the domain, codomain, and ordered pairs all match the dataset.",
            coach="List every depth for A, note B with 0 ≤ φ ≤ 1, and copy two ordered pairs from D.",
            length_hint=110,
        )
    )

    questions.append(
        QuestionSpec(
            id="FQ02",
            title_en="2) Function test",
            title_hu="2) Függvényteszt",
            text_en=(
                "Explain why the relation D qualifies as a function φ: A → B. Focus on the idea of one porosity value per depth."
            ),
            text_hu=(
                "Magyarázd el, miért tekinthető a D reláció függvénynek φ: A → B alakban. Emeld ki, hogy minden mélységhez egy porozitás érték tartozik."
            ),
            checks=[
                Check(
                    ["each depth", "every depth", "minden mélység"],
                    "State that you checked every depth in A.",
                ),
                Check(
                    ["single", "one value", "egy érték", "unique"],
                    "Mention that each depth has exactly one value.",
                ),
                Check(["porosity", "φ", "phi"], "Refer to porosity values explicitly."),
                Check(["function", "függvény"], "Name the mapping as a function."),
            ],
            praise="Great — you highlighted the one-depth-one-value rule clearly.",
            coach="Spell out that each depth in A maps to exactly one porosity value in B, which makes D a function.",
            length_hint=80,
        )
    )

    questions.append(
        QuestionSpec(
            id="FQ03",
            title_en="3) Highest porosity",
            title_hu="3) Legmagasabb porozitás",
            text_en=(
                "Identify the depth with the highest porosity in D and interpret what that means for the well log."
            ),
            text_hu=(
                "Azonosítsd a D halmazban a legmagasabb porozitású mélységet, és értelmezd, mit jelent ez a kútmérés szempontjából."
            ),
            checks=[
                Check([str(max_depth)], f"Name the depth {max_depth} m."),
                Check(
                    [_format_phi(max_phi), _format_phi_comma(max_phi)],
                    f"Quote the porosity value {_format_phi(max_phi)}.",
                ),
                Check(["highest", "max", "legmagasabb", "maximum"], "Mention that this is the highest value."),
            ],
            praise="Spot on — you found the peak porosity and explained its significance.",
            coach="State which depth has the maximum φ value and what that implies for the log.",
            length_hint=70,
        )
    )

    exists_list_en = ", ".join(f"{depth} m" for depth in meets_exists)
    exists_list_hu = exists_list_en
    questions.append(
        QuestionSpec(
            id="FQ04",
            title_en="4) Depths meeting a threshold",
            title_hu="4) Küszöböt elérő mélységek",
            text_en=(
                f"List every depth where φ ≥ {exists_threshold} and summarise what that tells you about the reservoir quality."
            ),
            text_hu=(
                f"Sorold fel az összes olyan mélységet, ahol φ ≥ {exists_threshold}, és foglald össze, mit jelent ez a tárolókőzet minőségére nézve."
            ),
            checks=[
                Check([exists_threshold, exists_threshold.replace(".", ",")], "Cite the ≥ threshold explicitly."),
                Check(["≥", ">=", "legalább"], "Use the ≥ idea in your description."),
            ]
            + [
                Check([str(depth)], f"Include the depth {depth} m from the threshold list.")
                for depth in meets_exists
            ],
            praise=f"Great — you listed {exists_list_en} and interpreted the higher porosity zones.",
            coach=f"Name each depth with φ ≥ {exists_threshold} and comment on why those intervals matter.",
            length_hint=90,
        )
    )

    questions.append(
        QuestionSpec(
            id="FQ05",
            title_en="5) Existential statement",
            title_hu="5) Egzisztenciális állítás",
            text_en=(
                f"Write the statement ‘There exists a depth with φ ≥ {exists_threshold}’ using quantifier notation, and then paraphrase it."
            ),
            text_hu=(
                f"Írd fel kvantoros jelöléssel a ‘Van olyan mélység, ahol φ ≥ {exists_threshold}’ állítást, majd fogalmazd át szavakkal."
            ),
            checks=[
                Check(["∃", "there exists", "van olyan"], "Use the existential quantifier."),
                Check(["φ", "phi"], "Include φ(z) in your notation."),
                Check([exists_threshold, exists_threshold.replace(".", ",")], "State the threshold value."),
                Check(["≥", ">=", "legalább"], "Show the ≥ relation in your statement."),
            ],
            praise="Excellent — the symbolic form and the explanation line up perfectly.",
            coach=f"Write ∃z ∈ A such that φ(z) ≥ {exists_threshold}, then explain it in words.",
            length_hint=70,
        )
    )

    questions.append(
        QuestionSpec(
            id="FQ06",
            title_en="6) Universal claim check",
            title_hu="6) Univerzális állítás vizsgálata",
            text_en=(
                f"Evaluate the claim ‘For every depth z ∈ A, φ(z) ≤ {forall_threshold}’. State whether it holds for D and justify with a counterexample or confirmation."
            ),
            text_hu=(
                f"Vizsgáld meg az állítást: ‘Minden z ∈ A mélységre φ(z) ≤ {forall_threshold}’. Írd le, hogy igaz-e D-re, és indokold ellenpéldával vagy megerősítéssel."
            ),
            checks=[
                Check(["false", "not true", "hamis", "nem igaz"], "Decide whether the universal claim fails."),
                Check(["∀", "for every", "minden"], "Reference the ∀ (for all) quantifier."),
                Check([str(max_depth)], f"Mention the depth {max_depth} m that tests the claim."),
                Check(
                    [_format_phi(max_phi), _format_phi_comma(max_phi)],
                    f"Quote the porosity value {_format_phi(max_phi)} that breaks the limit.",
                ),
            ],
            praise="Great — you spotted the counterexample and explained why the universal claim fails.",
            coach=f"State that the claim is false and show a depth like {max_depth} m where φ exceeds {forall_threshold}.",
            length_hint=90,
        )
    )

    return questions

def _assignment_spec(name: str, neptun: str) -> Tuple[Dict[str, Any], List[QuestionSpec]]:
    seed = _seed_from_identifiers(name, neptun)
    rng = random.Random(seed)
    dataset = _generate_dataset(rng)
    questions = _build_questions(dataset, rng)
    return dataset, questions


def _score_answer(answer: str, spec: QuestionSpec) -> Dict[str, Any]:
    text = (answer or "").strip()
    if not text:
        return {
            "score": 0,
            "feedback": "Please provide an answer that addresses the full prompt.",
        }

    lowered = text.lower()
    total_checks = len(spec.checks)
    hits = 0
    missing: List[str] = []

    for chk in spec.checks:
        if not chk.keywords:
            continue
        if any(keyword.lower() in lowered for keyword in chk.keywords):
            hits += 1
        else:
            if chk.hint:
                missing.append(chk.hint)

    base = 6 if len(text) >= spec.length_hint else 4
    bonus = round((hits / total_checks) * 4) if total_checks else 4
    score = max(0, min(10, base + bonus))

    if total_checks and hits == total_checks:
        feedback = spec.praise
    elif hits >= max(1, total_checks // 2):
        if missing:
            feedback = f"Good work. To secure full credit, also mention: {', '.join(missing[:2])}."
        else:
            feedback = "Good work. Add a little more detail to reach full credit."
    else:
        feedback = spec.coach
        if missing:
            feedback += f" Try including: {', '.join(missing[:2])}."

    return {"score": score, "feedback": feedback}


def _summary(overall_pct: int) -> str:
    if overall_pct >= 90:
        return "Outstanding command of the porosity-function workflow — ready for submission."
    if overall_pct >= 75:
        return "Nice job. Polish the points mentioned in feedback, then export the PDF."
    if overall_pct >= 60:
        return "Solid start. Revisit the flagged checkpoints (domain/codomain, quantifiers, thresholds)."
    return "Rework the answers using the hints, then re-grade until the score clears 70%."


@functions_assignment_bp.route("/assignment-3")
def assignment_three_home():
    return render_template("assignment_functions.html")


@functions_assignment_bp.route("/assignment-3/api/generate", methods=["POST"])
def assignment_three_generate():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    neptun = (data.get("neptun") or "").strip().upper()
    if not name or not neptun:
        return jsonify({"error": "Missing name or Neptun code"}), 400

    dataset, questions = _assignment_spec(name, neptun)

    hints = list(REFLECTION_HINTS)
    rng = random.Random(_seed_from_identifiers(name, neptun) ^ 0x9E3779B97F4A7C15)
    rng.shuffle(hints)
    if not hints:
        hints = [("", "")]

    payload_questions = []
    for idx, spec in enumerate(questions):
        hint = hints[idx % len(hints)]
        payload_questions.append(spec.payload(hint))

    return jsonify(
        {
            "assignment": "Assignment 3 — Functions in Well Logging",
            "dataset": {
                "summary_en": dataset["text_en"],
                "summary_hu": dataset["text_hu"],
                "pairs": dataset["pairs_for_display"],
                "exists_threshold": dataset["exists_threshold_str"],
                "forall_threshold": dataset["forall_threshold_str"],
            },
            "questions": payload_questions,
        }
    )


@functions_assignment_bp.route("/assignment-3/api/grade", methods=["POST"])
def assignment_three_grade():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    neptun = (data.get("neptun") or "").strip().upper()
    if not name or not neptun:
        return jsonify({"error": "Missing name or Neptun code"}), 400

    dataset, questions = _assignment_spec(name, neptun)
    lookup = {spec.id: spec for spec in questions}

    qa = data.get("qa") or []

    per_question = []
    total = 0
    counted = 0

    for item in qa:
        qid = item.get("id")
        spec = lookup.get(qid)
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
            "dataset": {
                "summary_en": dataset["text_en"],
                "summary_hu": dataset["text_hu"],
                "exists_threshold": dataset["exists_threshold_str"],
                "forall_threshold": dataset["forall_threshold_str"],
            },
        }
    )
