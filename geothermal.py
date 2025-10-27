# geothermal.py
import io
import time
from flask import Blueprint, render_template, request, Response, url_for
import matplotlib
matplotlib.use("Agg")  # headless backend for servers
import matplotlib.pyplot as plt
import numpy as np

bp = Blueprint("geothermal", __name__)

# ---------------- i18n ----------------
def get_lang():
    lang = (request.args.get("lang") or "").lower()
    return "hu" if lang == "hu" else "en"

def T(lang):
    """Return translation dict for the selected language."""
    if lang == "hu":
        return {
            # headers / nav
            "page_title": "Geotermikus gradiens — Lineáris függvény modell",
            "back_functions": "← Függvény példák",
            "relations": "Relációk és függvények",
            "language": "Nyelv",
            "english": "Angol",
            "hungarian": "Magyar",

            # sections
            "section_plot_aria": "Geotermikus gradiens ábra",
            "fig_alt": "Hőmérséklet (x) és mélység (y, 0 a felszínen) a T(z) = T0 + G·z függvényhez",
            "fig_caption": (
                "Hőmérséklet az x-tengelyen; mélység az y-tengelyen (0 a felszínen, lefelé növekszik). "
                "A tartomány: 0 ≤ z ≤ {zmax} km."
            ),

            # panel titles
            "inputs": "Bemeneti adatok",
            "results": "Számított értékek",

            # form labels
            "label_T0": "Felszíni hőmérséklet T₀ (°C)",
            "label_G": "Gradiens G (°C/km)",
            "label_zmax": "Ábrázolt mélység tartomány zₘₐₓ (km)",
            "label_z": "Értékelés mélységen z (km)",
            "label_T": "Inverz: célhőmérséklet T (°C)",
            "update_btn": "Grafikon és értékek frissítése",

            # results strings
            "forward": "Előre:",
            "forward_text": "z = {z} km mélységnél a hőmérséklet T = {T} °C.",
            "inverse": "Inverz:",
            "inverse_ok": "T = {T} °C esetén a mélység z = {z} km.",
            "inverse_fail": "Az inverz nem számítható, ha G = 0 (nincs hőmérsékletváltozás mélységgel).",
            "note": (
                "Lineáris modell: T(z) = T₀ + G·z. Ha G ≠ 0, akkor az inverz: z = (T − T₀)/G."
            ),

            # tip section
            "tip_badge": "Tanári tipp",
            "tip_code": "T(z) = T₀ + G·z",
            "tip_text": (
                "Ez egy lineáris függvény, amely minden z mélységhez pontosan egy T hőmérsékletet rendel "
                "(átmegy a „függőleges egyenes próbán”). Próbáld módosítani a G értékét, hogy "
                "forróbb medencéket vagy hűvösebb geotermikus környezetet modellezz, vagy változtasd a T₀-t "
                "a felszíni hőmérséklet évszakos ingadozásainak szimulálására."
            ),

            # plot labels (matplotlib)
            "plt_xlabel": "Hőmérséklet T (°C)",
            "plt_ylabel": "Mélység z (km) — 0 a felszínen",
            "plt_title": "Geotermikus gradiens  T(z) = T₀ + G·z  (Mélység lefelé nő)",
        }
    # ---- English default ----
    return {
        # headers / nav
        "page_title": "Geothermal Gradient — Linear Function Model",
        "back_functions": "← Function Examples",
        "relations": "Relations & Functions",
        "language": "Language",
        "english": "English",
        "hungarian": "Hungarian",

        # sections
        "section_plot_aria": "Geothermal gradient plot",
        "fig_alt": "Temperature (x) vs Depth (y, 0 at surface) for T(z) = T0 + G·z",
        "fig_caption": (
            "Temperature on the x-axis; depth on the y-axis (0 at the surface, increasing downward). "
            "Range shown: 0 ≤ z ≤ {zmax} km."
        ),

        # panel titles
        "inputs": "Model inputs",
        "results": "Calculated values",

        # form labels
        "label_T0": "Surface temperature T₀ (°C)",
        "label_G": "Gradient G (°C/km)",
        "label_zmax": "Plot depth range zₘₐₓ (km)",
        "label_z": "Evaluate at depth z (km)",
        "label_T": "Inverse: target temperature T (°C)",
        "update_btn": "Update graph & values",

        # results strings
        "forward": "Forward:",
        "forward_text": "At depth z = {z} km, temperature is T = {T} °C.",
        "inverse": "Inverse:",
        "inverse_ok": "For T = {T} °C, the depth is z = {z} km.",
        "inverse_fail": "Cannot compute the inverse when G = 0 (no temperature change with depth).",
        "note": (
            "Linear model: T(z) = T₀ + G·z. When G ≠ 0, the inverse is z = (T − T₀)/G."
        ),

        # tip section
        "tip_badge": "Classroom tip",
        "tip_code": "T(z) = T₀ + G·z",
        "tip_text": (
            "This is a linear function from depth to temperature. Each depth z has exactly one temperature value "
            "(it passes the vertical-line test). Try changing G to compare hotter basins versus cooler geothermal "
            "regimes, or adjust T₀ to simulate seasonal surface swings."
        ),

        # plot labels (matplotlib)
        "plt_xlabel": "Temperature T (°C)",
        "plt_ylabel": "Depth z (km) — 0 at surface",
        "plt_title": "Geothermal Gradient  T(z) = T₀ + G·z  (Depth increases downward)",
    }

