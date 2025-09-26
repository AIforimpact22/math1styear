# -*- coding: utf-8 -*-
from __future__ import annotations
import os, json, time, hashlib, random
from typing import List, Dict, Any
from flask import Blueprint, render_template, request, jsonify

assignment_bp = Blueprint("assignment", __name__)

# ------------------ Optional GPT grading config ------------------
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
MODEL_GRADING  = os.environ.get("ASSIGNMENT_GRADING_MODEL", "gpt-4o-mini")

USE_OFFICIAL = True
try:
    from openai import OpenAI  # pip install openai
except Exception:
    USE_OFFICIAL = False
import requests

def _client():
    if not OPENAI_API_KEY:
        return None
    if USE_OFFICIAL:
        return OpenAI(api_key=OPENAI_API_KEY)
    return None

def _chat_request(model: str, system_prompt: str, user_prompt: str) -> str:
    """Return assistant content (JSON string)."""
    if not OPENAI_API_KEY:
        raise RuntimeError("Missing OPENAI_API_KEY")
    if USE_OFFICIAL:
        client = _client()
        resp = client.chat.completions.create(
            model=model,
            temperature=0.4,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return resp.choices[0].message.content
    # Fallback HTTP
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"]

def _safe_json(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        t = (text or "").strip()
        if t.startswith("```"):
            t = t.strip("`")
            parts = t.split("\n", 1)
            if len(parts) == 2:
                t = parts[1]
        return json.loads(t)

# ------------------ Data & question builders ------------------
SET_LABELS = {
    "EN": {"I": "Igneous", "S": "Sedimentary", "M": "Metamorphic"},
    "HU": {"I": "Magmás",  "S": "Üledékes",   "M": "Metamorf"},
}
PAIRS = [("I","S"), ("I","M"), ("S","M")]

def lang_code(language: str) -> str:
    L = (language or "").strip().lower()
    if L.startswith("hu") or "magyar" in L:
        return "HU"
    return "EN"

# Simple, concept‑check prompts (English/Hungarian)
def Q_define_set(A: str, L: str) -> str:
    en = f"In your own words, what does set {A} ({SET_LABELS['EN'][A]}) represent in the game? Name one mineral that typically belongs to {A}."
    hu = f"Saját szavaiddal írd le, mit jelent az {A} halmaz ({SET_LABELS['HU'][A]}) a játékban! Nevezz meg egy ásványt, amely jellemzően az {A} halmazba tartozik."
    return hu if L=="HU" else en

def Q_intersection(A: str, B: str, L: str) -> str:
    en = f"Explain the intersection {A} ∩ {B}. Name one mineral you expect in {A} ∩ {B} and say why."
    hu = f"Magyarázd el a(z) {A} ∩ {B} metszetet! Nevezz meg egy ásványt, amely ide tartozhat, és indokold röviden."
    return hu if L=="HU" else en

def Q_difference(A: str, B: str, L: str) -> str:
    en = f"Explain the difference {A} \\ {B}. Give one mineral that is in {A} but not in {B}, with a short justification."
    hu = f"Magyarázd el a(z) {A} \\ {B} különbséget! Adj meg egy ásványt, amely {A}-ban benne van, de {B}-ben nincs, és indokold röviden."
    return hu if L=="HU" else en

def Q_symdiff(A: str, B: str, L: str) -> str:
    en = f"What does the symmetric difference {A} Δ {B} capture? Give one mineral included in {A} Δ {B} and one excluded; justify briefly."
    hu = f"Mit jelent a szimmetrikus különbség {A} Δ {B}? Adj meg egy ásványt, amely bekerül {A} Δ {B}-be, és egyet, amely nem; röviden indokold."
    return hu if L=="HU" else en

def Q_union(A: str, B: str, L: str) -> str:
    en = f"What does the union {A} ∪ {B} represent? Give one mineral only in {A} and one only in {B}."
    hu = f"Mit jelent az {A} ∪ {B} unió? Adj meg egy ásványt, amely csak az {A} halmazban, és egyet, amely csak a {B} halmazban szerepel."
    return hu if L=="HU" else en

def Q_triple(L: str) -> str:
    en = "What does the triple intersection I ∩ S ∩ M represent? Use Quartz as an example."
    hu = "Mit jelent az I ∩ S ∩ M hármas metszet? Használd a Kvarcot (Quartz) példaként."
    return hu if L=="HU" else en

def Q_outside(L: str) -> str:
    en = "What is the 'Outside all sets' region U \\ (I ∪ S ∪ M)? Suggest one plausible mineral/material that could be outside and explain briefly."
    hu = "Mit jelent a „Minden halmazon kívül” régió, azaz U \\ (I ∪ S ∪ M)? Javasolj egy lehetséges ásványt/anyagot, amely kívül lehet, és röviden indokold."
    return hu if L=="HU" else en

def Q_sentence_notation(A: str, B: str, L: str) -> str:
    en = f"If a mineral belongs to {B} but not {A}, write one short sentence using set notation, and name one mineral from the game you think fits."
    hu = f"Ha egy ásvány {B}-hez tartozik, de {A}-hoz nem, írj egy rövid mondatot halmaz‑jelöléssel, és nevezz meg egy szerinted ide illő ásványt a játékból."
    return hu if L=="HU" else en

def Q_compare_cap_delta(A: str, B: str, L: str) -> str:
    en = f"Compare {A} ∩ {B} and {A} Δ {B} in your own words. When would you use each to reason about minerals?"
    hu = f"Hasonlítsd össze a(z) {A} ∩ {B} és {A} Δ {B} halmazokat! Mikor használnád egyiket vagy a másikat az ásványok vizsgálatában?"
    return hu if L=="HU" else en

def build_question_set(rng: random.Random, L: str) -> List[Dict[str,str]]:
    P1 = rng.choice(PAIRS)  # intersection
    P2 = rng.choice(PAIRS)  # difference
    P3 = rng.choice(PAIRS)  # symdiff
    P4 = rng.choice(PAIRS)  # union
    P5 = rng.choice(PAIRS)  # compare
    items = [
        Q_define_set("I", L),
        Q_define_set("S", L),
        Q_define_set("M", L),
        Q_intersection(P1[0], P1[1], L),
        Q_difference(P2[0], P2[1], L),
        Q_symdiff(P3[0], P3[1], L),
        Q_union(P4[0], P4[1], L),
        Q_triple(L),
        Q_outside(L),
        Q_compare_cap_delta(P5[0], P5[1], L),
    ]
    tail = items[3:]
    rng.shuffle(tail)
    items = items[:3] + tail
    return [{"id": f"Q{i+1:02d}", "text": t} for i, t in enumerate(items)]

def _seed_from_identity(name: str, neptun: str) -> int:
    today = time.strftime("%Y-%m-%d")
    key = f"{name}|{neptun}|{today}"
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return int(h, 16) % (2**31 - 1)

def _gen_questions(name: str, neptun: str, language: str) -> Dict[str, Any]:
    L = lang_code(language)
    rng = random.Random(_seed_from_identity(name, neptun))
    return {
        "seed": str(_seed_from_identity(name, neptun)),
        "language": "Hungarian" if L=="HU" else "English",
        "questions": build_question_set(rng, L)
    }

# ------------------ Routes ------------------
@assignment_bp.route("/assignment")
def assignment_home():
    return render_template("assignment.html")

@assignment_bp.route("/assignment/api/generate", methods=["POST"])
def assignment_generate():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    neptun = (data.get("neptun") or "").strip().upper()
    language = (data.get("language") or "English").strip()
    if not name or not neptun:
        return jsonify({"error": "Missing name or Neptun code"}), 400
    return jsonify(_gen_questions(name, neptun, language))

@assignment_bp.route("/assignment/api/grade", methods=["POST"])
def assignment_grade():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    neptun = (data.get("neptun") or "").strip().upper()
    language = (data.get("language") or "English").strip()
    qa = data.get("qa") or []

    # No GPT: offline heuristic
    if not OPENAI_API_KEY or not qa:
        perq, total = [], 0
        L = lang_code(language)
        words_en = ["Igneous","Sedimentary","Metamorphic","intersection","difference","union","symmetric"]
        words_hu = ["Magmás","Üledékes","Metamorf","metszet","különbség","unió","szimmetrikus"]
        for item in qa:
            ans = (item.get("answer") or "").strip()
            base = min(10, max(0, len(ans)//160))  # ~2–5 sentences
            bonus = 0
            if any(sym in ans for sym in ["∩","∪","\\","Δ","U"]): bonus += 1
            if any(w in ans for w in (words_hu if L=="HU" else words_en)): bonus += 1
            score = max(0, min(10, base + bonus))
            total += score
            perq.append({"id": item.get("id","?"), "score": score, "feedback": "Heuristic grading (offline)."})
        overall = round(total / (len(qa) * 10) * 100) if qa else 0
        return jsonify({
            "per_question": perq,
            "overall_pct": overall,
            "pass": overall >= 70,
            "summary": "Offline heuristic result. Set OPENAI_API_KEY for rubric grading."
        })

    # GPT rubric grading
    system_prompt = (
        "You are a concise grader for short, open-ended answers about basic set relations in a geology-themed Venn diagram.\n"
        "Sets: I (Igneous), S (Sedimentary), M (Metamorphic). Relations: ∩, ∪, \\ , Δ, outside U, triple intersection.\n"
        "Accept English or Hungarian responses. Grade each answer 0–10 using: clarity (0–3), set-theory correctness (0–4), geology linkage (0–3).\n"
        "Return strict JSON: {per_question:[{id,score,feedback}], overall_pct, pass, summary}."
    )
    payload = {
        "language": language,
        "student": {"name": name, "neptun": neptun},
        "qa": [{"id": it.get("id","?"),
                "question": (it.get("question") or "")[:400],
                "answer": (it.get("answer") or "")[:4000]} for it in qa]
    }
    try:
        content = _chat_request(MODEL_GRADING, system_prompt, json.dumps(payload, ensure_ascii=False))
        obj = _safe_json(content)
        perq = obj.get("per_question", [])
        clean, total = [], 0
        for item in perq:
            sid = item.get("id","?")
            sc  = max(0, min(10, int(item.get("score", 0))))
            fb  = (item.get("feedback") or "").strip()
            total += sc
            clean.append({"id": sid, "score": sc, "feedback": fb})
        overall = obj.get("overall_pct")
        if overall is None:
            overall = round(total / (len(clean) * 10) * 100) if clean else 0
        passed = bool(obj.get("pass", overall >= 70))
        summary = obj.get("summary", "—")
        return jsonify({
            "per_question": clean,
            "overall_pct": int(overall),
            "pass": passed,
            "summary": summary
        })
    except Exception:
        # Fallback to heuristic on error
        perq, total = [], 0
        for item in qa:
            ans = (item.get("answer") or "").strip()
            base = min(10, max(0, len(ans)//160))
            bonus = 1 if any(sym in ans for sym in ["∩","∪","\\","Δ","U"]) else 0
            score = max(0, min(10, base + bonus))
            total += score
            perq.append({"id": item.get("id","?"), "score": score, "feedback": "Heuristic grading (API error)."})
        overall = round(total / (len(qa) * 10) * 100) if qa else 0
        return jsonify({
            "per_question": perq,
            "overall_pct": overall,
            "pass": overall >= 70,
            "summary": "Heuristic used due to API error."
        })
