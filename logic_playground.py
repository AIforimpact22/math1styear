from __future__ import annotations
from flask import Blueprint, Flask, jsonify, render_template

logic_text_bp = Blueprint("logic_text", __name__)

def _build_config() -> dict:
    """Return UI configuration (EN/HU defaults, connectors, examples)."""
    default_en = {
        "p": "the rock is sandstone",
        "q": "it contains fossils",
        "r": "it formed in a shallow marine environment",
        "o": "the sample contains olivine",
        "y": "the sample contains pyroxene",
        "i": "the rock is igneous",
    }
    default_hu = {
        "p": "a kőzet homokkő",
        "q": "fossziliákat tartalmaz",
        "r": "sekély tengeri környezetben képződött",
        "o": "a minta olivint tartalmaz",
        "y": "a minta piroxént tartalmaz",
        "i": "a kőzet magmás",
    }
    connectors_en = {
        "NOT": "not {x}",
        "AND": "{a} and {b}",
        "OR" : "{a} or {b}",
        "IMP": "if {a}, then {b}",
        "IFF": "{a} if and only if {b}",
    }
    connectors_hu = {
        "NOT": "nem {x}",
        "AND": "{a} és {b}",
        "OR" : "{a} vagy {b}",
        "IMP": "ha {a}, akkor {b}",
        "IFF": "{a} akkor és csak akkor, ha {b}",
    }

    examples = [
        {"expr": "(p ` q) → r",
         "en": "If the rock is sandstone and it contains fossils, then it formed in a shallow marine environment.",
         "hu": "Ha a kőzet homokkő és fosszíliákat tartalmaz, akkor sekély tengeri környezetben képződött."},
        {"expr": "p ↔ q",
         "en": "The rock is sandstone iff it contains fossils.",
         "hu": "A kőzet akkor és csak akkor homokkő, ha fosszíliákat tartalmaz."},
        {"expr": ",i → (,(o ~ y))",
         "en": "If it is not igneous, then it contains neither olivine nor pyroxene.",
         "hu": "Ha nem magmás, akkor sem olivint, sem piroxént nem tartalmaz."},
    ]

    return {
        "title": "Logic → Text — Geology (EN/HU)",
        "vars": {"allowed": ["p","q","r","o","y","i"], "default_en": default_en, "default_hu": default_hu},
        "connectors": {"en": connectors_en, "hu": connectors_hu},
        "operators": {"display": ["¬","∧","∨","→","↔","(",")"], "ascii": { "NOT": ",", "AND": "`", "OR": "~" }},
        "examples": examples,
        "hints": {
            "en": "Use the keypad or type: ¬ ∧ ∨ → ↔ and variables p,q,r,o,y,i. ASCII ',', '`', '~', '->', '<->' are also accepted.",
            "hu": "Használd a gombokat vagy gépeld: ¬ ∧ ∨ → ↔ és a p,q,r,o,y,i változókat. Az ASCII ',', '`', '~', '->', '<->' is működik."
        }
    }

@logic_text_bp.route("/logic-text")
def logic_text_page():
    return render_template("logic_text.html")

@logic_text_bp.route("/logic-text/api/config")
def logic_text_config():
    return jsonify(_build_config())

def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder=None)
    app.register_blueprint(logic_text_bp)
    return app

if __name__ == "__main__":
    create_app().run(debug=True)
