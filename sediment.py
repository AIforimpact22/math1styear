# sediment.py
import io
import time
from flask import Blueprint, render_template, request, Response
import matplotlib

matplotlib.use("Agg")  # headless backend for servers
import matplotlib.pyplot as plt
import numpy as np

sediment_bp = Blueprint("sediment", __name__)

# ------------------------ helpers ------------------------
def _get_float(args, name, default):
    """Safely parse a float from request args with a default fallback."""
    val = args.get(name, None)
    if val is None or val == "":
        return float(default)
    try:
        return float(val)
    except ValueError:
        return float(default)

# ------------------------ routes -------------------------
@sediment_bp.route("/", methods=["GET"])
def index():
    """
    Sediment transport (power-law) page:
      Qs = k * v^n
    """
    k      = _get_float(request.args, "k", 1.0)    # coefficient
    n      = _get_float(request.args, "n", 3.0)    # exponent (2–5 typical)
    vmax   = _get_float(request.args, "vmax", 5.0) # max velocity for plot (m/s)
    vpoint = _get_float(request.args, "v", 2.0)    # evaluate at (m/s)
    Qtarget = _get_float(request.args, "Q", k * (vpoint ** n))  # inverse target

    # Forward: transport at chosen velocity
    Q_at_v = k * (vpoint ** n)

    # Inverse: velocity for a chosen transport (only when k>0, n>0, Q>=0)
    v_for_Q = None
    inv_error = None
    if k > 0 and n > 0 and Qtarget >= 0:
        v_for_Q = (Qtarget / k) ** (1.0 / n)
    else:
        if n <= 0:
            inv_error = "Cannot compute inverse when n ≤ 0."
        elif k <= 0:
            inv_error = "Cannot compute inverse when k ≤ 0."
        elif Qtarget < 0:
            inv_error = "Cannot compute inverse for negative target Qs."

    # Sensitivity (doubling velocity factor)
    doubling_factor = 2.0 ** n

    return render_template(
        "sediment.html",
        k=k, n=n, vmax=vmax, vpoint=vpoint, Qtarget=Qtarget,
        Q_at_v=Q_at_v, v_for_Q=v_for_Q, inv_error=inv_error,
        doubling_factor=doubling_factor,
        ts=int(time.time())  # cache-buster for the plot image
    )

@sediment_bp.route("/plot.png", methods=["GET"])
def plot_png():
    """
    Plot sediment transport vs flow velocity:
      - x-axis: flow velocity v (m/s)
      - y-axis: sediment transport Qs (arbitrary units)
      Qs = k * v^n
    """
    k      = _get_float(request.args, "k", 1.0)
    n      = _get_float(request.args, "n", 3.0)
    vmax   = _get_float(request.args, "vmax", 5.0)
    vpoint = _get_float(request.args, "v", 2.0)

    if vmax <= 0:
        vmax = 1.0

    v = np.linspace(0.0, vmax, 300)

    # Avoid infinities if user passes n<0 with v=0
    v_safe = v.copy()
    if n < 0:
        v_safe = np.where(v_safe <= 0, 1e-9, v_safe)

    Q = k * (v_safe ** n)

    fig, ax = plt.subplots(figsize=(6, 4), dpi=150)
    ax.plot(v, Q, linewidth=2)

    # Mark evaluation point if in range and finite
    try:
        Q_pt = k * (vpoint ** n)
    except Exception:
        Q_pt = np.nan

    if 0 <= vpoint <= vmax and np.isfinite(Q_pt):
        ax.scatter([vpoint], [Q_pt], zorder=3)
        ax.axvline(vpoint, linestyle=":", alpha=0.6)
        ax.axhline(Q_pt, linestyle=":", alpha=0.6)

    ax.set_xlabel("Flow velocity v (m/s)")
    ax.set_ylabel("Sediment transport Qₛ (arbitrary units)")
    ax.set_title("Sediment transport: Qₛ = k · vⁿ")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.set_xlim(0, vmax)

    # y-limits with padding
    ymin = float(np.nanmin(Q))
    ymax = float(np.nanmax(Q))
    if ymin >= 0:
        ymin = 0.0
    dy = ymax - ymin
    if dy < 1e-9:
        dy = 1.0
    pad = 0.05 * dy
    ax.set_ylim(ymin - pad, ymax + pad)

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)

    resp = Response(buf.getvalue(), mimetype="image/png")
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp
