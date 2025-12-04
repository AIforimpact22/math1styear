from flask import Blueprint, render_template


bp = Blueprint("test_page", __name__)


@bp.route("/test", methods=["GET"])
def test_page():
    """Render the test page with identification fields and set theory items."""
    return render_template("test_page.html")
