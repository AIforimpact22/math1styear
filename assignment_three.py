from __future__ import annotations

import hashlib
import random
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence

from flask import Blueprint, jsonify, render_template, request

from assignment import (
    MODEL_GRADING,
    OPENAI_API_KEY,
    PASS_THRESHOLD,
    _chat_request,
    _safe_json,
)

assignment_three_bp = Blueprint("assignment_three", __name__)

# -----------------
# Shared structures
# -----------------
@dataclass
class LogSegment:
    name: str
    depths: Sequence[int]
    porosity: Sequence[float]

    def ordered_pairs(self) -> List[str]:
        return [f"({d}, {p:.2f})" for d, p in zip(self.depths, self.porosity)]


SEGMENTS: List[LogSegment] = [
    LogSegment("Alpha", (1198, 1200, 1203), (0.19, 0.24, 0.21)),
    LogSegment("Bravo", (1000, 1001, 1002, 1003), (0.18, 0.22, 0.21, 0.23)),
    LogSegment("Charlie", (1310, 1311, 1312), (0.14, 0.18, 0.20)),
    LogSegment("Delta", (1425, 1426, 1427, 1428), (0.26, 0.24, 0.23, 0.24)),
    LogSegment("Echo", (1500, 1501, 1502), (0.11, 0.11, 0.13)),
]

NOISY_SEGMENTS: List[Dict[str, Any]] = [
    {
        "name": "Noisy-1",
        "depths": (1600, 1601, 1601, 1602),
        "porosity": (0.17, 0.19, 0.23, 0.22),
        "note": "depth 1601 repeated with conflicting φ",
    },
    {
        "name": "Noisy-2",
        "depths": (1700, 1700, 1701),
        "porosity": (0.21, 0.21, 0.25),
        "note": "depth 1700 repeated but values consistent",
    },
]

ROLE_GUIDE = (
    "Roles: Student A – Data interpreter (summaries), Student B – Notation lead (formal math), "
    "Student C – Quality reviewer (units/policy plus closing reflection). State each contribution explicitly."
)

EXTRA_PROMPTS = [
    "Mention the domain (depths) and codomain (porosity values) with units.",
    "Use symbols like f: A → B, (z, φ), ∈, ∉, ⊆, × where they help clarity.",
    "Describe how the group handles duplicate or noisy readings before drawing conclusions.",
    "Close with a team sentence confirming collaboration (Student C).",
]


def _seed_from_group(group: str, members: Sequence[str]) -> int:
    today = time.strftime("%Y-%m-%d")
    roster = ",".join(sorted(members))
    base = f"{group}|{roster}|{today}"
    return int(hashlib.sha256(base.encode("utf-8")).hexdigest()[:16], 16) % (2**31 - 1)


@dataclass
class Template:
    name: str

    def build(self, rng: random.Random) -> Dict[str, str]:
        raise NotImplementedError


class DomainCodomainTemplate(Template):
    def build(self, rng: random.Random) -> Dict[str, str]:
        segment = rng.choice(SEGMENTS)
        depths = ", ".join(f"{d} m" for d in segment.depths)
        codomain_hint = "0 ≤ φ ≤ 1 (fraction)"
        text = (
            f"Segment {segment.name} provides the porosity log snippet. Depths: {depths}. Porosity readings: "
            f"{', '.join(f'{p:.2f}' for p in segment.porosity)}.\n"
            "Student A summarises the domain A and codomain B with units and restates the measurement rule.\n"
            "Student B writes the formal function statement (φ: A → B) and states one ordered pair with notation.\n"
            "Student C confirms there are no conflicting depths, explains the duplicate policy, and writes the closing team sentence.\n"
            f"Remember: {ROLE_GUIDE}"
        )
        return {"text": text, "focus": f"Domain & codomain with {segment.name} (B ⊆ {codomain_hint})."}


class OrderedPairTemplate(Template):
    def build(self, rng: random.Random) -> Dict[str, str]:
        segment = rng.choice(SEGMENTS)
        pairs = ", ".join(segment.ordered_pairs())
        text = (
            f"Using segment {segment.name}, list at least three ordered pairs from the porosity log ({pairs}).\n"
            "Student A narrates what each pair (z, φ) means physically.\n"
            "Student B assembles the relation M in set notation and highlights whether it satisfies the definition of a function.\n"
            "Student C checks symbols/units and states how the team would record these pairs for GPT grading.\n"
            f"Finish with explicit role attributions. {ROLE_GUIDE}"
        )
        return {"text": text, "focus": f"Ordered pair builder ({segment.name})."}


class FunctionDiagnosisTemplate(Template):
    def build(self, rng: random.Random) -> Dict[str, str]:
        noisy = rng.choice(NOISY_SEGMENTS)
        pairs = [f"({d}, {p:.2f})" for d, p in zip(noisy["depths"], noisy["porosity"])]
        pair_list = ", ".join(pairs)
        text = (
            f"Diagnose whether the noisy log {noisy['name']} with pairs {pair_list} defines a function. {noisy['note']}.\n"
            "Student A describes the conflict and proposes a cleaning choice (drop or average).\n"
            "Student B rewrites the cleaned relation using proper notation (including ∉ or ⊆ as needed).\n"
            "Student C states the policy for duplicates and delivers the collaboration wrap-up sentence.\n"
            f"Include Student A/B/C labels. {ROLE_GUIDE}"
        )
        return {"text": text, "focus": f"Function or not? ({noisy['name']})."}


class PolicyMemoTemplate(Template):
    def build(self, rng: random.Random) -> Dict[str, str]:
        segment = rng.choice(SEGMENTS)
        text = (
            f"Write a duplicate-handling memo for segment {segment.name}. Depths: {', '.join(map(str, segment.depths))}.\n"
            "Student A states why duplicates occur in porosity logs (field reality).\n"
            "Student B drafts the formal rule in math notation (e.g., restrict A′ ⊆ A).\n"
            "Student C explains how the team will document the decision before GPT grading and signs off with the collaboration line.\n"
            f"State contributions with Student labels. {ROLE_GUIDE}"
        )
        return {"text": text, "focus": "Measurement policy memo."}


class GraphOfFunctionTemplate(Template):
    def build(self, rng: random.Random) -> Dict[str, str]:
        segment = rng.choice(SEGMENTS)
        pairs = ", ".join(segment.ordered_pairs())
        text = (
            f"Show that the cleaned measurement set M = {{{pairs}}} is the graph of a function.\n"
            "Student A identifies domain, codomain, and actual range.\n"
            "Student B states the function f (or φ) formally and references A × B.\n"
            "Student C verifies the vertical-line (no duplicate depths) test and concludes with the teamwork sentence.\n"
            f"Use Student A/B/C prefixes. {ROLE_GUIDE}"
        )
        return {"text": text, "focus": f"Graph of a function ({segment.name})."}


class CartesianProductTemplate(Template):
    def build(self, rng: random.Random) -> Dict[str, str]:
        segment = rng.choice(SEGMENTS)
        depths = segment.depths[:3]
        porosity = segment.porosity[:3]
        axb = ", ".join(f"({d}, {p:.2f})" for d in depths for p in porosity)
        text = (
            f"Using the first three depths {', '.join(map(str, depths))} and porosities {', '.join(f'{p:.2f}' for p in porosity)}, list A × B explicitly ({axb}).\n"
            "Student A explains what A × B conceptually represents.\n"
            "Student B compares A × B to the measured relation M, noting subset status.\n"
            "Student C discusses why we rarely record full A × B in reports and closes with the collaboration sentence.\n"
            f"Keep Student A/B/C labels. {ROLE_GUIDE}"
        )
        return {"text": text, "focus": "Cartesian product vs relation."}


class DepthRelationTemplate(Template):
    def build(self, rng: random.Random) -> Dict[str, str]:
        segment = rng.choice(SEGMENTS)
        shallower_pairs = ", ".join(f"({segment.depths[i]}, {segment.depths[j]})" for i in range(len(segment.depths)) for j in range(i + 1, len(segment.depths)))
        text = (
            f"Define a depth-to-depth relation "
            f"R_shallow on {segment.name} depths using pairs like {shallower_pairs}.\n"
            "Student A motivates the relation verbally.\n"
            "Student B writes the formal definition (R_shallow = {(x,y) ∈ A×A : x < y}) and lists at least two pairs.\n"
            "Student C checks whether the relation is transitive/symmetric/reflexive and finalises with the collaboration statement.\n"
            f"Label Student A/B/C. {ROLE_GUIDE}"
        )
        return {"text": text, "focus": "Secondary relation design."}


class MembershipSubsetTemplate(Template):
    def build(self, rng: random.Random) -> Dict[str, str]:
        segment = rng.choice(SEGMENTS)
        text = (
            f"Clarify membership vs subset using segment {segment.name}.\n"
            "Student A writes an example using ∈ (individual depth or porosity).\n"
            "Student B writes an example using ⊆ with a subset of depths or porosity values.\n"
            "Student C contrasts the two, checks notation, and signs off with the teamwork line.\n"
            f"Explicit Student A/B/C roles required. {ROLE_GUIDE}"
        )
        return {"text": text, "focus": "Membership vs subset."}


