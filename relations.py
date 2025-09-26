from __future__ import annotations
from typing import Dict, Any, List, Tuple
from flask import Blueprint, render_template, jsonify

relations_bp = Blueprint("relations", __name__)

# -----------------------------
# Static data (fossils, beds, environments)
# -----------------------------

FOSSILS = [
    {"id": "iguanodon",    "name": "Iguanodon",    "img": "https://i.imgur.com/uSxSGu6.png"},
    {"id": "fish",         "name": "Fish",         "img": "https://i.imgur.com/hRPKl7l.png"},
    {"id": "triceratops",  "name": "Triceratops",  "img": "https://i.imgur.com/xVdWZvH.png"},
    {"id": "ammonoidea",   "name": "Ammonoidea",   "img": "https://i.imgur.com/556YaIo.png"},
    {"id": "ankylosaurus", "name": "Ankylosaurus", "img": "https://i.imgur.com/HPpF1BX.png"},
]

# Four beds with a stratigraphic order (1 = oldest … 4 = youngest)
BEDS = [
    {"id": "tuff",   "name": "Volcanic Tuff (T)",       "env": "volcanic",   "order": 1},
    {"id": "reef",   "name": "Reef Limestone (L)",      "env": "reef",       "order": 2},
    {"id": "marine", "name": "Marine Shale (Msh)",      "env": "marine",     "order": 3},
    {"id": "river",  "name": "River Sandstone (R)",     "env": "terrestrial","order": 4},
]

ENVIRONMENTS = [
    {"id": "terrestrial", "name": "Terrestrial"},
    {"id": "marine",      "name": "Marine"},
    {"id": "reef",        "name": "Reef"},
    {"id": "volcanic",    "name": "Volcanic"},
]

# -----------------------------
# Helpers (pairs for properties)
# -----------------------------
def _leq_pairs() -> List[Tuple[str, str]]:
    # All (a,b) with order(a) <= order(b)
    id_to_order = {b["id"]: b["order"] for b in BEDS}
    ids = [b["id"] for b in BEDS]
    out: List[Tuple[str, str]] = []
    for a in ids:
        for b in ids:
            if id_to_order[a] <= id_to_order[b]:
                out.append((a, b))
    return out

def _identity_pairs() -> List[Tuple[str, str]]:
    return [(b["id"], b["id"]) for b in BEDS]

def _adjacent_pairs() -> List[Tuple[str, str]]:
    # Symmetric "neighbor" relation among beds
    return [
        ("river", "marine"), ("marine", "river"),
        ("marine", "reef"),  ("reef", "marine"),
        ("reef", "tuff"),    ("tuff", "reef"),
    ]

# -----------------------------
# Defaults for the single-view game
# -----------------------------
DEFAULTS = {
    # General relation R ⊆ Fossils×Beds (not necessarily a function)
    "R_pairs": [
        ("iguanodon", "river"),
        ("triceratops", "river"),
        ("ankylosaurus", "river"),
        ("fish", "marine"),
        ("ammonoidea", "reef"),
    ],

    # Function f: Fossils → Beds (students can edit; starts similar to R)
    "f_pairs": [
        ("iguanodon", "river"),
        ("triceratops", "river"),
        ("ankylosaurus", "river"),
        ("fish", "marine"),
        ("ammonoidea", "reef"),
    ],

    # Fixed g: Beds → Environments (used for composition)
    "g_pairs": [
        ("river",  "terrestrial"),
        ("marine", "marine"),
        ("reef",   "reef"),
        ("tuff",   "volcanic"),
    ],

    # Bed↔Bed relation choices to illustrate properties
    "beds_relations": {
        "identity": _identity_pairs(),
        "adjacent": _adjacent_pairs(),
        "leq": _leq_pairs()
    },

    # Equivalence classes on fossils (taxonomy-style)
    "equiv_classes": {
        "Dinosaurs":   ["iguanodon", "triceratops", "ankylosaurus"],
        "Fish":        ["fish"],
        "Cephalopods": ["ammonoidea"]
    }
}

# -----------------------------
# Routes
# -----------------------------
@relations_bp.route("/relations")
def page():
    return render_template("relations.html")

@relations_bp.route("/relations/api/assets")
def api_assets():
    return jsonify({
        "fossils": FOSSILS,
        "beds": BEDS,
        "envs": ENVIRONMENTS,
        "defaults": DEFAULTS
    })
