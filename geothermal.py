import io
import time
from flask import Blueprint, render_template, request, Response
import matplotlib
matplotlib.use("Agg")  # headless backend for servers
import matplotlib.pyplot as plt
import numpy as np

bp = Blueprint("geothermal", __name__, template_folder="templates")

# --- helpers ---------------------------------------------------------------
def _get_float(args, name, default):
    """Safely parse a float from request args with a default fallback."""
    val = args.get(name, None)
    if val is None or val == "":
        return float(default)
    try:
        return float(val)
    except ValueError:
        return float(default)

# --- routes ----------------------------------------------------------------
@bp.route("/", methods=["GET"])
def index():
    """
    Main page: explains the math, accepts parameters, shows results + plot.
    """
    # Defaults are reasonable classroom values
    T0 = _get_float(request.args, "T0", 15.0)     # °C at the surface
    G = _get_float(request.args, "G", 25.0)       # °C/km geothermal gradient
    zmax = _get_float(request.args, "zmax", 10.0) # km plotted depth range
    zpoint = _get_float(request.args, "z", 3.0)   # km: depth to evaluate T
    Ttarget = _get_float(request.args, "T", T0 + G * zpoint)  # °C to invert for z

    # Forward evaluation: T at a chosen depth
    T_at_z = T0 + G * zpoint

    # Inverse evaluation: z for a chosen temperature (avoid division by zero)
    z_for_T = None
    if abs(G) > 1e-12:
        z_for_T = (Ttarget - T0) / G

    return render_template(
        "geothermal/index.html",
        T0=T0, G=G, zmax=zmax, zpoint=zpoint, Ttarget=Ttarget,
        T_at_z=T_at_z, z_for_T=z_for_T,
        ts=int(time.time())  # cache-buster for the plot image
    )

@bp.route("/plot.png", methods=["GET"])
def plot_png():
    """
    Render T vs depth with geological axes:
    - x-axis: Temperature T (°C), increasing to the right
    - y-axis: Depth z (km), 0 at top, increasing downward
    """
    T0 = _get_float(request.args, "T0", 15.0)
    G = _get_float(request.args, "G", 25.0)
    zmax = _get_float(request.args, "zmax", 10.0)

    # Keep the graph sensible even if a negative or tiny zmax is passed
    if zmax <= 0:
        zmax = 1.0

    # Compute the line: T(z) = T0 + G z
    z = np.linspace(0.0, zmax, 200)
    T = T0 + G * z

    fig, ax = plt.subplots(figsize=(6, 5), dpi=150)

    # Plot with T on x and z on y
    ax.plot(T, z, linewidth=2)

    # Labels & title
    ax.set_xlabel("Temperature T (°C)")
    ax.set_ylabel("Depth z (km) — 0 at surface")
    ax.set_title("Geothermal Gradient  T(z) = T₀ + G·z  (Depth increases downward)")

    # Geological convention: depth increases downward
    ax.set_ylim(0, zmax)
    ax.invert_yaxis()

    # Nice x-limits with a small margin (handles G ≈ 0)
    xmin, xmax = float(np.min(T)), float(np.max(T))
    dx = xmax - xmin
    if dx < 1e-9:
        dx = 1.0
    pad = 0.05 * dx
    ax.set_xlim(xmin - pad, xmax + pad)

    ax.grid(True, linestyle="--", alpha=0.5)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)

    resp = Response(buf.getvalue(), mimetype="image/png")
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp
