from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from flask import Blueprint, render_template


functions_assignment_bp = Blueprint("functions_assignment", __name__)


CONTENT_PATH = Path(__file__).parent / "content" / "functions.txt"


@dataclass(frozen=True)
class Section:
    slug: str
    heading_en: str
    heading_hu: str
    body_en: str
    body_hu: str


@dataclass(frozen=True)
class QuestionPlan:
    id: str
    prompt_en: str
    prompt_hu: str
    focus_en: str
    focus_hu: str
    ai_example_en: str | None = None
    ai_example_hu: str | None = None


def _build_sections() -> List[Section]:
    """Create bilingual context based on the provided source text."""

    raw = CONTENT_PATH.read_text(encoding="utf-8")
    # We only need selected highlights from the source document, not the full dump.
    # Splitting by lines allows us to pick the fragments we want to surface.
    lines = [line.strip() for line in raw.splitlines() if line.strip()]

    def grab(*needles: str) -> List[str]:
        picked: List[str] = []
        for needle in needles:
            for line in lines:
                if line.lower().startswith(needle.lower()):
                    picked.append(line)
                    break
        return picked

    return [
        Section(
            slug="background",
            heading_en="Background",
            heading_hu="Háttér",
            body_en=(
                "We record porosity φ at every metre depth while drilling a vertical well. "
                "To reason clearly about the measurements, we treat the well log as a mathematical "
                "function that maps depths to porosity values."
            ),
            body_hu=(
                "Függőleges kutat fúrunk, és minden egyes méteren porozitásértéket (φ) rögzítünk. "
                "A mért adatokat matematikai függvényként értelmezzük, amely a mélységet "
                "porozitásértékekhez rendeli, így pontosan tudunk következtetni."
            ),
        ),
        Section(
            slug="definitions",
            heading_en="Key definitions",
            heading_hu="Kulcsfogalmak",
            body_en=(
                "Domain A is the set of measured depths (metres), codomain B contains allowable porosity "
                "values (0 ≤ φ ≤ 1). A function φ: A → B assigns a single porosity to each depth; if one depth "
                "has two different readings, the relation is not a function."
            ),
            body_hu=(
                "Az A értelmezési tartomány a mért mélységeket (méterben) tartalmazza, míg a B céltartomány a "
                "megengedett porozitásértékeket (0 ≤ φ ≤ 1). A φ: A → B függvény minden mélységhez egyetlen "
                "porozitást rendel; ha egy mélységhez két különböző érték tartozik, akkor nem függvényről van szó."
            ),
        ),
        Section(
            slug="notation",
            heading_en="Notation cues",
            heading_hu="Jelölési emlékeztető",
            body_en=(
                "Use ordered pairs (z, φ), membership symbols (∈, ∉) and Cartesian products A × B to list "
                "possible combinations. Quantifiers ∃ and ∀ help translate geological questions into "
                "precise logical statements."
            ),
            body_hu=(
                "Használjunk rendezett párokat (z, φ), elemtagság jeleket (∈, ∉) és az A × B Descartes-szorzatot "
                "a lehetséges kombinációk felsorolásához. Az ∃ és ∀ kvantorokkal a geológiai kérdéseket pontos "
                "logikai állításokká alakíthatjuk."
            ),
        ),
    ]


