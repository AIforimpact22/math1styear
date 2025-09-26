{% extends "index.html" %}
{% block page_title %}Relations & Functions — Fossils (Interactive){% endblock %}

{% block controls %}
<div class="controls" aria-label="Relations controls">
  <div id="sceneTabs" class="chips"></div>
  <button id="btnReset" class="btn">Reset scene</button>
  <label class="switch btn"><input id="lockNodes" type="checkbox" /> Lock nodes</label>
  <label class="switch btn"><input id="showLabels" type="checkbox" checked /> Show labels</label>
</div>
{% endblock %}

{% block content %}
<section class="canvas-card" aria-label="Interactive canvas">
  <canvas id="stage" role="img" aria-label="Relations & Functions canvas"></canvas>
</section>

<aside>
  <div>
    <h2 id="sceneTitle">Relations &amp; Functions</h2>
    <div class="sets-top">
      <div class="badge">Dataset: <strong>Fossils • Beds • Environments</strong></div>
      <div class="tips">
        <div class="pill" style="margin:6px 0;">Tipp</div>
        <div>Húzd az objektumokat • Kattints először a forrásra, majd a célra, hogy létrehozz / törölj nyilat.</div>
        <div>Mindig alul látszik a magyarázat és az ellenőrzés.</div>
      </div>
    </div>
  </div>

  <div class="summary">
    <h2>Magyarázat &amp; Ellenőrzés</h2>
    <div id="explain" class="q-text">Válassz jelenetet fent, majd interaktívan próbáld ki a fogalmakat.</div>

    <!-- Scene 2 small selector -->
    <div id="propSwitcher" style="display:none; margin-top:8px;">
      <div class="row subhead">2) Példakapcsolat kiválasztása (R a Kőzetágyak halmazán):</div>
      <div class="chips" id="propChips"></div>
    </div>

    <div id="checks" class="rule-card" style="margin-top:10px; display:none;">
      <h3>Ellenőrzések</h3>
      <ul id="checkList" class="help-list"></ul>
    </div>
  </div>
</aside>

<section class="explain-card" aria-live="polite" aria-label="Bottom explanation">
  <div class="explain-head">
    <span class="badge">Összefoglaló</span>
  </div>
  <div id="footerMsg" class="explain-body">
    A színes nyilak a különböző hozzárendeléseket jelölik: <span style="color:#58c6ff;">R (kapcsolat)</span>,
    <span style="color:#34d399;">f</span>, <span style="color:#f59e0b;">g</span>, <span style="color:#facc15;">g∘f</span>.
  </div>
</section>
{% endblock %}

{% block scripts %}
<script>
(() => {
  // ---------------- Utilities ----------------
  const clamp = (v,a,b)=>Math.max(a,Math.min(b,v));
  const dist = (x1,y1,x2,y2)=>Math.hypot(x1-x2,y1-y2);
  const $ = (id)=>document.getElementById(id);
  const dpr = Math.max(1, window.devicePixelRatio || 1);

  // Colors for edges
  const COLORS = {
    R: "#58c6ff",   // relation pairs
    f: "#34d399",   // function f
    g: "#f59e0b",   // function g
    comp: "#facc15" // composition g∘f
  };

  // ---------------- State ----------------
  const canvas = $("stage");
  const ctx = canvas.getContext("2d");

  const state = {
    assets: null,       // { fossils, beds, envs, scenes }
    sceneKey: null,     // 'relation' | 'properties' | ...
    scene: null,        // scenes[sceneKey]
    nodes: [],          // [{id,type:'fossil'|'bed'|'env',name,img, x,y, w,h}]
    edges: [],          // [{from,to,kind:'R'|'f'|'g'|'comp'}]
    pending: null,      // pending source node id for edge add/remove
    needsDraw: true,
    propKey: "identity" // for scene 2
  };

  // ---------------- Layout helpers ----------------
  function resizeCanvas(){
    const rect = canvas.getBoundingClientRect();
    canvas.width = Math.floor(rect.width * dpr);
    canvas.height = Math.floor(rect.height * dpr);
    ctx.setTransform(dpr,0,0,dpr,0,0);
    state.needsDraw = true;
  }
  window.addEventListener("resize", resizeCanvas);

  function relayout(mode){
    // Decide column targets by mode
    const w = canvas.clientWidth, h = canvas.clientHeight;
    let cols = [];
    if (mode === "AtoB" || mode === "func" || mode === "iso"){
      cols = [0.22, 0.78];
    } else if (mode === "compose"){
      cols = [0.18, 0.50, 0.82];
    } else { // single-set scenes and poset use one band
      cols = [0.50];
    }
    const rowsFor = (n) => {
      const base = 0.18, step = (0.64)/(Math.max(1,n)-1 || 1);
      return Array.from({length:n}, (_,i)=> clamp(base + i*step, 0.12, 0.86));
    };

    // Position by type and mode
    const foss = state.nodes.filter(n => n.type==='fossil');
    const beds = state.nodes.filter(n => n.type==='bed');
    const envs = state.nodes.filter(n => n.type==='env');

    if (state.scene.mode === "compose"){
      placeColumn(foss, cols[0], rowsFor(foss.length));
      placeColumn(beds, cols[1], rowsFor(beds.length));
      placeColumn(envs, cols[2], rowsFor(envs.length));
    } else if (["AtoB","func","iso"].includes(state.scene.mode)){
      if (state.scene.mode === "iso"){ // fossils vs envs
        placeColumn(foss, cols[0], rowsFor(foss.length));
        placeColumn(envs, cols[1], rowsFor(envs.length));
        // hide beds
      } else { // fossils vs beds
        placeColumn(foss, cols[0], rowsFor(foss.length));
        placeColumn(beds, cols[1], rowsFor(beds.length));
      }
    } else if (state.scene.mode === "poset"){
      // stack by stratigraphic order (older bottom → younger top)
      const byOrder = beds.slice().sort((a,b) => a.order - b.order);
      const ys = [0.80,0.62,0.44,0.26]; // bottom to top
      byOrder.forEach((n,i)=>{ n.x = 0.50; n.y = ys[i]; });
      // center fossils/envs if any (should be none)
    } else {
      // single set: either beds or fossils centered
      if (state.sceneKey === "equiv" || state.scene.mode === "singleFossils"){
        placeCircle(foss, 0.50, 0.50, 0.32);
      } else {
        placeCircle(beds, 0.50, 0.50, 0.32);
      }
    }
    state.needsDraw = true;
  }

  function placeColumn(list, nx, nys){
    list.forEach((n, i) => { n.x = nx; n.y = nys[i] ?? 0.5; });
  }
  function placeCircle(list, cx, cy, rad){
    const n = Math.max(1, list.length);
    for (let i=0;i<list.length;i++){
      const t = (i/n) * Math.PI*2;
      list[i].x = cx + rad*Math.cos(t);
      list[i].y = cy + rad*Math.sin(t);
    }
  }

  // ---------------- Node/edge builders ----------------
  function buildNodesForScene(){
    state.nodes = [];
    const addF = (ids)=> {
      const set = new Set(ids || state.assets.fossils.map(f=>f.id));
      state.assets.fossils.forEach(f => {
        if (!ids || set.has(f.id)){
          state.nodes.push({id:f.id,type:'fossil',name:f.name,img:f.img,w:64,h:64});
        }
      });
    };
    const addB = ()=> state.assets.beds.forEach(b => state.nodes.push({id:b.id,type:'bed',name:b.name,order:b.order,w:80,h:36}));
    const addE = (ids)=> state.assets.envs.forEach(e => {
      if (!ids || ids.includes(e.id)) state.nodes.push({id:e.id,type:'env',name:e.name,w:90,h:36});
    });

    if (state.scene.mode === "compose"){
      addF(); addB(); addE();
    } else if (state.scene.mode === "iso"){
      addF(); addE();
    } else if (state.scene.mode === "func" || state.scene.mode === "AtoB"){
      addF(); addB();
    } else if (state.scene.mode === "poset" || state.scene.mode === "single"){
      addB();
    } else if (state.scene.mode === "singleFossils"){
      addF();
    } else if (state.scene.mode === "inverse"){
      addF(state.scene.domain); addE();
    }
  }

  function idNode(id){ return state.nodes.find(n => n.id===id); }

  function buildEdgesForScene(){
    state.edges = [];
    if (state.sceneKey === "relation"){
      (state.scene.pairs || []).forEach(([a,b]) => state.edges.push({from:a,to:b,kind:'R'}));
    } else if (state.sceneKey === "properties"){
      const rel = state.scene.relations[state.propKey];
      (rel.pairs || []).forEach(([a,b]) => state.edges.push({from:a,to:b,kind:'R'}));
    } else if (state.sceneKey === "equiv"){
      // connect all pairs within each equivalence class (including loops)
      const classes = state.scene.classes || {};
      Object.values(classes).forEach(ids => {
        ids.forEach(a => ids.forEach(b => state.edges.push({from:a,to:b,kind:'R'})));
      });
    } else if (state.sceneKey === "poset"){
      // Show Hasse-like edges by order + 1
      const beds = state.nodes.filter(n=>n.type==='bed').sort((a,b)=>a.order-b.order);
      for (let i=0;i<beds.length-1;i++){
        state.edges.push({from:beds[i].id, to:beds[i+1].id, kind:'R'});
      }
      // Loops (reflexive hint)
      beds.forEach(b => state.edges.push({from:b.id,to:b.id,kind:'R'}));
    } else if (state.sceneKey === "function"){
      (state.scene.suggest || []).forEach(([a,b]) => state.edges.push({from:a,to:b,kind:'f'}));
    } else if (state.sceneKey === "iso"){
      (state.scene.suggest || []).forEach(([a,e]) => state.edges.push({from:a,to:e,kind:'f'}));
    } else if (state.sceneKey === "compose"){
      (state.scene.g || []).forEach(([b,e]) => state.edges.push({from:b,to:e,kind:'g'}));
      (state.scene.f_suggest || []).forEach(([a,b]) => state.edges.push({from:a,to:b,kind:'f'}));
      buildCompositionEdges();
    } else if (state.sceneKey === "inverse"){
      (state.scene.bijection || []).forEach(([a,e]) => state.edges.push({from:a,to:e,kind:'f'}));
    }
  }

  function buildCompositionEdges(){
    // comp edges = g(f(a)) from fossils to envs
    // remove old comp first
    state.edges = state.edges.filter(e => e.kind !== 'comp');
    const f = state.edges.filter(e => e.kind==='f');
    const g = state.edges.filter(e => e.kind==='g');
    const mapF = new Map(); f.forEach(e => mapF.set(e.from, e.to));
    const mapG = new Map(); g.forEach(e => mapG.set(e.from, e.to));
    for (const [a,b] of mapF.entries()){
      const env = mapG.get(b);
      if (env) state.edges.push({from:a,to:env,kind:'comp'});
    }
  }

  // ---------------- Scene switching ----------------
  async function loadAssets(){
    const res = await fetch("/relations/api/assets");
    state.assets = await res.json();
  }

  function setScene(key){
    state.sceneKey = key;
    state.scene = state.assets.scenes[key];
    $("sceneTitle").textContent = state.scene.title;
    $("explain").textContent = state.scene.note;
    // Prop switcher visibility
    $("propSwitcher").style.display = (key === "properties") ? "block" : "none";
    // Checks box default hidden, each scene can show checks as needed
    $("checks").style.display = "none";
    buildNodesForScene();
    relayout(state.scene.mode);
    buildEdgesForScene();
    updateChecks();
    state.needsDraw = true;
  }

  // ---------------- UI: tabs & property chips ----------------
  function buildTabs(){
    const tabs = $("sceneTabs"); tabs.innerHTML = "";
    const order = ["relation","properties","equiv","poset","function","iso","compose","inverse"];
    order.forEach(k => {
      const chip = document.createElement("div");
      chip.className = "chip";
      chip.textContent = state.assets.scenes[k].title.split(") ")[0] + ")"; // "1)" etc.
      chip.title = state.assets.scenes[k].title;
      chip.addEventListener("click", ()=> {
        document.querySelectorAll("#sceneTabs .chip").forEach(c=>c.classList.remove("selected"));
        chip.classList.add("selected");
        setScene(k);
      });
      tabs.appendChild(chip);
      if (!state.sceneKey) chip.classList.add("selected");
    });
  }

  function buildPropChips(){
    const box = $("propChips"); box.innerHTML = "";
    const rels = state.assets.scenes.properties.relations;
    Object.keys(rels).forEach(key => {
      const chip = document.createElement("div");
      chip.className = "chip";
      chip.textContent = rels[key].label;
      chip.addEventListener("click", () => {
        document.querySelectorAll("#propChips .chip").forEach(c=>c.classList.remove("selected"));
        chip.classList.add("selected");
        state.propKey = key;
        setScene("properties");
      });
      box.appendChild(chip);
      if (key === state.propKey) chip.classList.add("selected");
    });
  }

  // ---------------- Interaction ----------------
  let drag = null;

  function pickNode(px,py){
    // Images (fossils) ~32px radius; others rectangular chips
    for (let i=state.nodes.length-1;i>=0;i--){
      const n = state.nodes[i];
      const x = n.x*canvas.clientWidth, y = n.y*canvas.clientHeight;
      if (n.type === 'fossil'){
        if (dist(px,py,x,y) <= 36) return n;
      } else {
        // rectangle
        const w= n.w, h=n.h;
        if (px>=x-w/2 && px<=x+w/2 && py>=y-h/2 && py<=y+h/2) return n;
      }
    }
    return null;
  }

  canvas.addEventListener("pointerdown", (ev) => {
    const rect = canvas.getBoundingClientRect();
    const x = ev.clientX - rect.left, y = ev.clientY - rect.top;
    const n = pickNode(x,y);
    if (!n) { state.pending = null; return; }

    // Edge-adding logic (by scene)
    const lock = $("lockNodes").checked;
    const connectable = ["relation","function","iso","compose","inverse"].includes(state.sceneKey);

    if (connectable){
      if (!state.pending){
        // choose a valid source type per scene
        if (state.sceneKey === "relation" || state.sceneKey === "function") {
          if (n.type==='fossil') state.pending = n.id;
        } else if (state.sceneKey === "iso" || state.sceneKey === "inverse" || state.sceneKey === "compose"){
          if (n.type==='fossil') state.pending = n.id;
        }
      } else {
        // complete with a valid target
        let ok=false, kind='R';
        if (state.sceneKey === "relation" && n.type==='bed'){ kind='R'; ok=true; }
        if (state.sceneKey === "function" && n.type==='bed'){ kind='f'; ok=true; }
        if (state.sceneKey === "iso" && n.type==='env'){ kind='f'; ok=true; }
        if (state.sceneKey === "inverse" && n.type==='env'){ kind='f'; ok=true; }
        if (state.sceneKey === "compose" && n.type==='bed'){ kind='f'; ok=true; }

        if (ok){
          toggleEdge(state.pending, n.id, kind);
          if (state.sceneKey === "compose") buildCompositionEdges();
          updateChecks();
          state.needsDraw = true;
        }
        state.pending = null;
      }
    }

    // Dragging
    if (!lock){
      drag = { id:n.id, dx: n.x*canvas.clientWidth - x, dy: n.y*canvas.clientHeight - y };
    }
  });

  window.addEventListener("pointermove", (ev) => {
    if (!drag) return;
    const rect = canvas.getBoundingClientRect();
    const x = ev.clientX - rect.left, y = ev.clientY - rect.top;
    const n = idNode(drag.id);
    if (!n) return;
    const nx = clamp((x + drag.dx)/canvas.clientWidth, 0.06, 0.94);
    const ny = clamp((y + drag.dy)/canvas.clientHeight, 0.08, 0.92);
    n.x = nx; n.y = ny;
    state.needsDraw = true;
  });
  window.addEventListener("pointerup", ()=> drag=null);

  function toggleEdge(from,to,kind){
    // For functions, replace existing outgoing from 'from'
    if (kind==='f'){
      state.edges = state.edges.filter(e => !(e.kind==='f' && e.from===from));
      state.edges.push({from,to,kind:'f'});
    } else {
      // relation R: toggle if exists
      const idx = state.edges.findIndex(e => e.kind==='R' && e.from===from && e.to===to);
      if (idx>=0) state.edges.splice(idx,1); else state.edges.push({from,to,kind:'R'});
    }
  }

  // ---------------- Checks per scene ----------------
  function updateChecks(){
    const list = $("checkList");
    list.innerHTML = "";
    $("checks").style.display = "none";

    if (state.sceneKey === "properties"){
      $("checks").style.display = "block";
      const pairs = state.edges.filter(e=>e.kind==='R').map(e=>[e.from,e.to]);
      const ids = state.nodes.filter(n=>n.type==='bed').map(n=>n.id);
      // Tests
      const isReflexive = ids.every(a => pairs.find(p => p[0]===a && p[1]===a));
      const isSym = pairs.every(([a,b]) => pairs.find(p => p[0]===b && p[1]===a));
      const isAnti = pairs.every(([a,b]) => (a===b) || !pairs.find(p => p[0]===b && p[1]===a));
      // Transitive (simple O(n^3))
      let isTrans = true;
      for (const [a,b] of pairs){
        for (const [c,d] of pairs){
          if (b===c){
            if (!pairs.find(p => p[0]===a && p[1]===d)) { isTrans=false; break; }
          }
        }
        if (!isTrans) break;
      }
      addCheck(list, "Reflexív", isReflexive);
      addCheck(list, "Szimmetrikus", isSym);
      addCheck(list, "Antiszimmetrikus", isAnti);
      addCheck(list, "Tranzitív", isTrans);
    }

    if (state.sceneKey === "function"){
      $("checks").style.display = "block";
      const fossils = state.nodes.filter(n=>n.type==='fossil').map(n=>n.id);
      const beds = state.nodes.filter(n=>n.type==='bed').map(n=>n.id);
      const f = state.edges.filter(e=>e.kind==='f');
      const outCount = new Map(); fossils.forEach(a=>outCount.set(a,0));
      const inCount = new Map();  beds.forEach(b=>inCount.set(b,0));
      f.forEach(e => { outCount.set(e.from, (outCount.get(e.from)||0)+1); inCount.set(e.to, (inCount.get(e.to)||0)+1); });
      const totalSet = fossils.every(a => (outCount.get(a)||0)===1);
      const injective = beds.every(b => (inCount.get(b)||0) <= 1);
      addCheck(list, "F függvény? (minden fosszília pontosan 1 ágyba)", totalSet);
      addCheck(list, "Injektív? (nincs két fosszília ugyanarra az ágyra)", injective);
      $("checks").style.display = "block";
    }

    if (state.sceneKey === "iso"){
      $("checks").style.display = "block";
      const fossils = state.nodes.filter(n=>n.type==='fossil').map(n=>n.id);
      const envs = state.nodes.filter(n=>n.type==='env').map(n=>n.id);
      const f = state.edges.filter(e=>e.kind==='f');
      const outCount = new Map(); fossils.forEach(a=>outCount.set(a,0));
      const inCount = new Map();  envs.forEach(b=>inCount.set(b,0));
      f.forEach(e => { outCount.set(e.from, (outCount.get(e.from)||0)+1); inCount.set(e.to, (inCount.get(e.to)||0)+1); });
      const isFunc = fossils.every(a => (outCount.get(a)||0)===1);
      const injective = envs.every(b => (inCount.get(b)||0) <= 1);
      const surjective = envs.every(b => (inCount.get(b)||0) >= 1);
      const bijective = isFunc && injective && surjective;
      addCheck(list, "F függvény? (minden fosszília kap értéket)", isFunc);
      addCheck(list, "Injektív?", injective);
      addCheck(list, "Szürjektív?", surjective);
      addCheck(list, "Bijektív?", bijective);
    }

    if (state.sceneKey === "compose"){
      $("checks").style.display = "block";
      const f = state.edges.filter(e=>e.kind==='f').length;
      const comp = state.edges.filter(e=>e.kind==='comp').length;
      addCheck(list, "g∘f kiszámítva (bal fosszília → jobb környezet)", comp>0);
      addCheck(list, "Hány f-nyíl?", f);
      addCheck(list, "Hány g∘f (összetett) nyíl?", comp);
    }

    if (state.sceneKey === "inverse"){
      $("checks").style.display = "block";
      const dom = new Set(state.scene.domain);
      const f = state.edges.filter(e=>e.kind==='f');
      const outCount = new Map(); state.scene.domain.forEach(a=>outCount.set(a,0));
      const envs = state.nodes.filter(n=>n.type==='env').map(n=>n.id);
      const inCount = new Map();  envs.forEach(b=>inCount.set(b,0));
      f.forEach(e => { if (dom.has(e.from)) { outCount.set(e.from, (outCount.get(e.from)||0)+1); inCount.set(e.to, (inCount.get(e.to)||0)+1); }});
      const isFunc = state.scene.domain.every(a => (outCount.get(a)||0)===1);
      const injective = envs.every(b => (inCount.get(b)||0) <= 1);
      const surjective = envs.every(b => (inCount.get(b)||0) >= 1);
      const bij = isFunc && injective && surjective;
      addCheck(list, "Bijekció? (csak ekkor invertálható)", bij);
      if (bij) footer("Bijekció és inverz fogalma: a nyilak megfordíthatók, minden környezeti elemhez pontosan egy fosszília tartozik és viszont.");
      $("checks").style.display = "block";
    }
  }

  function addCheck(ul, label, ok){
    const li = document.createElement("li");
    li.innerHTML = `<strong>${label}:</strong> ${ok===true ? "✓ Igen" : ok===false ? "✗ Nem" : ok}`;
    ul.appendChild(li);
  }

  function footer(msg){
    $("footerMsg").textContent = msg;
  }

  // ---------------- Drawing ----------------
  const imgCache = new Map();
  function getImage(url){
    return new Promise((resolve) => {
      if (imgCache.has(url)) { resolve(imgCache.get(url)); return; }
      const im = new Image();
      im.crossOrigin = "anonymous"; // imgur permits CORS
      im.onload = () => { imgCache.set(url, im); resolve(im); };
      im.onerror = () => resolve(null);
      im.src = url;
    });
  }

  async function draw(){
    state.needsDraw = false;
    const w = canvas.clientWidth, h = canvas.clientHeight;
    ctx.clearRect(0,0,w,h);

    // Frame
    ctx.fillStyle = "#0c1220";
    ctx.strokeStyle = "#223045";
    ctx.lineWidth = 1.5;
    rr(8.5,8.5, w-17, h-17, 12); ctx.fill(); ctx.stroke();

    // Edges (draw first, then nodes on top)
    for (const e of state.edges){
      drawEdge(e);
    }

    // Nodes
    const showLabels = $("showLabels").checked;
    for (const n of state.nodes){
      if (n.type==='fossil'){
        // circle with image
        const cx = n.x*w, cy = n.y*h, R=34;
        ctx.save();
        ctx.beginPath(); ctx.arc(cx,cy,R,0,Math.PI*2); ctx.closePath(); ctx.clip();
        const im = await getImage(n.img);
        if (im){
          // fit image keeping aspect
          const scale = Math.max((2*R)/im.width, (2*R)/im.height);
          const iw = im.width*scale, ih = im.height*scale;
          ctx.drawImage(im, cx - iw/2, cy - ih/2, iw, ih);
        } else {
          ctx.fillStyle = "#1b2536"; ctx.fill();
        }
        ctx.restore();
        ctx.strokeStyle = "#5aa7ff"; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(cx,cy,R,0,Math.PI*2); ctx.stroke();

        if (showLabels){
          labelChip(cx, cy+R+10, n.name);
        }
      }
      else if (n.type==='bed' || n.type==='env'){
        const cx = n.x*w, cy = n.y*h;
        const text = n.name;
        ctx.fillStyle = (n.type==='bed') ? "#0e1523" : "#0e1523";
        ctx.strokeStyle = (n.type==='bed') ? "#2b3a52" : "#2b3a52";
        ctx.lineWidth = 1.2;
        rr(cx - n.w/2, cy - n.h/2, n.w, n.h, 8); ctx.fill(); ctx.stroke();
        ctx.fillStyle = "#cfe0ff";
        ctx.font = "500 12px system-ui, -apple-system, Segoe UI, Roboto, Arial";
        ctx.textAlign = "center"; ctx.textBaseline = "middle";
        ctx.fillText(text, cx, cy);
      }
    }
  }

  function rr(x,y,w,h,r){
    const rr = Math.min(r, Math.min(w,h)/2);
    ctx.beginPath();
    ctx.moveTo(x+rr,y);
    ctx.arcTo(x+w,y, x+w,y+h, rr);
    ctx.arcTo(x+w,y+h, x,y+h, rr);
    ctx.arcTo(x,y+h, x,y, rr);
    ctx.arcTo(x,y, x+w,y, rr);
    ctx.closePath();
  }

  function labelChip(cx, topY, text){
    ctx.font = "500 12px system-ui, -apple-system, Segoe UI, Roboto, Arial";
    const pad=8, tw = ctx.measureText(text).width + pad*2, th=20;
    ctx.fillStyle = "rgba(12,18,32,0.92)";
    rr(cx - tw/2, topY- th/2, tw, th, 8); ctx.fill();
    ctx.strokeStyle = "#233040"; ctx.lineWidth = 1; rr(cx - tw/2, topY- th/2, tw, th, 8); ctx.stroke();
    ctx.fillStyle = "#d7e6ff"; ctx.textAlign="center"; ctx.textBaseline="middle";
    ctx.fillText(text, cx, topY);
  }

  function drawEdge(e){
    const a = idNode(e.from), b = idNode(e.to);
    if (!a || !b) return;
    const w = canvas.clientWidth, h = canvas.clientHeight;
    const ax = a.x*w, ay = a.y*h;
    const bx = b.x*w, by = b.y*h;
    const col = COLORS[e.kind] || "#7dd3fc";
    ctx.strokeStyle = col; ctx.lineWidth = 2.2; ctx.fillStyle = col;
    // curve slightly
    const mx = (ax+bx)/2, my = (ay+by)/2 - 18;
    ctx.beginPath();
    ctx.moveTo(ax,ay);
    ctx.quadraticCurveTo(mx,my,bx,by);
    ctx.stroke();
    // arrow head
    const ang = Math.atan2(by-my, bx-mx);
    const size = 6;
    ctx.beginPath();
    ctx.moveTo(bx,by);
    ctx.lineTo(bx - size*Math.cos(ang - Math.PI/6), by - size*Math.sin(ang - Math.PI/6));
    ctx.lineTo(bx - size*Math.cos(ang + Math.PI/6), by - size*Math.sin(ang + Math.PI/6));
    ctx.closePath(); ctx.fill();
  }

  // ---------------- Animation loop ----------------
  function loop(){
    if (state.needsDraw) draw();
    requestAnimationFrame(loop);
  }

  // ---------------- Buttons ----------------
  $("btnReset").addEventListener("click", () => {
    setScene(state.sceneKey);
  });

  // ---------------- Boot ----------------
  (async function boot(){
    // size canvas
    resizeCanvas();
    // fetch assets
    await loadAssets();
    buildTabs();
    buildPropChips();
    // default scene
    setScene("relation");
    loop();
  })();
})();
</script>
{% endblock %}
