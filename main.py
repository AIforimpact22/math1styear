import os
from flask import Flask, render_template
from werkzeug.exceptions import HTTPException

# --- Paths: make sure Flask knows where templates/static live ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Set Theory (kept as before)
from set_theory import (
    set_theory_bp,
    api_default as st_api_default,
    api_puzzle as st_api_puzzle,
)

# Assignment 1 page (typing-based, PDF export after ≥ 70%)
from assignment import assignment_bp
from logic_assignment import logic_assignment_bp
from functions_assignment import functions_assignment_bp
from logic_playground import logic_playground_bp
from geothermal import bp as geothermal_bp
from sedimentation import bp as sedimentation_bp
from function_examples import function_examples_bp

# NEW: Relations & Functions (Fossils) interactive page
from relations import relations_bp


def create_app():
    # explicitly tell Flask the templates/static paths
    app = Flask(
        __name__,
        template_folder=TEMPLATES_DIR,
        static_folder=STATIC_DIR,
        static_url_path="/static",
    )

    # --- Landing page (root) ---
    @app.route("/")
    def home():
        # Make sure templates/index.html exists
        return render_template("index.html")

    # --- Health probe ---
    @app.route("/healthz")
    def healthz():
        return "ok", 200

    # --- Keep old Set Theory API paths so existing JS fetch('/api/...') still works ---
    # Note: The Set Theory UI itself is mounted at /sets (see blueprint below).
    @app.route("/api/default")
    def proxy_api_default():
        return st_api_default()

    @app.route("/api/puzzle")
    def proxy_api_puzzle():
        return st_api_puzzle()

    # --- Mount pages ---
    # Set Theory UI at /sets (its own /api/... appear under /sets/api/...).
    app.register_blueprint(set_theory_bp, url_prefix="/sets")

    # Assignment 1 page at /assignment
    app.register_blueprint(assignment_bp)

    # Assignment 2 (Logic) at /logic-assignment
    app.register_blueprint(logic_assignment_bp)

    # Assignment 3 (Functions collaboration) at /assignment-3
    app.register_blueprint(functions_assignment_bp)

    # Logic Playground (symbols ⇄ sentences tools) at /logic-playground
    app.register_blueprint(logic_playground_bp)

    # Function examples gallery at /function-examples
    app.register_blueprint(function_examples_bp)

    # Geothermal gradient function visualiser at /geothermal
    app.register_blueprint(geothermal_bp, url_prefix="/geothermal")

    # Sediment accumulation linear model at /sedimentation
    app.register_blueprint(sedimentation_bp, url_prefix="/sedimentation")

    # NEW: Relations & Functions (Fossils) at /relations
    # - Page route:            GET /relations
    # - Assets (JSON) route:   GET /relations/api/assets
    app.register_blueprint(relations_bp)

    # -------- Friendly error pages (so you see what's wrong locally) --------
    @app.errorhandler(Exception)
    def handle_exception(e):
        # In debug/server logs you’ll still get the traceback.
        if isinstance(e, HTTPException):
            return e  # let Flask show default HTTP errors
        # For generic 500s, render a tiny helpful page
        return (
            "<h3>Internal Server Error</h3>"
            "<p>Check the server logs for a traceback. Common causes:</p>"
            "<ul>"
            "<li>Template not found (templates/index.html or templates/relations.html)</li>"
            "<li>Blueprint imported but route renders missing template</li>"
            "<li>Wrong working directory when starting Flask</li>"
            "</ul>",
            500,
        )

    return app


app = create_app()

if __name__ == "__main__":
    # Visit http://localhost:5000/       → landing screen
    # Set Theory:  http://localhost:5000/sets
    # Assignment:  http://localhost:5000/assignment
    # Relations:   http://localhost:5000/relations
    app.run(host="0.0.0.0", port=5000, debug=True)
