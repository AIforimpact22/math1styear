from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Tuple
from flask import Blueprint, render_template, jsonify

relations_bp = Blueprint("relations", __name__)

# -----------------------------
# Static data (fossils, beds, environments)
# -----------------------------

FOSSILS = [
    # id, name, image (PNG)
    {"id": "iguanodon",    "name": "Iguanodon",    "img": "https://i.imgur.com/uSxSGu6.png"},
    {"id": "fish",         "name": "Fish",         "img": "https://i.imgur.com/hRPKl7l.png"},
    {"id": "triceratops",  "name": "Triceratops",  "img": "https://i.imgur.com/xVdWZvH.png"},
    {"id": "ammonoidea",   "name": "Ammonoidea",   "img": "https://i.imgur.com/556YaIo.png"},
    {"id": "ankylosaurus", "name": "Ankylosaurus", "img": "https://i.imgur.com/HPpF1BX.png"},
]

# Four simple beds with a stratigraphic order (1 = oldest, 4 = youngest)
BEDS = [
    {"id": "tuff",   "name": "Volcanic Tuff (T)",       "env": "Volcanic",  "order": 1},
    {"id": "reef",   "name": "Reef Limestone (L)",      "env": "Reef",      "order": 2},
    {"id": "marine", "name": "Marine Shale (Msh)",      "env": "Marine",    "order": 3},
    {"id": "river",  "name": "River Sandstone (R)",     "env": "Terrestrial","order": 4},
]

ENVIRONMENTS = [
    {"id": "terrestrial", "name": "Terrestrial"},
    {"id": "marine",      "name": "Marine"},
    {"id": "reef",        "name": "Reef"},
    {"id": "volcanic",    "name": "Volcanic"},
]

# -----------------------------
# Scenes (eight ideas)
# -----------------------------
SCENES: Dict[str, Any] = {
    # 1) Relation as subset of A×B (Fossils × Beds)
    "relation": {
        "title": "1) Relation R ⊆ Fossils × Beds",
        "mode": "AtoB",  # left A (fossils), right B (beds)
        "note": "A relation is any set of pairs (fossil, bed). Click a fossil then a bed to toggle a pair.",
        "pairs": [  # suggested example pairs
            ["iguanodon", "river"],
            ["triceratops", "river"],
            ["ankylosaurus", "river"],
            ["fish", "marine"],
            ["ammonoidea", "reef"]
        ]
    },

    # 2) Properties: reflexive / symmetric / antisymmetric / transitive (on one set: Beds)
    "properties": {
        "title": "2) Properties on a Relation R over Beds",
        "mode": "single",  # one set only
        "note": "Toggle between example relations on Beds: identity (reflexive), adjacent (symmetric), and stratigraphic ≤ (reflexive, antisymmetric, transitive).",
        "relations": {
            "identity": {  # Reflexive: all (b,b)
                "label": "Identity (Reflexive)",
                "pairs": [[b["id"], b["id"]] for b in BEDS]
            },
            "adjacent": {  # Symmetric example pairs
                "label": "Adjacent (Symmetric)",
                "pairs": [
                    ["river","marine"], ["marine","river"],
                    ["marine","reef"],  ["reef","marine"],
                    ["tuff","reef"],    ["reef","tuff"],
                ]
            },
            "leq": {  # ≤ by stratigraphic order (includes (b,b) self-pairs)
                "label": "Stratigraphic ≤ (Reflexive, Antisymmetric, Transitive)",
                "pairs": []
            }
        }
    },

    # 3) Equivalence relation on fossils (same taxonomic group)
    "equiv": {
        "title": "3) Equivalence: same taxonomic group on Fossils",
        "mode": "singleFossils",
        "note": "An equivalence relation partitions a set into classes. Here: Dinosaurs {Iguanodon, Triceratops, Ankylosaurus}, Fish {Fish}, Cephalopods {Ammonoidea}.",
        "classes": {
            "Dinosaurs":   ["iguanodon","triceratops","ankylosaurus"],
            "Fish":        ["fish"],
            "Cephalopods": ["ammonoidea"]
        }
    },

    # 4) Partial order (≤) on Beds
    "poset": {
        "title": "4) Partial Order on Beds: older-or-equal (≤)",
        "mode": "poset",
        "note": "A partial order is reflexive, antisymmetric, and transitive. We use stratigraphic order: Tuff ≤ Reef ≤ Marine ≤ River.",
    },

    # 5) Function f: Fossils → Beds
    "function": {
        "title": "5) Function f: Fossils → Beds",
        "mode": "func",
        "note": "Make f a function: every fossil must map to exactly one bed. Click fossil then bed to set/replace its arrow.",
        "suggest": [
            ["iguanodon", "river"],
            ["triceratops", "river"],
            ["ankylosaurus", "river"],
            ["fish", "marine"],
            ["ammonoidea", "reef"]
        ]
    },

    # 6) Injective / Surjective / Bijective (Fossils → Environments)
    "iso": {
        "title": "6) Injective / Surjective / Bijective",
        "mode": "iso",
        "note": "Map Fossils to Environments. Injection: no two fossils share the same environment. Surjection: all environments are hit. Bijective = both.",
        "suggest": [
            ["iguanodon", "terrestrial"],
            ["triceratops", "terrestrial"],
            ["ankylosaurus", "terrestrial"],
            ["fish", "marine"],
            ["ammonoidea", "reef"]
        ]
    },

    # 7) Composition g∘f: Fossils → Beds → Environments
    "compose": {
        "title": "7) Composition g∘f",
        "mode": "compose",
        "note": "We fix g: Beds → Environments, and you can edit f: Fossils → Beds. The composed map g∘f sends each fossil directly to an environment.",
        "g": [
            ["river",  "terrestrial"],
            ["marine", "marine"],
            ["reef",   "reef"],
            ["tuff",   "volcanic"]
        ],
        "f_suggest": [
            ["iguanodon", "river"],
            ["triceratops", "river"],
            ["ankylosaurus", "river"],
            ["fish", "marine"],
            ["ammonoidea", "reef"]
        ]
    },

    # 8) Inverse function (only if bijection)
    "inverse": {
        "title": "8) Inverse function f⁻¹ (bijective case)",
        "mode": "inverse",
        "note": "We restrict to 4 fossils ↔ 4 environments and start with a bijection. If mapping stays bijective, you can invert it.",
        "domain": ["iguanodon","fish","ammonoidea","ankylosaurus"],  # no triceratops here
        "bijection": [
            ["iguanodon",    "terrestrial"],
            ["fish",         "marine"],
            ["ammonoidea",   "reef"],
            ["ankylosaurus", "volcanic"]
        ]
    }
}

# Pre-compute ≤ pairs for scene 2 and 4
def _leq_pairs() -> List[Tuple[str, str]]:
    # All (a,b) with order(a) <= order(b)
    id_to_order = {b["id"]: b["order"] for b in BEDS}
    ids = [b["id"] for b in BEDS]
    pairs: List[Tuple[str,str]] = []
    for a in ids:
        for b in ids:
            if id_to_order[a] <= id_to_order[b]:
                pairs.append((a,b))
    return pairs

SCENES["properties"]["relations"]["leq"]["pairs"] = [[a,b] for (a,b) in _leq_pairs()]

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
        "scenes": SCENES
    })
