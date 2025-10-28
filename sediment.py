# sediment.py  (bilingual EN/HU)
import io
import time
from flask import Blueprint, render_template, request, Response
import matplotlib
matplotlib.use("Agg")  # headless backend for servers
import matplotlib.pyplot as plt
import numpy as np

sediment_bp = Blueprint("sediment", __name__)

# ------------------------ translations ------------------------
TR = {
    "en": {
        "page_title": "Sediment Transport — Power‑Law Model",
        "nav_examples": "← Function Examples",
        "nav_relations": "Relations & Functions",

        "about_h2": "About the model",
        "about_p1": "We model sediment transport with a power law:",
        "where": "where:",
        "bul_Qs": "Qₛ is sediment transport (arbitrary units)",
        "bul_k": "k is a coefficient (material/geometry)",
        "bul_v": "v is flow velocity (m/s)",
        "bul_n": "n is an exponent (typically 2–5)",
        "math_notes": (
            "Math notes: Power‑law nonlinearity. Doubling velocity multiplies transport by 2ⁿ. "
            "Inverse (k > 0, n > 0, Qₛ ≥ 0): v = (Qₛ / k)^(1/n)."
        ),

        "inputs_h2": "Model inputs",
        "label_k": "Coefficient k",
        "label_n": "Exponent n (typ. 2–5)",
        "label_vmax": "Plot velocity range vₘₐₓ (m/s)",
        "label_v": "Evaluate at velocity v (m/s)",
        "label_Q": "Inverse: target transport Qₛ (arb. units)",
        "btn_update": "Update graph & values",

        "calc_h2": "Calculated values",
        "forward_strong": "Forward:",
        "forward_text": "at velocity v = {v} m/s → Qₛ = {Q} (arb. units).",
        "inverse_strong": "Inverse:",
        "inverse_text": "for Qₛ = {Q} → v = {v} m/s.",
        "inv_err_n": "Cannot compute inverse when n ≤ 0.",
        "inv_err_k": "Cannot compute inverse when k ≤ 0.",
        "inv_err_Q": "Cannot compute inverse for negative target Qₛ.",

        "tip_p": (
            "Power‑law model: Qₛ = k · vⁿ. Strong nonlinearity: doubling v multiplies Qₛ by 2ⁿ. "
            "With your n = {n}, doubling v multiplies Qₛ by ≈ {factor}."
        ),

        "fig_alt": "Sediment transport (Qₛ) vs flow velocity (v), with Qₛ = k·vⁿ",
        "figcaption": "Flow velocity on the x-axis (m/s). Sediment transport on the y-axis (arbitrary units). "
                      "Plot shown for 0 ≤ v ≤ {vmax}.",

        "plot_title": "Sediment transport: Qₛ = k · vⁿ",
        "plot_xlabel": "Flow velocity v (m/s)",
        "plot_ylabel": "Sediment transport Qₛ (arbitrary units)",

        "lang_label": "Language",
        "lang_en": "English",
        "lang_hu": "Hungarian",
    },
    "hu": {
        "page_title": "Üledékszállítás — Hatványfüggvény‑modell",
        "nav_examples": "← Függvénypéldák",
        "nav_relations": "Relációk és függvények",

        "about_h2": "A modellről",
        "about_p1": "Az üledékszállítást hatványfüggvénnyel írjuk le:",
        "where": "ahol:",
        "bul_Qs": "Qₛ az üledékszállítás (relatív egység)",
        "bul_k": "k egy együttható (anyag/geometria)",
        "bul_v": "v az áramlási sebesség (m/s)",
        "bul_n": "n az exponens (általában 2–5)",
        "math_notes": (
            "Megjegyzés: Erősen nemlineáris viselkedés. A sebesség megkétszerezése a szállítást 2ⁿ‑szeresére növeli. "
            "Inverz (k > 0, n > 0, Qₛ ≥ 0): v = (Qₛ / k)^(1/n)."
        ),

        "inputs_h2": "Bemenetek",
        "label_k": "Együttható k",
        "label_n": "Kitevő n (ált. 2–5)",
        "label_vmax": "Ábrázolt sebességtartomány vₘₐₓ (m/s)",
        "label_v": "Értékelés sebességnél v (m/s)",
        "label_Q": "Inverz: cél üledékszállítás Qₛ (rel. egység)",
        "btn_update": "Grafikon és értékek frissítése",

        "calc_h2": "Számított értékek",
        "forward_strong": "Előre:",
        "forward_text": "v = {v} m/s sebességnél → Qₛ = {Q} (rel. egység).",
        "inverse_strong": "Inverz:",
        "inverse_text": "Qₛ = {Q} esetén → v = {v} m/s.",
        "inv_err_n": "n ≤ 0 esetén az inverz nem számítható.",
        "inv_err_k": "k ≤ 0 esetén az inverz nem számítható.",
        "inv_err_Q": "Negatív cél Qₛ esetén az inverz nem számítható.",

        "tip_p": (
            "Hatványfüggvényes modell: Qₛ = k · vⁿ. Erősen nemlineáris: a v duplázása Qₛ‑t 2ⁿ‑szeresére növeli. "
            "Az Ön n = {n} értékével a duplázás szorzója ≈ {factor}."
        ),

        "fig_alt": "Üledékszállítás (Qₛ) az áramlási sebesség (v) függvényében, Qₛ = k·vⁿ",
        "figcaption": "Az x tengelyen az áramlási sebesség (m/s). Az y tengelyen az üledékszállítás (relatív egység). "
                      "Ábra tartománya: 0 ≤ v ≤ {vmax}.",

        "plot_title": "Üledékszállítás: Qₛ = k · vⁿ",
        "plot_xlabel": "Áramlási sebesség v (m/s)",
        "plot_ylabel": "Üledékszállítás Qₛ (relatív egység)",

        "lang_label": "Nyelv",
        "lang_en": "Angol",
        "lang_hu": "Magyar",
    },
}

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

