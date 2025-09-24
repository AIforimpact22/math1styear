from flask import Flask, render_template
from set_theory import set_theory_bp, api_default as st_api_default, api_puzzle as st_api_puzzle
from function import function_bp

def create_app():
    app = Flask(__name__)

    # --- Landing page (root) ---
    @app.route("/")
    def home():
        # Renders the base template directly; its default 'content' block shows the two big options
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
    # Set Theory UI at /sets (its own /api/... will appear under /sets/api/...,
    # but we also exposed /api/... proxies above to avoid breaking older code)
    app.register_blueprint(set_theory_bp, url_prefix="/sets")

    # Function page keeps its own URLs (/function and /function/api/puzzle)
    app.register_blueprint(function_bp)

    return app


app = create_app()

if __name__ == "__main__":
    # Visit http://localhost:5000/  → landing screen
    # Set Theory: http://localhost:5000/sets
    # Functions:  http://localhost:5000/function
    app.run(host="0.0.0.0", port=5000, debug=True)
