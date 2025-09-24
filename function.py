from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple, Optional
from flask import Blueprint, jsonify, render_template

function_bp = Blueprint("function", __name__)

@dataclass
class Item:
    id: str
    label: str

def _dataset() -> Dict[str, Any]:
    # Simple 4×4 mapping in geology context
    domain: List[Item] = [
        Item("S1", "Basalt"),
        Item("S2", "Granite"),
        Item("S3", "Limestone"),
        Item("S4", "Gneiss"),
    ]
    codomain: List[Item] = [
        Item("C1", "Olivine‑rich"),
        Item("C2", "Feldspar‑dominant"),
        Item("C3", "Calcite‑dominant"),
        Item("C4", "Quartz‑rich"),
    ]

    # Target solution (bijective)
    solution_pairs: List[Tuple[str, str]] = [
        ("S1", "C1"),  # Basalt → Olivine‑rich
        ("S2", "C2"),  # Granite → Feldspar‑dominant
        ("S3", "C3"),  # Limestone → Calcite‑dominant
        ("S4", "C4"),  # Gneiss → Quartz‑rich
    ]

    # Deliberately imperfect starting map (not a function, not injective)
    #   S1 → C2
    #   S2 → C2   (collision)
    #   S3 → C4
    #   S4 → None (unassigned)
    initial_pairs: List[Tuple[str, Optional[str]]] = [
        ("S1", "C2"),
        ("S2", "C2"),
        ("S3", "C4"),
        ("S4", None),
    ]

    return {
        "universe": {
            "name": "Functions in Geology (D → E)",
            "domain_name": "Rock Samples (D)",
            "codomain_name": "Mineral Signatures (E)"
        },
        "domain": [asdict(d) for d in domain],
        "codomain": [asdict(c) for c in codomain],
        "solution_pairs": solution_pairs,
        "initial_pairs": initial_pairs
    }

@function_bp.route("/function")
def function_home():
    return render_template("function.html")

@function_bp.route("/function/api/puzzle")
def function_puzzle():
    return jsonify(_dataset())