def _get_lang(args):
    lang = (args.get("lang") or "en").lower()
    return "hu" if lang == "hu" else "en"

# ------------------------ routes -------------------------
@sediment_bp.route("/", methods=["GET"])
def index():
    """
    Sediment transport (power-law): Qs = k * v^n, bilingual UI (EN/HU).
    """
    lang = _get_lang(request.args)
    tr = TR[lang]

    k       = _get_float(request.args, "k", 1.0)     # coefficient
    n       = _get_float(request.args, "n", 3.0)     # exponent (2–5 typical)
    vmax    = _get_float(request.args, "vmax", 5.0)  # max velocity for plot (m/s)
    vpoint  = _get_float(request.args, "v", 2.0)     # evaluate at (m/s)
    Qtarget = _get_float(request.args, "Q", k * (vpoint ** n))  # inverse target

    # Forward: transport at chosen velocity
    Q_at_v = k * (vpoint ** n)

    # Inverse: velocity for a chosen transport
    v_for_Q = None
    inv_error = None
    if k > 0 and n > 0 and Qtarget >= 0:
        v_for_Q = (Qtarget / k) ** (1.0 / n)
    else:
        if n <= 0:
            inv_error = tr["inv_err_n"]
        elif k <= 0:
            inv_error = tr["inv_err_k"]
        elif Qtarget < 0:
            inv_error = tr["inv_err_Q"]

    # Sensitivity (doubling velocity factor)
    doubling_factor = 2.0 ** n

    # Pre-format lines in the chosen language
    forward_line = tr["forward_text"].format(v=round(vpoint, 3), Q=round(Q_at_v, 6))
    inverse_line = None
    if v_for_Q is not None:
        inverse_line = tr["inverse_text"].format(Q=round(Qtarget, 6), v=round(v_for_Q, 6))

    figcaption_line = tr["figcaption"].format(vmax=round(vmax, 3))
    tip_line = tr["tip_p"].format(n=round(n, 3), factor=round(doubling_factor, 3))

    return render_template(
        "sediment.html",
        # state
        lang=lang, tr=tr,
        k=k, n=n, vmax=vmax, vpoint=vpoint, Qtarget=Qtarget,
        Q_at_v=Q_at_v, v_for_Q=v_for_Q, inv_error=inv_error,
        doubling_factor=doubling_factor,
        # preformatted text
        forward_line=forward_line,
        inverse_line=inverse_line,
        figcaption_line=figcaption_line,
        tip_line=tip_line,
        ts=int(time.time())  # cache-buster for the plot image
    )

@sediment_bp.route("/plot.png", methods=["GET"])
def plot_png():
    """
    Plot sediment transport vs flow velocity with bilingual labels.
    """
    lang = _get_lang(request.args)
    tr = TR[lang]

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

    ax.set_xlabel(tr["plot_xlabel"])
    ax.set_ylabel(tr["plot_ylabel"])
    ax.set_title(tr["plot_title"])
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
