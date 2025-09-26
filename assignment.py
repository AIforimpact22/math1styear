from flask import Blueprint, render_template

assignment_bp = Blueprint ("assignment", __name__)
@assignment_bp.route("/assignment")
def assignment_home():
  return render)template("assignment.html")