# -------------- helpers --------------
def _get_float(args, name, default):
    val = args.get(name)
    if val is None or val == "":
        return float(default)
    try:
        return float(val)
    except ValueError:
        return float(default)

def _url_with_lang(endpoint, **params):
    """Preserve the current ?lang in all internal links."""
    lang = get_lang()
    params["lang"] = lang
    return url_for(endpoint, **params)


def _current_page_with_lang(target_lang: str) -> str:
    """Return the current page URL but with the language switched."""
    params = request.args.to_dict(flat=True)
    params["lang"] = target_lang
    view_args = request.view_args or {}
    return url_for(request.endpoint, **view_args, **params)

# --------------- routes ---------------
@bp.route("/", methods=["GET"])
def index():
    """
    Main page: explains the math, accepts parameters, shows results + plot.
    """
    lang = get_lang()
    text = T(lang)

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
        "geothermal.html",
        # numbers
        T0=T0, G=G, zmax=zmax, zpoint=zpoint, Ttarget=Ttarget,
        T_at_z=T_at_z, z_for_T=z_for_T,
        ts=int(time.time()),
        lang_links={
            "en": _current_page_with_lang("en"),
            "hu": _current_page_with_lang("hu"),
        },
        # i18n
        t=text, lang=lang,
        # helpers for links that keep ?lang
        url_with_lang=_url_with_lang
    )

@bp.route("/plot.png", methods=["GET"])
def plot_png():
    """
    Render T vs depth with geological axes and localized labels:
      - x-axis: Temperature T (°C), increasing to the right
      - y-axis: Depth z (km), 0 at top, increasing downward
    """
    lang = get_lang()
    text = T(lang)

    T0 = _get_float(request.args, "T0", 15.0)
    G  = _get_float(request.args, "G", 25.0)
    zmax = _get_float(request.args, "zmax", 10.0)

    if zmax <= 0:
        zmax = 1.0

    z = np.linspace(0.0, zmax, 200)
    Tval = T0 + G * z

    fig, ax = plt.subplots(figsize=(6, 5), dpi=150)
    ax.plot(Tval, z, linewidth=2)

    ax.set_xlabel(text["plt_xlabel"])
    ax.set_ylabel(text["plt_ylabel"])
    ax.set_title(text["plt_title"])

    # Geological convention: depth increases downward
    ax.set_ylim(0, zmax)
    ax.invert_yaxis()

    # Nice x-limits with a small margin
    xmin, xmax = float(np.min(Tval)), float(np.max(Tval))
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
