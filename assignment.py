{% extends "index.html" %}
{% block page_title %}Assignment 1 — Set Theory with Minerals / Halmazelmélet ásványokkal{% endblock %}

{% block controls %}
<div class="controls" aria-label="Assignment controls">
  <a href="/" class="btn" target="_blank" rel="noopener" id="lblOpenGame">Open Set Theory Game</a>
  <button id="btnStart" class="btn">Start Assignment</button>
  <button id="btnGrade" class="btn">Check & Grade</button>
  <button id="btnPdf" class="btn" disabled>Generate PDF</button>
</div>
{% endblock %}

{% block content %}
<section class="canvas-card" aria-label="Assignment form container">
  <style>
    .assign-wrap{ padding: 14px; }
    .id-card{
      display:grid; gap:8px; background:#0f141c; border:1px solid #233040; border-radius:12px; padding:10px;
      margin-bottom: 10px;
    }
    .id-row{ display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
    .id-row label{ min-width: 140px; color:#cbd7ea; }
    .id-row input[type="text"], .id-row select{
      background:#0d1320; border:1px solid #263243; color:#e8f0ff; padding:8px 10px; border-radius:8px; width: 280px;
    }

    .rule-card{ background: var(--card); border:1px solid #233040; border-radius:14px; padding:12px; margin-bottom:10px; }
    .rule-card h3{ margin:0 0 6px; font-size:14px; color:#cbd7ea; }
    .rule-card ul{ margin:6px 0 0 18px; color:#d7e6ff; }

    .q-card{
      background:#0f141c; border:1px solid #233040; border-radius:12px; padding:12px; margin-top:10px;
    }
    .q-card h4{ margin:0 0 6px; font-size:14px; color:#cbd7ea; }
    .q-text{ color:#d7e6ff; margin: 4px 0 8px; white-space: pre-wrap; }
    .q-card textarea{
      background:#0d1320; border:1px solid #263243; color:#e8f0ff; padding:10px; border-radius:8px; width:100%;
      min-height: 110px;
    }

    .score{
      display:flex; align-items:center; gap:8px; padding:2px 6px; border-radius:10px;
      background: rgba(14,21,35,0.6); border:1px solid #223045; margin-top: 10px;
    }
    .score .bar{ width:230px; height:8px; border:1px solid #263243; background:#0e1523; border-radius:999px; overflow:hidden; }
    .score .fill{ height:100%; width:0%; background: linear-gradient(90deg, #16a34a, #22c55e); }
    .pill{ display:inline-block; padding:2px 8px; border-radius:999px; border:1px solid #223045; background:#0e1523; color:#a7b8cc; }

    .perq{ display:grid; gap:6px; margin-top:8px; }
    .perq .item{ display:flex; justify-content:space-between; gap:8px; border:1px dashed #2a394e; border-radius:10px; padding:6px 8px; }
    .good{ color:#34d399; font-weight:700; }
    .bad{ color:#ef4444; font-weight:700; }

    @media print {
      header, .controls { display:none !important; }
      body { background: #fff; }
      .q-card{ page-break-inside: avoid; }
      .rule-card{ page-break-inside: avoid; }
    }
  </style>

  <div class="assign-wrap">
    <!-- 1) Identity -->
    <div class="id-card">
      <div class="id-row">
        <label for="studentName" id="lblName">Student Name</label>
        <input type="text" id="studentName" placeholder="Your full name / Teljes név" required />
      </div>
      <div class="id-row">
        <label for="neptun" id="lblNeptun">Neptun Code</label>
        <input type="text" id="neptun" placeholder="ABC123" maxlength="6" pattern="[A-Za-z0-9]{6}" required />
      </div>
      <div class="id-row">
        <label for="language" id="lblLang">Language / Nyelv</label>
        <select id="language">
          <option value="English">English</option>
          <option value="Hungarian">Hungarian (Magyar)</option>
        </select>
      </div>
    </div>

    <!-- 2) Short instruction -->
    <div class="rule-card">
      <h3 id="instTitle">Instruction</h3>
      <ul id="instList">
        <li>Use the <strong>Set Theory Minerals Game</strong> to think about regions (∩, ∪, \, Δ, triple, outside).</li>
        <li>Answer each question in 2–5 sentences. You may write in <em>any language</em>.</li>
        <li>Click <strong>Start Assignment</strong> to load your 10 personalized questions.</li>
        <li>Click <strong>Check & Grade</strong> for instant feedback. If your score is <strong>≥ 70%</strong>, you can <strong>Generate PDF</strong> and then <strong>upload it</strong> to the University learning system under this assignment.</li>
      </ul>
    </div>

    <!-- 3) Questions -->
    <div id="questionsBox"></div>

    <!-- 4) Bottom: Grading & feedback -->
    <div class="q-card" id="gradingBox" style="display:none;">
      <h4 id="gradeTitle">Grading</h4>
      <div class="score">
        <span id="scoreText">Score: 0%</span>
        <div class="bar"><div id="scoreFill" class="fill"></div></div>
        <span id="passPill" class="pill">—</span>
      </div>
      <div class="perq" id="perQuestion"></div>
      <div class="rule-card" style="margin-top:10px;">
        <h3 id="sumTitle">Summary</h3>
        <div id="summaryText" class="q-text">—</div>
      </div>
      <div class="rule-card" style="margin-top:10px;">
        <strong id="submitNote">Submission:</strong>
        <span id="submitText">After generating your PDF, please <u>upload it to the University learning system</u> under this assignment.</span>
      </div>
    </div>
  </div>
</section>
{% endblock %}

{% block scripts %}
<script>
(() => {
  const $ = (id) => document.getElementById(id);

  const btnStart = $("btnStart");
  const btnGrade = $("btnGrade");
  const btnPdf   = $("btnPdf");
  const langSel  = $("language");

  const questionsBox = $("questionsBox");
  const gradingBox   = $("gradingBox");
  const scoreText    = $("scoreText");
  const scoreFill    = $("scoreFill");
  const passPill     = $("passPill");
  const perQuestion  = $("perQuestion");
  const summaryText  = $("summaryText");

  let currentQuestions = []; // [{id,text}]
  let gradingResult = null;

  // --- Simple UI i18n (EN/HU) for labels/instructions ---
  const I18N = {
    EN: {
      openGame: "Open Set Theory Game",
      start: "Start Assignment",
      grade: "Check & Grade",
      pdf: "Generate PDF",
      name: "Student Name",
      neptun: "Neptun Code",
      lang: "Language",
      instructionTitle: "Instruction",
      instructionList: [
        "Use the Set Theory Minerals Game to think about regions (∩, ∪, \\, Δ, triple, outside).",
        "Answer each question in 2–5 sentences. You may write in any language.",
        "Click Start Assignment to load your 10 personalized questions.",
        "Click Check & Grade for instant feedback. If your score is ≥ 70%, you can Generate PDF and then upload it to the University learning system under this assignment."
      ],
      grading: "Grading",
      summary: "Summary",
      submissionNote: "Submission:",
      submissionText: "After generating your PDF, please upload it to the University learning system under this assignment.",
      scoreLabel: (pct)=>`Score: ${pct}%`,
      pass: "PASS (≥ 70%)",
      revise: "REVISE (< 70%)",
      answerPlaceholder: "Type your answer (2–5 sentences). Any language is ok."
    },
    HU: {
      openGame: "Halmazjáték megnyitása",
      start: "Feladat indítása",
      grade: "Ellenőrzés és értékelés",
      pdf: "PDF készítése",
      name: "Hallgató neve",
      neptun: "Neptun-kód",
      lang: "Nyelv",
      instructionTitle: "Utasítás",
      instructionList: [
        "Használd a Halmazelmélet–Ásványok játékot a régiók megértéséhez (∩, ∪, \\, Δ, hármas metszet, kívül).",
        "Minden kérdésre 2–5 mondatban válaszolj. Bármely nyelven írhatsz.",
        "Kattints a Feladat indítása gombra a 10 személyre szabott kérdés betöltéséhez.",
        "Kattints az Ellenőrzés és értékelés gombra az azonnali visszajelzéshez. Ha az eredményed ≥ 70%, készíts PDF‑et, majd töltsd fel az egyetemi oktatási rendszerbe ehhez a feladathoz."
      ],
      grading: "Értékelés",
      summary: "Összegzés",
      submissionNote: "Leadás:",
      submissionText: "A PDF elkészítése után töltsd fel az egyetemi oktatási rendszerbe ehhez a feladathoz.",
      scoreLabel: (pct)=>`Pontszám: ${pct}%`,
      pass: "SIKERES (≥ 70%)",
      revise: "JAVÍTANDÓ (< 70%)",
      answerPlaceholder: "Írd meg a választ (2–5 mondat). Bármely nyelv elfogadott."
    }
  };

  function uiLangCode(){
    const v = (langSel.value || "English").toLowerCase();
    return v.startsWith("hungarian") ? "HU" : "EN";
  }

  function applyUIStrings(){
    const L = I18N[uiLangCode()];
    $("lblOpenGame").textContent = L.openGame;
    $("btnStart").textContent = L.start;
    $("btnGrade").textContent = L.grade;
    $("btnPdf").textContent   = L.pdf;

    $("lblName").textContent   = L.name;
    $("lblNeptun").textContent = L.neptun;
    $("lblLang").textContent   = "Language / Nyelv";

    $("instTitle").textContent = L.instructionTitle;
    const ul = $("instList");
    ul.innerHTML = "";
    L.instructionList.forEach(t => {
      const li = document.createElement("li"); li.innerHTML = t; ul.appendChild(li);
    });

    $("gradeTitle").textContent = L.grading;
    $("sumTitle").textContent   = L.summary;
    $("submitNote").textContent = L.submissionNote;
    $("submitText").innerHTML   = L.submissionText;

    // Update score label if already graded
    const cur = parseInt((scoreText.textContent.match(/\d+/)||[0])[0], 10) || 0;
    scoreText.textContent = L.scoreLabel(cur);

    // Update answer placeholders
    currentQuestions.forEach(q => {
      const ta = document.getElementById(`ans_${q.id}`);
      if (ta) ta.placeholder = L.answerPlaceholder;
    });
  }

  langSel.addEventListener("change", applyUIStrings);

  // Helpers
  function escapeHtml(s){ return (s||"").replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

  function renderQuestions(list){
    const L = I18N[uiLangCode()];
    questionsBox.innerHTML = "";
    list.forEach(q => {
      const card = document.createElement("div");
      card.className = "q-card";
      card.innerHTML = `
        <h4>${q.id}</h4>
        <div class="q-text">${escapeHtml(q.text)}</div>
        <textarea id="ans_${q.id}" placeholder="${escapeHtml(L.answerPlaceholder)}"></textarea>
      `;
      questionsBox.appendChild(card);
    });
    // restore autosave
    list.forEach(q => {
      const key = saveKey(q.id);
      const saved = localStorage.getItem(key);
      if (saved) {
        const ta = document.getElementById(`ans_${q.id}`);
        if (ta) ta.value = saved;
      }
    });
  }

  function autosaveWire(list){
    list.forEach(q => {
      const ta = document.getElementById(`ans_${q.id}`);
      if (!ta) return;
      ta.addEventListener("input", () => {
        localStorage.setItem(saveKey(q.id), ta.value);
      });
    });
  }

  function saveKey(qid){
    const name = ($("studentName").value || "").trim();
    const neptun = ($("neptun").value || "").trim().toUpperCase();
    const L = uiLangCode();
    return `assign1:${neptun}:${name}:${L}:${qid}`;
    // (language added so EN/HU drafts don't overwrite each other)
  }

  // Start / Generate
  btnStart.addEventListener("click", async () => {
    const name = $("studentName").value.trim();
    const neptun = $("neptun").value.trim().toUpperCase();
    const language = langSel.value;
    if (!name){ alert(uiLangCode()==="HU" ? "Add meg a nevedet!" : "Please enter your name."); return; }
    if (!/^[A-Za-z0-9]{6}$/.test(neptun)){
      alert(uiLangCode()==="HU" ? "Adj meg érvényes 6 karakteres Neptun‑kódot!" : "Please enter a valid 6‑character Neptun code.");
      return;
    }
    btnStart.disabled = true; btnStart.textContent = uiLangCode()==="HU" ? "Betöltés…" : "Loading…";
    try {
      const r = await fetch("/assignment/api/generate", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ name, neptun, language })
      });
      const data = await r.json();
      if (data.error){ alert(data.error); return; }
      currentQuestions = data.questions || [];
      renderQuestions(currentQuestions);
      autosaveWire(currentQuestions);
      gradingBox.style.display = "none";
      gradingResult = null;
      btnPdf.disabled = true;
      window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
    } catch (e){
      console.error(e);
      alert(uiLangCode()==="HU" ? "Hiba a kérdések betöltésekor." : "Could not load questions.");
    } finally {
      btnStart.disabled = false; btnStart.textContent = I18N[uiLangCode()].start;
    }
  });

  // Grade
  btnGrade.addEventListener("click", async () => {
    const name = $("studentName").value.trim();
    const neptun = $("neptun").value.trim().toUpperCase();
    const language = langSel.value;
    if (!currentQuestions.length){
      alert(uiLangCode()==="HU" ? "Előbb indítsd el a feladatot." : "Please start the assignment first.");
      return;
    }
    const qa = currentQuestions.map(q => ({
      id: q.id,
      question: q.text,
      answer: (document.getElementById(`ans_${q.id}`)?.value || "").trim()
    }));
    btnGrade.disabled = true; btnGrade.textContent = uiLangCode()==="HU" ? "Értékelés…" : "Grading…";
    try {
      const r = await fetch("/assignment/api/grade", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ name, neptun, language, qa })
      });
      const data = await r.json();
      gradingResult = data;
      showGrading(data);
      gradingBox.style.display = "block";
      window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
    } catch (e){
      console.error(e);
      alert(uiLangCode()==="HU" ? "Hiba az értékelés során." : "Grading failed.");
    } finally {
      btnGrade.disabled = false; btnGrade.textContent = I18N[uiLangCode()].grade;
    }
  });

  function showGrading(res){
    const L = I18N[uiLangCode()];
    const pct = res.overall_pct || 0;
    scoreText.textContent = L.scoreLabel(pct);
    scoreFill.style.width = `${Math.max(0,Math.min(100,pct))}%`;
    const pass = pct >= 70;
    passPill.textContent = pass ? L.pass : L.revise;
    passPill.style.color = pass ? "#a8f0c4" : "#ffb4bf";
    passPill.style.background = pass ? "#11281f" : "#2a1115";
    passPill.style.border = pass ? "1px solid #1f6f4f" : "1px solid #5a2831";

    perQuestion.innerHTML = "";
    (res.per_question || []).forEach(item => {
      const div = document.createElement("div");
      div.className = "item";
      div.innerHTML = `
        <span><strong>${item.id}</strong></span>
        <span class="${item.score>=7 ? 'good':'bad'}">${item.score}/10</span>
      `;
      perQuestion.appendChild(div);
    });
    summaryText.textContent = res.summary || "—";
    btnPdf.disabled = !pass;
  }

  // PDF (print)
  $("btnPdf").addEventListener("click", () => {
    if (!gradingResult || (gradingResult.overall_pct||0) < 70){
      alert(uiLangCode()==="HU" ? "PDF készítéséhez legalább 70% szükséges." : "You must score ≥ 70% to generate the PDF.");
      return;
    }
    const name = $("studentName").value.trim();
    const neptun = $("neptun").value.trim().toUpperCase();
    const today = new Date().toISOString().slice(0,10);
    const L = I18N[uiLangCode()];

    // Printable header
    const hdr = document.createElement("div");
    hdr.id = "printHeader";
    hdr.style.padding = "8px 16px";
    hdr.style.borderBottom = "1px solid #233040";
    hdr.style.marginBottom = "8px";
    hdr.style.fontSize = "13px";
    hdr.style.background = "#0e1523";
    hdr.style.color = "#cfe0ff";
    hdr.innerHTML = `<strong>Assignment 1 — Set Theory with Minerals / Halmazelmélet ásványokkal</strong> | `
      + `Name/Név: ${escapeHtml(name)} | Neptun: ${escapeHtml(neptun)} | Date: ${today} | `
      + `${L.scoreLabel(gradingResult.overall_pct)}<br>`
      + `<em>${L.submissionText}</em>`;
    document.body.prepend(hdr);

    const originalTitle = document.title;
    document.title = `Assignment1_${neptun}_${name.replace(/\s+/g,'_')}`;
    window.print();
    document.title = originalTitle;
    hdr.remove();
  });

  // Minor UX: uppercase Neptun as they type
  $("neptun").addEventListener("input", e => e.target.value = e.target.value.toUpperCase());

  // Initialize UI strings for default language
  applyUIStrings();
})();
</script>
{% endblock %}
