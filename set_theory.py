from __future__ import annotations
from dataclasses import dataclass, asdict, replace
from typing import List, Dict, Any, Tuple
from math import hypot
import random

from flask import Blueprint, render_template, jsonify, request

set_theory_bp = Blueprint("set_theory", __name__)

# ----------------- Models -----------------
@dataclass
class SetDef:
    id: str
    name: str
    color: str
    x: float
    y: float
    r: float

@dataclass
class ElementDef:
    id: str
    label: str
    x: float
    y: float

# ----------------- Canonical layout (solution) -----------------
def solution_state() -> Dict[str, Any]:
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
    elements: List[ElementDef] = [
        # Igneous-dominant
        ElementDef("olivine",     "Olivine",               0.31, 0.62),
        ElementDef("pyroxene",    "Pyroxene",              0.36, 0.64),
        ElementDef("plagioclase", "Plagioclase Feldspar",  0.34, 0.52),
        ElementDef("amphibole",   "Amphibole",             0.34, 0.66),
        ElementDef("biotite",     "Biotite",               0.40, 0.58),
        ElementDef("ilmenite",    "Ilmenite",              0.32, 0.56),
        # Sedimentary-dominant
        ElementDef("gypsum",      "Gypsum",                0.70, 0.54),
        ElementDef("halite",      "Halite",                0.72, 0.56),
        ElementDef("kaolinite",   "Kaolinite",             0.65, 0.48),
        ElementDef("opal",        "Opal",                  0.68, 0.52),
        ElementDef("galena",      "Galena",                0.70, 0.60),
        ElementDef("hematite",    "Hematite",              0.64, 0.50),
        # Metamorphic-dominant
        ElementDef("garnet",      "Garnet",                0.50, 0.28),
        ElementDef("kyanite",     "Kyanite",               0.46, 0.30),
        ElementDef("staurolite",  "Staurolite",            0.54, 0.34),
        ElementDef("sillimanite", "Sillimanite",           0.56, 0.30),
        ElementDef("chlorite",    "Chlorite",              0.48, 0.28),
        ElementDef("graphite",    "Graphite",              0.44, 0.32),
        # Intersections
        ElementDef("zeolite",     "Zeolite",               0.50, 0.60),  # I ∩ S
        ElementDef("serpentine",  "Serpentine",            0.43, 0.40),  # I ∩ M
        ElementDef("hornblende",  "Hornblende",            0.46, 0.38),  # I ∩ M
        ElementDef("muscovite",   "Muscovite",             0.42, 0.42),  # I ∩ M
        ElementDef("calcite",     "Calcite",               0.60, 0.46),  # S ∩ M
        ElementDef("dolomite",    "Dolomite",              0.58, 0.44),  # S ∩ M
        ElementDef("talc",        "Talc",                  0.60, 0.40),  # S ∩ M
        # Triple intersection
        ElementDef("quartz",      "Quartz",                0.50, 0.46),
    ]
    return {
        "universe": universe,
        "sets": [asdict(s) for s in sets],
        "elements": [asdict(e) for e in elements]
    }

# ----------------- Answer key -----------------
def _in_circle(ex: float, ey: float, cx: float, cy: float, r: float) -> bool:
    return hypot(ex - cx, ey - cy) <= r

def compute_answer_key(universe: Dict[str, Any],
                       sets: List[Dict[str, Any]],
                       elements: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    W = float(universe.get("width", 1200))
    H = float(universe.get("height", 750))
    S = min(W, H)
    key: Dict[str, List[str]] = {}
    for e in elements:
        ex, ey = e["x"] * W, e["y"] * H
        member_ids: List[str] = []
        for s in sets:
            cx, cy, r = s["x"] * W, s["y"] * H, s["r"] * S
            if _in_circle(ex, ey, cx, cy, r):
                member_ids.append(s["id"])
        member_ids.sort()
        key[e["id"]] = member_ids
    return key

# ----------------- Scramble puzzle -----------------
def _keep_inside(x: float, y: float, r: float) -> Tuple[float, float]:
    pad = r + 0.02
    return (min(max(x, pad), 1 - pad), min(max(y, pad), 1 - pad))

def scramble_state(sol: Dict[str, Any], seed: int | None = None) -> Dict[str, Any]:
    rng = random.Random(seed)
    universe = sol["universe"]
    sets_sol = [SetDef(**s) for s in sol["sets"]]
    elements_sol = [ElementDef(**e) for e in sol["elements"]]

    corner_targets = [(0.22, 0.22), (0.78, 0.24), (0.50, 0.80)]
    rng.shuffle(corner_targets)

    sets_scrambled: List[SetDef] = []
    for i, s in enumerate(sets_sol):
        tx, ty = corner_targets[i % len(corner_targets)]
        jx, jy = rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05)
        nx, ny = _keep_inside(tx + jx, ty + jy, s.r)
        nr = max(0.08, min(0.45, s.r * rng.uniform(0.95, 1.05)))
        sets_scrambled.append(replace(s, x=nx, y=ny, r=nr))

    elements_scrambled: List[ElementDef] = []
    for e in elements_sol:
        nx, ny = rng.uniform(0.06, 0.94), rng.uniform(0.08, 0.92)
        elements_scrambled.append(replace(e, x=nx, y=ny))

    return {
        "universe": universe,
        "sets": [asdict(s) for s in sets_scrambled],
        "elements": [asdict(e) for e in elements_scrambled]
    }

# ----------------- Routes -----------------
@set_theory_bp.route("/")
def home():
    return render_template("set_theory.html")

@set_theory_bp.route("/api/default")
def api_default():
    return jsonify(solution_state())

@set_theory_bp.route("/api/puzzle")
def api_puzzle():
    sol = solution_state()
    seed_q = request.args.get("seed")
    try:
        seed = int(seed_q) if seed_q is not None else None
    except ValueError:
        seed = None
    puzzle = scramble_state(sol, seed=seed)
    answer_key = compute_answer_key(sol["universe"], sol["sets"], sol["elements"])
    return jsonify({
        "universe": puzzle["universe"],
        "sets": puzzle["sets"],
        "elements": puzzle["elements"],
        "answer_key": answer_key,
        "solution": {"sets": sol["sets"], "elements": sol["elements"]}
    })
