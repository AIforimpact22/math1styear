from __future__ import annotations
from typing import Dict, Any, List, Tuple
from flask import Blueprint, render_template, jsonify

relations_bp = Blueprint("relations", __name__)

# ---------- Static sets: A (circles), B (squares), C (diamonds) ----------
A_SET = [{"id": f"a{i}", "name": f"a{i}"} for i in range(1, 5)]
B_SET = [{"id": f"b{i}", "name": f"b{i}", "order": i} for i in range(1, 5)]
C_SET = [{"id": f"c{i}", "name": f"c{i}"} for i in range(1, 5)]

# Helpers to prebuild standard relations on B
def _leq_pairs() -> List[Tuple[str, str]]:
    ids = [b["id"] for b in B_SET]
    id2ord = {b["id"]: b["order"] for b in B_SET}
    out: List[Tuple[str, str]] = []
    for a in ids:
        for b in ids:
            if id2ord[a] <= id2ord[b]:
                out.append((a, b))
    return out

def _identity_pairs() -> List[Tuple[str, str]]:
    return [(b["id"], b["id"]) for b in B_SET]

def _adjacent_pairs() -> List[Tuple[str, str]]:
    # b1↔b2, b2↔b3, b3↔b4 (symmetric, not reflexive)
    return [("b1","b2"),("b2","b1"),
            ("b2","b3"),("b3","b2"),
            ("b3","b4"),("b4","b3")]

DEFAULTS = {
    # Start with a small R so students add more (goal #1 asks ≥4 pairs)
    "R_pairs": [("a1","b1"), ("a2","b3")],
    # Start f empty so students must build a function
    "f_pairs": [],
    # g starts as identity B→C so composition is easy to see
    "g_pairs": [("b1","c1"), ("b2","c2"), ("b3","c3"), ("b4","c4")],
    # B↔B relation templates for properties / poset
    "B_relations": {
        "identity": _identity_pairs(),
        "adjacent": _adjacent_pairs(),
        "chain_leq": _leq_pairs()
    },
    # A↔A relation for equivalence (start as identity so they see one example works)
    "A_equiv": [(a["id"], a["id"]) for a in A_SET]
}

# ---------- Routes ----------
@relations_bp.route("/relations")
def relations_page():
    return render_template("relations.html")

@relations_bp.route("/relations/api/assets")
def relations_assets():
    return jsonify({
        "A": A_SET,
        "B": B_SET,
        "C": C_SET,
        "defaults": DEFAULTS
    })
