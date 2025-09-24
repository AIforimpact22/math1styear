from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple
from flask import Blueprint, jsonify, render_template, request

function_bp = Blueprint("function", __name__)

# --- Static geology-themed dataset for the mapping game (D -> E) ---

@dataclass
class Item:
    id: str
    label: str

def _dataset() -> Dict[str, Any]:
    domain: List[Item] = [
        Item("S1", "Basalt (A)"),
        Item("S2", "Granite (B)"),
        Item("S3", "Limestone (C)"),
        Item("S4", "Gneiss (D)"),
        Item("S5", "Shale (E)"),
        Item("S6", "Peridotite (F)"),
    ]
    codomain: List[Item] = [
        Item("C1", "Olivine‑rich"),
        Item("C2", "Feldspar‑dominant"),
        Item("C3", "Calcite‑dominant"),
        Item("C4", "Quartz‑rich"),
        Item("C5", "Clay minerals"),
        Item("C6", "Mafic oxides"),
    ]

    # One perfectly bijective "solution" mapping (for reference)
    solution_pairs: List[Tuple[str, str]] = [
        ("S1", "C1"),  # Basalt → Olivine‑rich
        ("S2", "C2"),  # Granite → Feldspar‑dominant
        ("S3", "C3"),  # Limestone → Calcite‑dominant
        ("S4", "C4"),  # Gneiss → Quartz‑rich
        ("S5", "C5"),  # Shale → Clay minerals
        ("S6", "C6"),  # Peridotite → Mafic oxides
    ]

    # A deliberately "bad" starting mapping (not injective, not surjective, not total)
    #  - S6 is unmapped
    #  - C1 and C5 have collisions
    #  - C2, C4, C6 unused
    initial_pairs: List[Tuple[str, str]] = [
        ("S1", "C1"),
        ("S2", "C1"),
        ("S3", "C3"),
        ("S4", "C5"),
        ("S5", "C5"),
        # S6 -> None
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
    # Optional seed for future extensions; currently returns the static puzzle
    _ = request.args.get("seed")
    return jsonify(_dataset())