def _build_questions() -> List[QuestionPlan]:
    """Create the collaborative ten-question plan."""

    return [
        QuestionPlan(
            id="Q01",
            prompt_en=(
                "AI example: Demonstrate how the porosity log can be expressed as a function by stating the "
                "domain, codomain, and one ordered pair from the measurements."
            ),
            prompt_hu=(
                "AI példa: Mutasd be, hogyan írható fel a porozitásgörbe függvényként: nevezd meg az "
                "értelmezési tartományt, a céltartományt, és adj meg egy rendezett párt a mérésből."
            ),
            focus_en="Model the well log explicitly as φ: A → B.",
            focus_hu="A kútmérés expliciten jelenjen meg φ: A → B alakban.",
            ai_example_en=(
                "AI solution: Domain A = {1198 m, 1200 m, 1203 m}; codomain B = {φ ∈ ℝ : 0 ≤ φ ≤ 1}. "
                "One measured pair is (1200, 0.24), so φ(1200) = 0.24. Since every listed depth has exactly "
                "one φ value, the relation is a function."
            ),
            ai_example_hu=(
                "AI megoldás: A tartomány A = {1198 m, 1200 m, 1203 m}; a céltartomány B = {φ ∈ ℝ : 0 ≤ φ ≤ 1}. "
                "Egy mért pár: (1200, 0,24), tehát φ(1200) = 0,24. Mivel minden mélységhez pontosan egy φ érték tartozik, "
                "a reláció függvény."
            ),
        ),
        QuestionPlan(
            id="Q02",
            prompt_en="Group task: Draft a joint glossary of the symbols f, φ, A, B, ∈, ∉, A × B in both languages.",
            prompt_hu="Csoportfeladat: Állítsatok össze közös szójegyzéket az f, φ, A, B, ∈, ∉, A × B jelekhez mindkét nyelven.",
            focus_en="Ensure consistent notation across the team notes.",
            focus_hu="Legyen egységes jelölés a csapat jegyzeteiben.",
        ),
        QuestionPlan(
            id="Q03",
            prompt_en="Analyse how to treat duplicate or noisy porosity readings at the same depth and decide a cleaning policy.",
            prompt_hu="Elemezzétek, hogyan kezeljétek a duplikált vagy zajos porozitásértékeket ugyanazon a mélységen, és döntsetek tisztítási szabályról.",
            focus_en="Connect field practice with the function test (one input → one output).",
            focus_hu="Kapcsoljátok össze a terepi gyakorlatot a függvényteszttel (egy bemenet → egy kimenet).",
        ),
        QuestionPlan(
            id="Q04",
            prompt_en="Build the relation M = {(z, φ)} from the provided measurements and explain why M ⊆ A × B.",
            prompt_hu="Állítsátok össze az M = {(z, φ)} relációt a megadott mérésekből, és magyarázzátok el, miért igaz M ⊆ A × B.",
            focus_en="Practice writing out ordered pairs with units.",
            focus_hu="Gyakoroljátok a rendezett párok felírását mértékegységekkel.",
        ),
        QuestionPlan(
            id="Q05",
            prompt_en="Select one alternative relation on depths (e.g. \"is shallower than\") and test it for reflexivity, symmetry, and transitivity.",
            prompt_hu="Válasszatok egy alternatív relációt a mélységeken (pl. „sekélyebb, mint”), és vizsgáljátok meg reflexivitás, szimmetria és tranzitivitás szempontjából.",
            focus_en="Link set-theoretic properties to geological interpretation.",
            focus_hu="Kapcsoljátok össze a halmazelméleti tulajdonságokat a geológiai értelmezéssel.",
        ),
        QuestionPlan(
            id="Q06",
            prompt_en="Translate the statement “There exists a depth with porosity ≥ 0.25” into symbolic form and discuss its geological meaning.",
            prompt_hu="Fordítsátok le szimbólumokkal a „Van olyan mélység, ahol φ ≥ 0,25” állítást, és beszéljétek meg a geológiai jelentését.",
            focus_en="Use the ∃ quantifier correctly with φ(z).",
            focus_hu="Használjátok helyesen az ∃ kvantort φ(z)-zel.",
        ),
        QuestionPlan(
            id="Q07",
            prompt_en="Do the same for the universal claim “At every depth φ ≤ 0.30” and evaluate whether the dataset supports it.",
            prompt_hu="Ugyanezt tegyétek meg az „Minden mélységben φ ≤ 0,30” univerzális állításra, és értékeljétek, hogy az adathalmaz alátámasztja-e.",
            focus_en="Coordinate the group when testing ∀ statements against the log.",
            focus_hu="Egyeztessetek a csapaton belül az ∀ állítások ellenőrzésekor.",
        ),
        QuestionPlan(
            id="Q08",
            prompt_en="Design prompts for GPT to generate two additional realistic porosity scenarios for peer groups to practise on.",
            prompt_hu="Tervezettek promptokat a GPT számára két további porozitási forgatókönyv generálásához, amelyeken más csoportok gyakorolhatnak.",
            focus_en="Emphasise collaborative prompt-writing for future automation.",
            focus_hu="Emeljétek ki a közös prompt-írást a jövőbeli automatizáláshoz.",
        ),
        QuestionPlan(
            id="Q09",
            prompt_en="Define how GPT-based grading should award points (rubric, thresholds, bilingual feedback) for this assignment.",
            prompt_hu="Határozzátok meg, hogyan pontozzon a GPT-alapú értékelés (rubrika, küszöbök, kétnyelvű visszajelzés) ehhez a feladathoz.",
            focus_en="Plan the scoring conversation with the model, mirroring Assignments 1–2.",
            focus_hu="Tervezitek meg az értékelő beszélgetést a modellel az 1–2. beadandó mintájára.",
        ),
        QuestionPlan(
            id="Q10",
            prompt_en="Summarise group roles, division of labour, and version-control strategy for submitting the joint PDF report.",
            prompt_hu="Foglaljátok össze a csoportszerepeket, a munkamegosztást és a verziókövetési stratégiát a közös PDF beadásához.",
            focus_en="Ensure collaborative accountability and clear documentation.",
            focus_hu="Biztosítsátok a közös felelősséget és az átlátható dokumentációt.",
        ),
    ]


@functions_assignment_bp.route("/assignment-3")
def assignment_three_plan():
    sections = _build_sections()
    questions = _build_questions()

    workflow = [
        (
            "Kick-off / Indítás",
            "Meet as a trio, review the background card, and agree on notation before dividing tasks.",
            "A háromfős csapat találkozik, áttekinti a háttér-összefoglalót, és megegyezik a jelölésekről a feladatmegosztás előtt.",
        ),
        (
            "Co-authoring / Közös írás",
            "Rotate the scribe role for questions Q02–Q07 so every student contributes equally.",
            "Forgassátok a jegyzetelő szerepét a Q02–Q07 feladatoknál, hogy mindenki egyenlő mértékben járuljon hozzá.",
        ),
        (
            "AI collaboration / MI-együttműködés",
            "Use GPT to expand question variants and to draft bilingual formative feedback, mirroring Assignments 1 & 2.",
            "A GPT-t használjátok további feladatváltozatok kidolgozására és kétnyelvű formatív visszajelzés tervezésére az 1. és 2. beadandó mintájára.",
        ),
        (
            "Review & grading / Ellenőrzés és értékelés",
            "Run the agreed rubric through GPT to obtain tentative scores before final human sign-off.",
            "A jóváhagyott rubrikát futtassátok le GPT-vel előzetes pontszámokért, majd közösen hagyjátok jóvá az eredményt.",
        ),
    ]

    return render_template(
        "assignment_functions.html",
        sections=sections,
        questions=questions,
        workflow=workflow,
    )
