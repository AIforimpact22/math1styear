from __future__ import annotations
from flask import Flask, render_template, jsonify
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

app = Flask(__name__)


@dataclass
class SetDef:
    id: str      # e.g. "I"
    name: str    # e.g. "Igneous"
    color: str   # hex
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
    universe = {
        "name": "Lithosphere Materials (U)",
        "width": 1200,
        "height": 750
    }

    sets: List[SetDef] = [
        SetDef(id="I", name="Igneous",      color="#f97316", x=0.38, y=0.54, r=0.23),
        SetDef(id="S", name="Sedimentary",  color="#60a5fa", x=0.62, y=0.54, r=0.23),
        SetDef(id="M", name="Metamorphic",  color="#34d399", x=0.50, y=0.34, r=0.23),
    ]

    elements: List[ElementDef] = [
        # Igneous
        ElementDef("basalt", "Basalt", 0.31, 0.64),
        ElementDef("granite", "Granite", 0.36, 0.62),
        ElementDef("obsidian", "Obsidian", 0.30, 0.52),
        ElementDef("rhyolite", "Rhyolite", 0.40, 0.46),
        ElementDef("diorite", "Diorite", 0.34, 0.66),
        # Sedimentary
        ElementDef("limestone", "Limestone", 0.70, 0.58),
        ElementDef("sandstone", "Sandstone", 0.66, 0.62),
        ElementDef("shale", "Shale", 0.65, 0.48),
        ElementDef("conglomerate", "Conglomerate", 0.72, 0.52),
        ElementDef("greywacke", "Greywacke", 0.63, 0.62),
        ElementDef("fossil_lime", "Fossiliferous Limestone", 0.68, 0.60),
        ElementDef("chert", "Chert", 0.68, 0.44),
        ElementDef("breccia", "Breccia", 0.66, 0.56),
        # Metamorphic
        ElementDef("marble", "Marble", 0.52, 0.26),
        ElementDef("slate", "Slate", 0.54, 0.40),
        ElementDef("gneiss", "Gneiss", 0.44, 0.28),
        ElementDef("quartzite", "Quartzite", 0.56, 0.44),
        # Cross‑category examples
        ElementDef("tuff", "Tuff (Pyroclastic)", 0.50, 0.58),  # I ∩ S
        ElementDef("migmatite", "Migmatite", 0.44, 0.42),      # I ∩ M
        ElementDef("skarn", "Skarn", 0.48, 0.38),              # I ∩ M
    ]

    return {
        "universe": universe,
        "sets": [asdict(s) for s in sets],
        "elements": [asdict(e) for e in elements]
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/default")
def api_default():
    return jsonify(default_state())


@app.route("/healthz")
def healthz():
    return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
