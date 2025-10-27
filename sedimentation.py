import io
import time
from flask import Blueprint, render_template, request, Response
import matplotlib
matplotlib.use("Agg")  # headless backend for servers
import matplotlib.pyplot as plt
import numpy as np

bp = Blueprint("sedimentation", __name__, template_folder="templates")

# ------------------------ translations ------------------------
TR = {
    "en": {
        "title": "Sediment Accumulation — Linear Model",
        "h1": "Constant-Rate Sediment Accumulation: h(t) = h₀ + r·t",
        "subtitle": "Time on X (years) • Thickness on Y (meters). Linear, monotone when r ≠ 0.",

        "about_h2": "About the model",
        "about_p1": "We model vertical accumulation of sediment with a constant rate:",
        "where": "where:",
        "bul_h": "h is thickness (meters)",
        "bul_h0": "h₀ is the initial thickness (meters)",
        "bul_r": "r is the deposition rate (meters per year)",
        "bul_t": "t is time (years)",
        "math_notes": (
            "Math notes: A linear function with slope r and intercept h₀. "
            "Monotone increasing if r > 0 (deposition), decreasing if r < 0 (net erosion), "
            "constant if r = 0. Inverse (when r ≠ 0): t = (H − h₀)/r."
        ),

        "inputs_h2": "Model inputs",
        "label_h0": "Initial thickness h₀ (m)",
        "label_r": "Rate r (m/yr)",
        "label_tmax": "Plot time range tₘₐₓ (yr)",
        "label_t": "Evaluate at time t (yr)",
        "label_H": "Inverse: target thickness H (m)",
        "update_btn": "Update graph & values",

        "calc_h2": "Calculated values",
        "forward_strong": "Forward (thickness at a time):",
        "forward_text": "At time t = {t} yr, h = {h} m.",
        "inverse_strong": "Inverse (time to reach a thickness):",
        "inverse_text_pos": "To reach H = {H} m, the required time is t = {t} yr.",
        "inverse_text_neg": (
            "Algebra gives t = {t} yr (negative → not reached in the future with the current r and h₀)."
        ),
        "inverse_text_r0": "Cannot compute inverse when r = 0.",
        "example_p": (
            "Example: with r = 0.002 m/yr (2 mm/yr), in 500 years "
            "h = h₀ + 0.002 × 500 = h₀ + 1 m."
        ),

        "fig_alt": "Thickness (y) vs time (x) for h(t) = h₀ + r·t",
        "figcaption": "Time on the x-axis (years). Thickness on the y-axis (meters). Plot shown for 0 ≤ t ≤ {tmax} years.",
        "tip_p": "Tip: Increasing r makes the line steeper (faster accumulation). Negative r represents net erosion, sloping downward.",

        "plot_title": "Constant-Rate Sediment Accumulation   h(t) = h₀ + r·t",
        "plot_xlabel": "Time t (years)",
        "plot_ylabel": "Sediment thickness h (m)",

        "lang_label": "Language",
        "lang_en": "English",
        "lang_hu": "Hungarian",
        "lang_code": "en",
    },
    "hu": {
        "title": "Üledék‑felhalmozódás — Lineáris modell",
        "h1": "Állandó rátájú üledék‑felhalmozódás: h(t) = h₀ + r·t",
        "subtitle": "Idő az X tengelyen (év) • Vastagság az Y tengelyen (méter). Lineáris, monoton ha r ≠ 0.",

        "about_h2": "A modellről",
        "about_p1": "Az üledék függőleges felhalmozódását állandó rátával modellezzük:",
        "where": "ahol:",
        "bul_h": "h a vastagság (méter)",
        "bul_h0": "h₀ a kezdeti vastagság (méter)",
        "bul_r": "r a lerakódási ráta (méter/év)",
        "bul_t": "t az idő (év)",
        "math_notes": (
            "Megjegyzés: Lineáris függvény, meredeksége r, tengelymetszete h₀. "
            "Monoton nő, ha r > 0 (lerakódás), csökken, ha r < 0 (erózió), "
            "állandó, ha r = 0. Inverz (r ≠ 0 esetén): t = (H − h₀)/r."
        ),

        "inputs_h2": "Bemenetek",
        "label_h0": "Kezdeti vastagság h₀ (m)",
        "label_r": "Ráta r (m/év)",
        "label_tmax": "Ábrázolt időtartomány tₘₐₓ (év)",
        "label_t": "Értékelés t időpontban (év)",
        "label_H": "Inverz: cél vastagság H (m)",
        "update_btn": "Grafikon és értékek frissítése",

        "calc_h2": "Számított értékek",
        "forward_strong": "Előre (vastagság adott időnél):",
        "forward_text": "t = {t} évnél h = {h} m.",
        "inverse_strong": "Inverz (idő egy vastagság eléréséhez):",
        "inverse_text_pos": "H = {H} m eléréséhez szükséges idő: t = {t} év.",
        "inverse_text_neg": (
            "Az algebra t = {t} évet ad (negatív → a jövőben nem érhető el a jelenlegi r és h₀ mellett)."
        ),
        "inverse_text_r0": "r = 0 esetén az inverz nem számítható.",
        "example_p": (
            "Példa: r = 0,002 m/év (2 mm/év) esetén 500 év alatt "
            "h = h₀ + 0,002 × 500 = h₀ + 1 m."
        ),

        "fig_alt": "Vastagság (y) az idő függvényében (x) h(t) = h₀ + r·t esetén",
        "figcaption": "Idő az x tengelyen (év). Vastagság az y tengelyen (m). Az ábra tartománya: 0 ≤ t ≤ {tmax} év.",
        "tip_p": "Tipp: A nagyobb r meredekebb vonalat jelent (gyorsabb felhalmozódás). A negatív r nettó eróziót jelez, lefelé lejt.",

        "plot_title": "Állandó rátájú üledék‑felhalmozódás   h(t) = h₀ + r·t",
        "plot_xlabel": "Idő t (év)",
        "plot_ylabel": "Üledékvastagság h (m)",

        "lang_label": "Nyelv",
        "lang_en": "Angol",
        "lang_hu": "Magyar",
        "lang_code": "hu",
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
@bp.route("/", methods=["GET"])
def index():
    """
    Page for constant-rate sediment accumulation: h(t) = h0 + r t
    with bilingual UI (EN/HU).
    """
    lang = _get_lang(request.args)
    tr = TR[lang]

    h0      = _get_float(request.args, "h0", 0.0)       # m  (initial thickness)
    r       = _get_float(request.args, "r", 0.002)      # m/yr (2 mm/yr)
    tmax    = _get_float(request.args, "tmax", 500.0)   # years (plot extent)
    tpoint  = _get_float(request.args, "t", 500.0)      # years (evaluate at)
    Htarget = _get_float(request.args, "H", h0 + r*tpoint)  # m (inverse target)

    # Forward: thickness at a chosen time
    h_at_t = h0 + r * tpoint

    # Inverse: time to reach a chosen thickness (if r != 0)
    t_for_H = None
    if abs(r) > 1e-12:
        t_for_H = (Htarget - h0) / r

    # Pre-format a few dynamic text lines in the chosen language
    forward_line = tr["forward_text"].format(t=round(tpoint, 3), h=round(h_at_t, 3))
    figcaption_line = tr["figcaption"].format(tmax=round(tmax, 3))

    inverse_line = None
    inverse_r0_msg = None
    if t_for_H is None:
        inverse_r0_msg = tr["inverse_text_r0"]
    else:
        if t_for_H >= 0:
            inverse_line = tr["inverse_text_pos"].format(H=round(Htarget, 3), t=round(t_for_H, 3))
        else:
            inverse_line = tr["inverse_text_neg"].format(t=round(t_for_H, 3))

    return render_template(
        "sedimentation/index.html",
        # numeric/state
        h0=h0, r=r, tmax=tmax, tpoint=tpoint, Htarget=Htarget,
        h_at_t=h_at_t, t_for_H=t_for_H,
        ts=int(time.time()),  # cache-buster for the plot image
        lang=lang,
        # texts
        tr=tr,
        forward_line=forward_line,
        inverse_line=inverse_line,
        inverse_r0_msg=inverse_r0_msg,
        figcaption_line=figcaption_line,
    )

@bp.route("/plot.png", methods=["GET"])
def plot_png():
    """
    Plot thickness vs time with bilingual axis labels & title:
      - x-axis: time t (years), increasing to the right
      - y-axis: thickness h (m), increasing upward
    """
    lang = _get_lang(request.args)
    tr = TR[lang]

    h0     = _get_float(request.args, "h0", 0.0)
    r      = _get_float(request.args, "r", 0.002)
    tmax   = _get_float(request.args, "tmax", 500.0)
    tpoint = _get_float(request.args, "t", 500.0)

    if tmax <= 0:
        tmax = 1.0

    t = np.linspace(0.0, tmax, 200)
    h = h0 + r * t

    fig, ax = plt.subplots(figsize=(6, 5), dpi=150)
    ax.plot(t, h, linewidth=2)

    # Mark the evaluation point and add guide lines (if within plot window)
    h_pt = h0 + r * tpoint
    if 0 <= tpoint <= tmax:
        ax.scatter([tpoint], [h_pt], zorder=3)
        ax.axvline(tpoint, linestyle=":", alpha=0.6)
        ax.axhline(h_pt, linestyle=":", alpha=0.6)

    ax.set_xlabel(tr["plot_xlabel"])
    ax.set_ylabel(tr["plot_ylabel"])
    ax.set_title(tr["plot_title"])
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.set_xlim(0, tmax)

    # y-limits with padding
    ymin, ymax = float(np.min(h)), float(np.max(h))
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
