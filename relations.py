from __future__ import annotations
from flask import Blueprint, Flask, jsonify, render_template


relations_bp = Blueprint("relations", __name__)


def _build_config() -> dict:
    """Return the configuration payload used by the relations UI."""

    # --- Domain A (depths, y-axis): 10 measurements (in meters) ---
    A_depths_m = [980, 1000, 1001, 1002, 1010, 1050, 1100, 1150, 1198, 1203]

    # --- Measured relation M = {(z, phi)} ---
    M_pairs = [
        {"z": 980, "phi": 0.16},
        {"z": 1000, "phi": 0.18},
        {"z": 1001, "phi": 0.22},
        {"z": 1002, "phi": 0.21},
        {"z": 1010, "phi": 0.20},
        {"z": 1050, "phi": 0.23},
        {"z": 1100, "phi": 0.24},
        {"z": 1150, "phi": 0.20},
        {"z": 1198, "phi": 0.19},
        {"z": 1203, "phi": 0.21},
    ]

    # --- Codomain B is [0,1]. We sample ticks for the grid (x-axis). ---
    observed = sorted({p["phi"] for p in M_pairs})
    extras = [0.15, 0.17, 0.25]  # a few extra choices
    B_ticks_phi = sorted(set(observed + extras))

    return {
        "universe": {"name": "Functions & Relations — Porosity (U)"},
        "A_depths_m": A_depths_m,  # y-axis (rows)
        "B_ticks_phi": B_ticks_phi,  # x-axis (columns)
        "B_description": "[0,1] (porosity fraction)",
        "units": {"depth": "m", "phi": "fraction (0–1)"},
        "M_pairs": M_pairs,  # measurement relation M
        "notation": {"f_symbol": "ϕ", "reading": "ϕ : A → B, ϕ(z)"},
    }


@relations_bp.route("/relations")
def relations_page():
    return render_template("relations.html")


@relations_bp.route("/api/config")
def api_config():
    return jsonify(_build_config())


def create_app() -> Flask:
    """Allow running this module standalone for local debugging."""

    app = Flask(__name__, template_folder="templates", static_folder=None)
    app.register_blueprint(relations_bp)
    return app


if __name__ == "__main__":
    create_app().run(debug=True)
