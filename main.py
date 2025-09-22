from flask import Flask
from set_theory import set_theory_bp

def create_app():
    app = Flask(__name__)
    app.register_blueprint(set_theory_bp, url_prefix="/")
    return app

app = create_app()

@app.route("/healthz")
def healthz():
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