class QuantifierTemplate(Template):
    def build(self, rng: random.Random) -> Dict[str, str]:
        segment = rng.choice(SEGMENTS)
        threshold = rng.choice([0.20, 0.22, 0.25, 0.30])
        text = (
            f"Evaluate the statements for segment {segment.name}: ∃z (φ(z) ≥ {threshold:.2f}) and ∀z (φ(z) ≤ {threshold + 0.05:.2f}).\n"
            "Student A decides the truth values with reference to the data.\n"
            "Student B writes the quantifier statements formally and explains the reasoning.\n"
            "Student C confirms units/notation and wraps with the collaboration sentence.\n"
            f"Student labels mandatory. {ROLE_GUIDE}"
        )
        return {"text": text, "focus": "Quantifier checkpoint."}


class RelationCounterexampleTemplate(Template):
    def build(self, rng: random.Random) -> Dict[str, str]:
        segment = rng.choice(SEGMENTS)
        pairs = segment.ordered_pairs()
        bad_depth = segment.depths[0]
        bad_phi = segment.porosity[-1] + 0.05
        text = (
            f"Let xRy mean “at depth x, porosity equals y” for segment {segment.name}. True pairs include {', '.join(pairs)}.\n"
            f"Student A confirms one true pair. Student B constructs a counterexample such as ({bad_depth}, {bad_phi:.2f}) ∉ R and explains why.\n"
            "Student C summarises how the team records the rule R ⊆ A × B and closes with the collaboration sentence.\n"
            f"Label Student A/B/C. {ROLE_GUIDE}"
        )
        return {"text": text, "focus": "Relation definition & counterexample."}


TEMPLATES: List[Template] = [
    DomainCodomainTemplate("domain"),
    OrderedPairTemplate("pairs"),
    FunctionDiagnosisTemplate("diagnosis"),
    PolicyMemoTemplate("policy"),
    GraphOfFunctionTemplate("graph"),
    CartesianProductTemplate("axb"),
    DepthRelationTemplate("depth"),
    MembershipSubsetTemplate("membership"),
    QuantifierTemplate("quantifier"),
    RelationCounterexampleTemplate("counterexample"),
]

# Provide slight variety by duplicating some templates with different weighting
TEMPLATES += [
    OrderedPairTemplate("pairs2"),
    FunctionDiagnosisTemplate("diagnosis2"),
    QuantifierTemplate("quantifier2"),
]


def _gen_questions(group: str, members: Sequence[str]) -> Dict[str, Any]:
    seed = _seed_from_group(group, members)
    rng = random.Random(seed)
    chosen = rng.sample(TEMPLATES, 10)
    questions = []
    for idx, tpl in enumerate(chosen, start=1):
        info = tpl.build(rng)
        questions.append({
            "id": f"Q{idx:02d}",
            "text": info["text"],
            "focus": info.get("focus", tpl.name),
        })
    return {"seed": str(seed), "questions": questions, "roles": ROLE_GUIDE, "extra": EXTRA_PROMPTS}


# -----------------
# Offline grading
# -----------------
ROLE_RE = re.compile(r"Student\s+[ABC]", re.IGNORECASE)
SYMBOL_RE = re.compile(r"[∈∉⊆⊂×∀∃φϕ]")
ARROW_RE = re.compile(r"f\s*:\s*A\s*(?:→|->)\s*B", re.IGNORECASE)
PRODUCT_RE = re.compile(r"A\s*×\s*B")
PAIR_RE = re.compile(r"\(\s*\d{3,4}\s*,\s*0?\.\d+\s*\)")
CONCEPT_TERMS = [
    "domain",
    "codomain",
    "range",
    "ordered pair",
    "relation",
    "function",
    "policy",
    "duplicate",
    "cartesian",
    "quantifier",
    "∃",
    "∀",
    "subset",
]


def _soft_score_and_feedback(ans: str) -> tuple[int, str]:
    text = (ans or "").strip()
    if not text:
        return 0, "Please provide a shared answer with Student A/B/C contributions."

    length = len(text)
    base = 6 if length >= 120 else 4
    lower = text.lower()

    concept_hits = sum(1 for term in CONCEPT_TERMS if term in lower)
    concept_points = min(4, concept_hits)

    symbol_points = 0
    if SYMBOL_RE.search(text):
        symbol_points += 1
    if ARROW_RE.search(text):
        symbol_points += 1
    if PRODUCT_RE.search(text):
        symbol_points += 1
    if PAIR_RE.search(text):
        symbol_points += 1
    symbol_points = min(3, symbol_points)

    roles = {match.lower() for match in ROLE_RE.findall(text)}
    role_points = min(3, len(roles))

    score = min(10, base + concept_points + symbol_points + role_points)

    if len(roles) < 3:
        score = min(score, 6)

    if score >= 9:
        feedback = "Great teamwork evidence and clear notation."
    elif score >= 7:
        feedback = "Good job—add one more concept detail for top marks."
    elif score >= 4:
        feedback = "Add more formal notation or clarify each student’s contribution."
    else:
        feedback = "Please expand with Student A/B/C sections, notation, and policy remarks."

    return score, feedback


