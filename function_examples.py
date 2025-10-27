"""Simple blueprint that showcases example functions used in the course."""

from flask import Blueprint, render_template

function_examples_bp = Blueprint(
    "function_examples", __name__, url_prefix="/function-examples"
)


@function_examples_bp.route("/", methods=["GET"])
def function_examples_index():
    """Render the function examples landing page."""
    return render_template("function_examples.html")
