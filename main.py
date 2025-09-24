from flask import Flask
from set_theory import set_theory_bp
from function import function_bp  # NEW

def create_app():
    app = Flask(__name__)
    # Set Theory routes remain at "/" etc.
    app.register_blueprint(set_theory_bp, url_prefix="/")
    # Function routes mounted at /function and /function/api/...
    app.register_blueprint(function_bp)
    return app

app = create_app()

@app.route("/healthz")
def healthz():
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