# -----------------
# Routes
# -----------------
@assignment_three_bp.route("/assignment-three")
def assignment_three_home():
    return render_template("assignment_three.html")


@assignment_three_bp.route("/assignment-three/api/generate", methods=["POST"])
def assignment_three_generate():
    data = request.get_json(force=True, silent=True) or {}
    group = (data.get("group") or "").strip()
    students = [
        (data.get("studentA") or "").strip(),
        (data.get("studentB") or "").strip(),
        (data.get("studentC") or "").strip(),
    ]
    if not group or any(not s for s in students):
        return jsonify({"error": "Provide group name and all three student names."}), 400
    return jsonify(_gen_questions(group, students))


@assignment_three_bp.route("/assignment-three/api/grade", methods=["POST"])
def assignment_three_grade():
    payload = request.get_json(force=True, silent=True) or {}
    group = (payload.get("group") or "").strip()
    students = [
        (payload.get("studentA") or "").strip(),
        (payload.get("studentB") or "").strip(),
        (payload.get("studentC") or "").strip(),
    ]
    qa = payload.get("qa") or []

    if not qa:
        return jsonify({"error": "Missing answers."}), 400

    if not OPENAI_API_KEY:
        total = 0
        perq = []
        for item in qa:
            score, fb = _soft_score_and_feedback(item.get("answer", ""))
            total += score
            perq.append({"id": item.get("id", "?"), "score": score, "feedback": fb})
        overall = round(total / (len(qa) * 10) * 100)
        return jsonify({
            "per_question": perq,
            "overall_pct": overall,
            "pass": overall >= PASS_THRESHOLD,
            "summary": "Offline rubric used. Ensure Student A/B/C contributions and clear notation.",
        })

    system_prompt = (
        "You grade collaborative answers about porosity-log functions. Be encouraging and LENIENT. "
        "Three students respond together: Student A (data interpreter), Student B (notation lead), Student C (quality reviewer). "
        "Rubric per question (0–10): concept accuracy 0–4, notation/units 0–3, collaboration evidence (explicit Student A/B/C) 0–3. "
        "Award ≥6 when the answer is relevant, multi-sentence, and references the porosity log. Cap at 6 if roles are missing. "
        "Return JSON {per_question:[{id,score,feedback}], overall_pct, pass, summary}. Feedback ≤1 sentence, friendly."
    )

    user_payload = {
        "group": group,
        "students": students,
        "qa": [
            {
                "id": item.get("id", "?"),
                "question": (item.get("question") or "")[:600],
                "answer": (item.get("answer") or "")[:4000],
            }
            for item in qa
        ],
    }

    try:
        content = _chat_request(MODEL_GRADING, system_prompt, user_payload)
        obj = _safe_json(content)
        perq = obj.get("per_question", [])
        cleaned = []
        total = 0
        for item, src in zip(perq, qa):
            sid = item.get("id", "?")
            score = max(0, min(10, int(item.get("score", 0))))
            answer_text = src.get("answer", "")
            roles = {m.lower() for m in ROLE_RE.findall(answer_text)}
            if len(roles) < 3:
                score = min(score, 6)
            total += score
            feedback = (item.get("feedback") or "Good effort—add more explicit role notes.").strip()
            cleaned.append({"id": sid, "score": score, "feedback": feedback})
        if not cleaned:
            raise ValueError("Empty grading response")
        overall = obj.get("overall_pct")
        if overall is None:
            overall = round(total / (len(cleaned) * 10) * 100)
        passed = bool(obj.get("pass", overall >= PASS_THRESHOLD))
        summary = obj.get("summary", "Lenient collaborative rubric applied.")
        return jsonify({
            "per_question": cleaned,
            "overall_pct": int(overall),
            "pass": passed,
            "summary": summary,
        })
    except Exception:
        total = 0
        perq = []
        for item in qa:
            score, fb = _soft_score_and_feedback(item.get("answer", ""))
            total += score
            perq.append({"id": item.get("id", "?"), "score": score, "feedback": fb})
        overall = round(total / (len(qa) * 10) * 100)
        return jsonify({
            "per_question": perq,
            "overall_pct": overall,
            "pass": overall >= PASS_THRESHOLD,
            "summary": "GPT error — offline rubric used.",
        })
