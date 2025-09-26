from flask import Flask, render_template

# Set Theory (kept as before)
from set_theory import (
    set_theory_bp,
    api_default as st_api_default,
    api_puzzle as st_api_puzzle,
)

# Assignment 1 page (typing-based, PDF export after ≥ 70%)
from assignment import assignment_bp

# NEW: Relations & Functions (Fossils) interactive page
from relations import relations_bp


def create_app():
    app = Flask(__name__)

    # --- Landing page (root) ---
    @app.route("/")
    def home():
        # Renders the base template directly; its default 'landing' shows the tiles
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
    # We also exposed /api/... proxies above to avoid breaking older code.
    app.register_blueprint(set_theory_bp, url_prefix="/sets")

    # Assignment 1 page at /assignment
    app.register_blueprint(assignment_bp)

    # NEW: Relations & Functions (Fossils) at /relations
    # - Page route:            GET /relations
    # - Assets (JSON) route:   GET /relations/api/assets
    app.register_blueprint(relations_bp)

    return app


app = create_app()

if __name__ == "__main__":
    # Visit http://localhost:5000/       → landing screen
    # Set Theory:  http://localhost:5000/sets
    # Assignment:  http://localhost:5000/assignment
    # Relations:   http://localhost:5000/relations
    app.run(host="0.0.0.0", port=5000, debug=True)
