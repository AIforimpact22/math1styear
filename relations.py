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
    {"id": "tuff",   "name": "Volcanic Tuff (T)",       "env": "Volcanic",   "order": 1},
    {"id": "reef",   "name": "Reef Limestone (L)",      "env": "Reef",       "order": 2},
    {"id": "marine", "name": "Marine Shale (Msh)",      "env": "Marine",     "order": 3},
    {"id": "river",  "name": "River Sandstone (R)",     "env": "Terrestrial","order": 4},
]

ENVIRONMENTS = [
    {"id": "terrestrial", "name": "Terrestrial"},
    {"id": "marine",      "name": "Marine"},
    {"id": "reef",        "name": "Reef"},
    {"id": "volcanic",    "name": "Volcanic"},
]

# -----------------------------
# Helper: ≤ pairs for stratigraphy
# -----------------------------
def _leq_pairs() -> List[Tuple[str, str]]:
    id_to_order = {b["id"]: b["order"] for b in BEDS}
    ids = [b["id"] for b in BEDS]
    pairs: List[Tuple[str,str]] = []
    for a in ids:
        for b in ids:
            if id_to_order[a] <= id_to_order[b]:
                pairs.append((a,b))
    return pairs

# -----------------------------
# SCENES (with bilingual titles & notes)
# -----------------------------
SCENES: Dict[str, Any] = {
    # Relation: R ⊆ Fossils × Beds
    "relation": {
        "short": "R ⊆ Fossils×Beds",
        "title_hu": "Reláció: R ⊆ Fosszíliák × Kőzetágyak",
        "title_en": "Relation: R ⊆ Fossils × Beds",
        "mode": "AtoB",
        "note_hu": "A reláció bármely részhalmaza az A×B Descartes‑szorzatnak. Kattints egy fosszíliára, majd egy ágyra a (a,b) pár hozzáadásához/törléséhez. Egy fosszíliához több ágy is kapcsolódhat (ezért nem feltétlen függvény).",
        "note_en": "A relation is any subset of the Cartesian product A×B. Click a fossil then a bed to toggle the pair (a,b). A fossil may relate to multiple beds or to none (so a relation need not be a function).",
        "pairs": [
            ["iguanodon", "river"],
            ["triceratops", "river"],
            ["ankylosaurus", "river"],
            ["fish", "marine"],
            ["ammonoidea", "reef"]
        ]
    },

    # Properties of relations on Beds
    "properties": {
        "short": "Relation Properties",
        "title_hu": "Reláció tulajdonságai (Kőzetágyak halmazán)",
        "title_en": "Properties of a Relation (on the set of Beds)",
        "mode": "single",
        "note_hu": "Válts a példák között: Identitás (reflexív), Szomszédos (szimmetrikus), Rétegtani ≤ (reflexív, antiszimmetrikus, tranzitív). A tulajdonságok alább automatikusan ellenőrződnek.",
        "note_en": "Switch between examples: Identity (reflexive), Adjacent (symmetric), and Stratigraphic ≤ (reflexive, antisymmetric, transitive). The properties are checked live below.",
        "relations": {
            "identity": {
                "label_hu": "Identitás (reflexív)",
                "label_en": "Identity (reflexive)",
                "pairs": [[b["id"], b["id"]] for b in BEDS]
            },
            "adjacent": {
                "label_hu": "Szomszédos (szimmetrikus)",
                "label_en": "Adjacent (symmetric)",
                "pairs": [
                    ["river","marine"], ["marine","river"],
                    ["marine","reef"],  ["reef","marine"],
                    ["tuff","reef"],    ["reef","tuff"],
                ]
            },
            "leq": {
                "label_hu": "Rétegtani ≤ (reflexív, antiszimmetrikus, tranzitív)",
                "label_en": "Stratigraphic ≤ (reflexive, antisymmetric, transitive)",
                "pairs": []  # filled below
            }
        }
    },

    # Equivalence relation on Fossils
    "equiv": {
        "short": "Equivalence (Fossils)",
        "title_hu": "Ekvivalenciareláció: azonos taxonómiai csoport (fosszíliák)",
        "title_en": "Equivalence Relation: same taxonomic group (fossils)",
        "mode": "singleFossils",
        "note_hu": "Az ekvivalencia (reflexív, szimmetrikus, tranzitív) osztályokra bontja a halmazt. Itt: Dinoszauruszok {Iguanodon, Triceratops, Ankylosaurus}, Halak {Fish}, Fejlábúak {Ammonoidea}.",
        "note_en": "An equivalence relation (reflexive, symmetric, transitive) partitions the set into classes. Here: Dinosaurs {Iguanodon, Triceratops, Ankylosaurus}, Fish {Fish}, Cephalopods {Ammonoidea}.",
        "classes": {
            "Dinosaurs":   ["iguanodon","triceratops","ankylosaurus"],
            "Fish":        ["fish"],
            "Cephalopods": ["ammonoidea"]
        }
    },

    # Partial order (≤) on Beds (stratigraphy)
    "poset": {
        "short": "Partial Order ≤ (Beds)",
        "title_hu": "Részbenrendezés (≤): rétegtani sorrend a kőzetágyakon",
        "title_en": "Partial Order (≤): stratigraphic order on beds",
        "mode": "poset",
        "note_hu": "A részbenrendezés reflexív, antiszimmetrikus és tranzitív. Itt a kor szerinti sorrend: Tuff ≤ Reef ≤ Marine ≤ River. (Itt teljes rendezés, de a fogalom általánosabb.)",
        "note_en": "A partial order is reflexive, antisymmetric, and transitive. Here we use age order: Tuff ≤ Reef ≤ Marine ≤ River. (This is a total order instance; the concept is more general.)",
    },

    # Function f: Fossils → Beds
    "function": {
        "short": "Function f: Fossils→Beds",
        "title_hu": "Függvény f: Fosszíliák → Kőzetágyak",
        "title_en": "Function f: Fossils → Beds",
        "mode": "func",
        "note_hu": "Állíts be egy f függvényt: minden fosszíliához pontosan egy ágy tartozzon. Kattints fosszíliára, majd ágyra a nyíl beállításához/cseréjéhez.",
        "note_en": "Make f a function: each fossil must map to exactly one bed. Click a fossil then a bed to set/replace the arrow.",
        "suggest": [
            ["iguanodon", "river"],
            ["triceratops", "river"],
            ["ankylosaurus", "river"],
            ["fish", "marine"],
            ["ammonoidea", "reef"]
        ]
    },

    # Injective / Surjective / Bijective (Fossils → Environments)
    "iso": {
        "short": "Injective / Surjective / Bijective",
        "title_hu": "Injektív / Szürjektív / Bijektív (Fosszíliák → Környezetek)",
        "title_en": "Injective / Surjective / Bijective (Fossils → Environments)",
        "mode": "iso",
        "note_hu": "Injektív: nincs két különböző fosszília ugyanarra a környezetre. Szürjektív: minden környezet kap előképet. Bijektív = mindkettő. Próbáld elérni a bijekciót!",
        "note_en": "Injective: no two different fossils map to the same environment. Surjective: every environment gets hit. Bijective = both. Try to achieve a bijection!",
        "suggest": [
            ["iguanodon", "terrestrial"],
            ["triceratops", "terrestrial"],
            ["ankylosaurus", "terrestrial"],
            ["fish", "marine"],
            ["ammonoidea", "reef"]
        ]
    },

    # Composition g∘f: Fossils → Beds → Environments
    "compose": {
        "short": "Composition g∘f",
        "title_hu": "Függvények összetétele g∘f: Fosszíliák → Ágyak → Környezetek",
        "title_en": "Composition g∘f: Fossils → Beds → Environments",
        "mode": "compose",
        "note_hu": "g rögzített: Ágyak → Környezetek. f szerkeszthető: Fosszíliák → Ágyak. A g∘f közvetlenül környezetet rendel minden fosszíliához.",
        "note_en": "g is fixed: Beds → Environments. You edit f: Fossils → Beds. The composition g∘f sends each fossil directly to an environment.",
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

    # Inverse function (bijective case)
    "inverse": {
        "short": "Inverse f⁻¹ (bijective)",
        "title_hu": "Inverz függvény f⁻¹ (bijekció esetén)",
        "title_en": "Inverse function f⁻¹ (when bijective)",
        "mode": "inverse",
        "note_hu": "Ha f bijektív, létezik inverze: f⁻¹. Itt 4 fosszília ↔ 4 környezet indul bijektíven; tartsd meg a bijekciót, hogy az inverz értelmezhető maradjon.",
        "note_en": "If f is bijective, it has an inverse f⁻¹. Here 4 fossils ↔ 4 environments start as a bijection; keep it bijective so the inverse remains valid.",
        "domain": ["iguanodon","fish","ammonoidea","ankylosaurus"],
        "bijection": [
            ["iguanodon",    "terrestrial"],
            ["fish",         "marine"],
            ["ammonoidea",   "reef"],
            ["ankylosaurus", "volcanic"]
        ]
    }
}

# Fill ≤ pairs
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
