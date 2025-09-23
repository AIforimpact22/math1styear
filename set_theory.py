from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from flask import Blueprint, render_template, jsonify

set_theory_bp = Blueprint("set_theory", __name__)

@dataclass
class SetDef:
    id: str      # e.g. "I"
    name: str    # e.g. "Igneous"
    color: str   # hex color
    x: float     # normalized [0..1]
    y: float     # normalized [0..1]
    r: float     # normalized vs min(width,height)

@dataclass
class ElementDef:
    id: str
    label: str
    x: float
    y: float

def default_state() -> Dict[str, Any]:
    """
    Universe + three sets (Igneous, Sedimentary, Metamorphic).
    Elements now use a diverse list of MINERALS instead of rocks.
    Positions are normalized so the UI is responsive.
    """
    universe = {
        "name": "Lithosphere Minerals (U)",
        "width": 1200,
        "height": 750
    }

    sets: List[SetDef] = [
        SetDef(id="I", name="Igneous",      color="#f97316", x=0.38, y=0.54, r=0.23),
        SetDef(id="S", name="Sedimentary",  color="#60a5fa", x=0.62, y=0.54, r=0.23),
        SetDef(id="M", name="Metamorphic",  color="#34d399", x=0.50, y=0.34, r=0.23),
    ]

    # --- Minerals dataset (approx positions to seed interesting memberships)
    elements: List[ElementDef] = [
        # Igneous-dominant minerals (inside I)
        ElementDef("olivine",      "Olivine",               0.31, 0.62),
        ElementDef("pyroxene",     "Pyroxene",              0.36, 0.64),
        ElementDef("plagioclase",  "Plagioclase Feldspar",  0.34, 0.52),
        ElementDef("amphibole",    "Amphibole",             0.34, 0.66),
        ElementDef("biotite",      "Biotite",               0.40, 0.58),
        ElementDef("ilmenite",     "Ilmenite",              0.32, 0.56),

        # Sedimentary-dominant minerals (inside S)
        ElementDef("gypsum",       "Gypsum",                0.70, 0.54),
        ElementDef("halite",       "Halite",                0.72, 0.56),
        ElementDef("kaolinite",    "Kaolinite",             0.65, 0.48),
        ElementDef("opal",         "Opal",                  0.68, 0.52),
        ElementDef("galena",       "Galena",                0.70, 0.60),
        ElementDef("hematite",     "Hematite",              0.64, 0.50),

        # Metamorphic-dominant minerals (inside M)
        ElementDef("garnet",       "Garnet",                0.50, 0.28),
        ElementDef("kyanite",      "Kyanite",               0.46, 0.30),
        ElementDef("staurolite",   "Staurolite",            0.54, 0.34),
        ElementDef("sillimanite",  "Sillimanite",           0.56, 0.30),
        ElementDef("chlorite",     "Chlorite",              0.48, 0.28),
        ElementDef("graphite",     "Graphite",              0.44, 0.32),

        # Intersections
        # I ∩ S
        ElementDef("zeolite",      "Zeolite",               0.50, 0.60),

        # I ∩ M
        ElementDef("serpentine",   "Serpentine",            0.43, 0.40),
        ElementDef("hornblende",   "Hornblende",            0.46, 0.38),
        ElementDef("muscovite",    "Muscovite",             0.42, 0.42),

        # S ∩ M
        ElementDef("calcite",      "Calcite",               0.60, 0.46),
        ElementDef("dolomite",     "Dolomite",              0.58, 0.44),
        ElementDef("talc",         "Talc",                  0.60, 0.40),

        # I ∩ S ∩ M (triple)
        ElementDef("quartz",       "Quartz",                0.50, 0.46),
    ]

    return {
        "universe": universe,
        "sets": [asdict(s) for s in sets],
        "elements": [asdict(e) for e in elements]
    }

@set_theory_bp.route("/")
def home():
    return render_template("set_theory.html")

@set_theory_bp.route("/api/default")
def api_default():
    return jsonify(default_state())
