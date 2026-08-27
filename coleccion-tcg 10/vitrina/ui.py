"""Interfaz local: una sola página servida desde el propio programa."""

PAGE = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vitrina — colección TCG</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Saira+Condensed:wght@500;600;700&family=Archivo:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
:root{
  --accent:#c9a227; --deep:#0d2a21; --glow:#17402f;
  --ivory:#f1ece0; --paper:#e7e0cf; --ink:#141d19; --sage:#93ac9e;
  --line:rgba(241,236,224,.16); --panel:rgba(9,26,20,.72);
  --red:#cf5340; --green:#5fbf8a;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--deep);color:var(--ivory);
  font-family:'Archivo',system-ui,sans-serif;padding-bottom:4rem;
  transition:background-color .6s ease}
button,input,select,textarea{font-family:inherit}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
a{color:var(--accent)}
.wrap{max-width:72rem;margin:0 auto;padding:0 1rem;position:relative;z-index:1}

/* ---------- escenario ---------- */
#scene{position:fixed;inset:0;z-index:0;overflow:hidden;pointer-events:none;background:var(--deep)}
#motif{position:absolute;inset:-10%;background-repeat:repeat;background-size:240px 240px;opacity:.5}
#cast{position:absolute;inset:0}
#cast img{position:absolute;object-fit:contain;opacity:0;filter:saturate(.8) contrast(1.05);
  transition:opacity 1.1s ease, transform 1.1s ease;transform:translateY(14px) scale(.97);will-change:opacity}
#cast img.in{opacity:var(--o,.34);transform:none}
#scene::after{content:"";position:absolute;inset:0;
  background:radial-gradient(ellipse at 50% 42%, rgba(4,14,11,.55) 0%, rgba(4,14,11,.86) 58%, rgba(4,14,11,.96) 100%),
             radial-gradient(circle at 18% -12%, var(--glow) 0%, transparent 52%)}
#scene .vignette{position:absolute;inset:0;
  background:linear-gradient(180deg, rgba(4,14,11,.75) 0%, transparent 22%, transparent 70%, rgba(4,14,11,.85) 100%)}
@media (prefers-reduced-motion:reduce){#cast img{transition:none}}

/* ---------- cabecera ---------- */
header{border-bottom:1px solid var(--line);padding:1.5rem 0 .6rem}
.topline{display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;flex-wrap:wrap}
.eyebrow{font:600 .68rem/1 'IBM Plex Mono',monospace;letter-spacing:.18em;text-transform:uppercase;color:var(--sage)}
h1{font:700 2.6rem/1 'Saira Condensed',sans-serif;letter-spacing:.02em;text-transform:uppercase;margin:.25rem 0 0}
#scenetag{font:500 .7rem/1 'IBM Plex Mono',monospace;color:var(--accent);letter-spacing:.1em;text-transform:uppercase}
.tick{text-align:right;margin-left:auto}
.ticklabel{display:block;font:500 .65rem/1 'IBM Plex Mono',monospace;letter-spacing:.16em;text-transform:uppercase;color:var(--sage)}
.tickvalue{display:block;font:600 2.2rem/1.1 'IBM Plex Mono',monospace;color:var(--accent);font-variant-numeric:tabular-nums}
.ticksub{display:block;font-size:.74rem;color:var(--sage);margin-top:.2rem}
.up{color:var(--green)}.down{color:var(--red)}
.tabs{display:flex;gap:.4rem;margin-top:1rem;overflow-x:auto;padding-bottom:.5rem}
.tab{flex:none;background:rgba(9,26,20,.5);border:1px solid var(--line);color:var(--sage);border-radius:999px;
  padding:.42rem .85rem;font:600 .78rem/1 'Saira Condensed',sans-serif;letter-spacing:.06em;
  text-transform:uppercase;cursor:pointer;transition:background .25s,color .25s}
.tab em{font-style:normal;font-family:'IBM Plex Mono',monospace;font-size:.7rem;opacity:.7;margin-left:.3rem}
.tab.on{background:var(--accent);color:#1a1405;border-color:var(--accent)}

/* ---------- barra ---------- */
.bar{display:flex;gap:.5rem;padding:.9rem 0;flex-wrap:wrap;align-items:center}
.search{flex:1 1 12rem;min-width:0;background:var(--panel);border:1px solid var(--line);color:var(--ivory);
  border-radius:.4rem;padding:.6rem .7rem;font-size:.9rem}
.search::placeholder{color:#6c8579}
select.sel{background:var(--panel);border:1px solid var(--line);color:var(--ivory);border-radius:.4rem;padding:.6rem .5rem;font-size:.82rem}
.primary{background:var(--accent);color:#1a1405;border:0;border-radius:.4rem;padding:.6rem 1rem;cursor:pointer;
  font:600 .82rem/1 'Saira Condensed',sans-serif;letter-spacing:.08em;text-transform:uppercase}
.primary:disabled{opacity:.4;cursor:default}
.ghost{background:rgba(9,26,20,.45);border:1px solid var(--line);color:var(--ivory);border-radius:.4rem;cursor:pointer;
  padding:.55rem .9rem;font:600 .78rem/1 'Saira Condensed',sans-serif;letter-spacing:.07em;text-transform:uppercase;
  text-decoration:none;display:inline-block}
.ghost.sm{padding:.4rem .7rem;font-size:.72rem}
.danger{background:transparent;border:1px solid var(--red);color:var(--red);border-radius:.4rem;cursor:pointer;
  padding:.55rem .9rem;font:600 .78rem/1 'Saira Condensed',sans-serif;letter-spacing:.07em;text-transform:uppercase}
.status{font:400 .72rem/1.5 'IBM Plex Mono',monospace;color:var(--sage);margin:.2rem 0 0}
.status.err{color:var(--red)}

/* ---------- grupos y fichas ---------- */
.ghead{display:flex;align-items:baseline;gap:.6rem;margin:1.6rem 0 .6rem}
.gcat{font:500 .62rem/1 'IBM Plex Mono',monospace;letter-spacing:.14em;text-transform:uppercase;
  color:var(--deep);background:var(--sage);padding:.25rem .4rem;border-radius:.2rem}
.ghead h2{font:600 1.15rem/1 'Saira Condensed',sans-serif;letter-spacing:.04em;text-transform:uppercase;margin:0}
.grule{flex:1;height:1px;background:var(--line)}
.gsum{font:600 .95rem/1 'IBM Plex Mono',monospace;color:var(--accent)}

.slab{background:var(--paper);color:var(--ink);border-radius:.3rem;margin-bottom:.45rem;overflow:hidden;
  box-shadow:0 2px 10px rgba(0,0,0,.35)}
.slab.graded{border-left:5px solid var(--accent)}
.slab.raw{background:var(--panel);color:var(--ivory);border:1px dashed var(--line);
  backdrop-filter:blur(3px);box-shadow:none}
.slabmain{display:flex;align-items:center;gap:.7rem;width:100%;background:transparent;border:0;color:inherit;
  text-align:left;padding:.6rem .7rem;cursor:pointer}
.meta{flex:none;width:5.2rem;border-right:1px solid rgba(20,29,25,.18);padding-right:.5rem}
.slab.raw .meta{border-color:var(--line)}
.mline{display:block;font:600 .78rem/1.2 'IBM Plex Mono',monospace}
.mline.dim{font-weight:400;font-size:.66rem;opacity:.6;margin-top:.15rem}
.title{flex:1;min-width:0}
.cname{display:block;font:600 1.02rem/1.15 'Saira Condensed',sans-serif;letter-spacing:.02em;text-transform:uppercase;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.chips{display:flex;gap:.25rem;margin-top:.25rem;flex-wrap:wrap}
.chip{font:500 .6rem/1 'IBM Plex Mono',monospace;padding:.22rem .35rem;border-radius:.2rem;background:rgba(20,29,25,.09)}
.slab.raw .chip{background:rgba(255,255,255,.09)}
.chip.hot{background:var(--red);color:#fff}
.chip.warm{background:var(--accent);color:#1a1405}
.chip.up{background:#1f6b47;color:#dff5e8}
.chip.down{background:rgba(207,83,64,.2);color:#8f2f1f}
.slab.raw .chip.down{color:#ffb3a5;background:rgba(207,83,64,.28)}
.chip.qty{background:var(--ink);color:var(--paper)}
.slab.raw .chip.qty{background:var(--ivory);color:var(--ink)}
.right{flex:none;display:flex;align-items:center;gap:.6rem}
.gradebox{display:flex;flex-direction:column;align-items:center;justify-content:center;background:var(--ink);
  color:var(--paper);border-radius:.2rem;padding:.25rem .45rem;min-width:2.9rem}
.gradebox em{font:500 .55rem/1 'IBM Plex Mono',monospace;font-style:normal;letter-spacing:.1em;opacity:.75}
.gradebox b{font:700 1.25rem/1 'Saira Condensed',sans-serif}
.condbox{font:600 .72rem/1 'IBM Plex Mono',monospace;border:1px solid rgba(20,29,25,.3);padding:.35rem .4rem;border-radius:.2rem}
.slab.raw .condbox{border-color:var(--line);color:var(--sage)}
.price{font:600 1rem/1 'IBM Plex Mono',monospace;min-width:5.6rem;text-align:right;font-variant-numeric:tabular-nums}
.delta{display:block;font:500 .64rem/1.4 'IBM Plex Mono',monospace;text-align:right}

.detail{display:grid;grid-template-columns:1fr 1fr;gap:1.2rem;padding:.2rem .9rem 1rem;border-top:1px solid rgba(20,29,25,.14)}
.slab.raw .detail{border-color:var(--line)}
.detail h3{font:600 .68rem/1 'IBM Plex Mono',monospace;letter-spacing:.14em;text-transform:uppercase;opacity:.55;margin:.9rem 0 .5rem}
.sales{list-style:none;margin:0;padding:0}
.sales li{display:flex;align-items:center;gap:.5rem;margin-bottom:.3rem}
.sdate{font:400 .68rem/1 'IBM Plex Mono',monospace;opacity:.6;flex:none;width:5.4rem}
.sbar{height:.55rem;background:var(--accent);border-radius:1px;min-width:2px;flex:none;max-width:45%}
.sprice{font:500 .78rem/1 'IBM Plex Mono',monospace;margin-left:auto}
.facts{display:grid;grid-template-columns:auto 1fr;gap:.25rem .8rem;margin:0;font-size:.78rem}
.facts dt{opacity:.6}
.facts dd{margin:0;font-family:'IBM Plex Mono',monospace;text-align:right}
.dactions{display:flex;gap:.4rem;margin-top:.9rem;flex-wrap:wrap}
.slab:not(.raw) .ghost{border-color:rgba(20,29,25,.25);color:var(--ink);background:transparent}
.dim{opacity:.6;font-size:.8rem}
.empty{color:var(--sage);text-align:center;padding:2.5rem 1rem;font-size:.9rem}

footer{margin-top:2rem;padding-top:1.2rem;border-top:1px solid var(--line)}
.brow{display:flex;align-items:center;gap:.6rem;margin-bottom:.35rem}
.blabel{width:5.5rem;font:600 .75rem/1 'Saira Condensed',sans-serif;letter-spacing:.06em;text-transform:uppercase}
.bbar{flex:1;height:.4rem;background:rgba(255,255,255,.08);border-radius:1px;overflow:hidden}
.bbar span{display:block;height:100%;background:var(--accent)}
.bval{font:500 .78rem/1 'IBM Plex Mono',monospace;width:7rem;text-align:right;color:var(--sage)}
.note{font-size:.72rem;color:var(--sage);opacity:.85;line-height:1.6;margin-top:1rem;max-width:48rem}

/* ---------- editor ---------- */
.scrim{position:fixed;inset:0;background:rgba(3,12,9,.88);display:flex;align-items:flex-start;justify-content:center;
  z-index:40;padding:1rem;overflow:auto}
.sheet{background:rgba(11,30,23,.97);border:1px solid var(--line);border-radius:.6rem;width:100%;max-width:47rem;
  padding:1rem;margin:auto;box-shadow:0 20px 60px rgba(0,0,0,.5)}
.sheethead{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:.9rem;gap:1rem}
.sheethead h2{font:600 1.3rem/1 'Saira Condensed',sans-serif;letter-spacing:.05em;text-transform:uppercase;margin:0}
.fields{display:grid;grid-template-columns:repeat(2,1fr);gap:.6rem}
label.f{display:flex;flex-direction:column;gap:.25rem}
label.f.wide,.f.wide{grid-column:1/-1}
label.f>span,.f>span{font:500 .64rem/1 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--sage)}
.f input,.f select,.f textarea{background:rgba(4,14,11,.6);border:1px solid var(--line);color:var(--ivory);
  border-radius:.35rem;padding:.55rem .6rem;font-size:.88rem;width:100%}
.segrow{display:flex;gap:.35rem}
.seg{flex:1;background:rgba(4,14,11,.6);border:1px solid var(--line);color:var(--sage);border-radius:.35rem;padding:.55rem;
  font:600 .75rem/1 'Saira Condensed',sans-serif;letter-spacing:.06em;text-transform:uppercase;cursor:pointer}
.seg.on{background:var(--ivory);color:var(--ink);border-color:var(--ivory)}
.block{margin:1rem 0;padding:.8rem;border:1px solid var(--line);border-radius:.4rem;background:rgba(4,14,11,.35)}
.blockhead{display:flex;justify-content:space-between;align-items:center;gap:.5rem;margin-bottom:.6rem}
.blockhead h3{font:600 .7rem/1 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--sage);margin:0}
.salerow{display:flex;gap:.4rem;margin-bottom:.4rem}
.salerow input{background:rgba(4,14,11,.6);border:1px solid var(--line);color:var(--ivory);border-radius:.35rem;
  padding:.5rem .55rem;font:500 .85rem/1 'IBM Plex Mono',monospace;flex:1;min-width:0}
.x{background:transparent;border:1px solid var(--line);color:var(--sage);border-radius:.35rem;width:2.2rem;font-size:1.1rem;cursor:pointer}
.hint{font-size:.7rem;color:var(--sage);opacity:.85;margin:.5rem 0 0;line-height:1.5}
.results{list-style:none;margin:.5rem 0 0;padding:0;max-height:15rem;overflow:auto;border-top:1px solid var(--line)}
.results li{display:flex;justify-content:space-between;gap:.6rem;padding:.5rem;border-bottom:1px solid var(--line);
  cursor:pointer;font-size:.83rem;align-items:center}
.results li:hover,.results li:focus{background:rgba(255,255,255,.06)}
.results .rname{display:block}
.results small{color:var(--sage);font-family:'IBM Plex Mono',monospace;font-size:.68rem}
.origin{font:500 .58rem/1 'IBM Plex Mono',monospace;letter-spacing:.06em;text-transform:uppercase;
  padding:.2rem .35rem;border-radius:.2rem;background:rgba(255,255,255,.1);color:var(--sage);white-space:nowrap}
.origin.api{background:var(--accent);color:#1a1405}
.origin.mine{background:rgba(95,191,138,.2);color:var(--green)}
.rprice{font:600 .82rem/1 'IBM Plex Mono',monospace;text-align:right;white-space:nowrap}
.linked{font:500 .72rem/1.4 'IBM Plex Mono',monospace;color:var(--green)}
.linked.no{color:var(--sage)}
.sheetfoot{display:flex;gap:.5rem;align-items:center;margin-top:1rem;flex-wrap:wrap}
.spacer{flex:1}
.spin{display:inline-block;width:.7rem;height:.7rem;border:2px solid var(--sage);border-top-color:transparent;
  border-radius:50%;animation:sp .7s linear infinite;vertical-align:-1px}
@keyframes sp{to{transform:rotate(360deg)}}
@media (max-width:640px){
  h1{font-size:2rem}.tickvalue{font-size:1.6rem}
  .detail{grid-template-columns:1fr;gap:0}.fields{grid-template-columns:1fr}
  .meta{width:4.2rem}.price{min-width:4.8rem;font-size:.85rem}.cname{font-size:.95rem}
}
</style>
</head>
<body>
<div id="scene"><div id="motif"></div><div id="cast"></div><div class="vignette"></div></div>

<div class="wrap">
  <header>
    <div class="topline">
      <div>
        <div class="eyebrow">Registro de colección</div>
        <h1>Vitrina</h1>
        <div id="scenetag"></div>
      </div>
      <div class="tick">
        <span class="ticklabel">Valor total</span>
        <span class="tickvalue" id="total">—</span>
        <span class="ticksub" id="totalsub"></span>
      </div>
    </div>
    <nav class="tabs" id="tabs"></nav>
  </header>

  <div class="bar">
    <input class="search" id="q" placeholder="Buscar en tu colección…">
    <select class="sel" id="basis">
      <option value="avg7">Valorar con AVG7 (media 7 días)</option>
      <option value="trend">Valorar con Trend</option>
      <option value="avg1">Valorar con AVG1 (media de ayer)</option>
      <option value="avg30">Valorar con AVG30</option>
      <option value="low">Valorar con precio más bajo</option>
    </select>
    <button class="ghost" id="sync">Actualizar precios</button>
    <button class="primary" id="add">+ Añadir carta</button>
  </div>
  <p class="status" id="status"></p>

  <main id="list"></main>

  <footer>
    <div id="breakdown"></div>
    <p class="note" id="note"></p>
  </footer>
</div>

<div id="modal"></div>

<script>
const CATS = [["pokemon","Pokémon"],["onepiece","One Piece"],["futbol","Fútbol"],["basquet","Básquet"],["beisbol","Béisbol"]];
const CM_CATS = ["pokemon","onepiece"];
const SCENE_TAG = {all:"Toda la vitrina", pokemon:"Sección Pokémon", onepiece:"Sección One Piece",
  futbol:"Sección Fútbol", basquet:"Sección Básquet", beisbol:"Sección Béisbol"};
const eur = n => new Intl.NumberFormat("es-ES",{style:"currency",currency:"EUR"}).format(n||0);
const esc = s => String(s??"").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const pct = n => (n>0?"+":"") + n.toFixed(1) + "%";
let STATE = {cards:[], total:0}, CAT = "all", Q = "", OPEN = null, BASIS = "avg7";

async function api(path, opts={}) {
  const r = await fetch(path, {headers:{"Content-Type":"application/json"}, ...opts});
  const data = await r.json();
  if (!r.ok || data.error) throw new Error(data.error || ("Error " + r.status));
  return data;
}
function say(msg, err) {
  const el = document.getElementById("status");
  el.innerHTML = msg || ""; el.className = "status" + (err ? " err" : "");
}

/* ------------------------------------------------------------ escenario */

// Posiciones fijas: los personajes enmarcan la página y dejan libre el centro.
const SLOTS = [
  {left:"-4%",  bottom:"-6%", height:"52vh", o:.34, z:1},
  {right:"-3%", bottom:"-4%", height:"46vh", o:.30, z:1},
  {left:"6%",   top:"6%",     height:"30vh", o:.20, z:0},
  {right:"7%",  top:"4%",     height:"33vh", o:.22, z:0},
  {left:"38%",  bottom:"-14%",height:"38vh", o:.14, z:0},
  {right:"31%", top:"30%",    height:"26vh", o:.12, z:0},
];

let sceneToken = 0;
async function setScene(cat) {
  const token = ++sceneToken;
  document.getElementById("scenetag").textContent = SCENE_TAG[cat] || "";
  let data;
  try { data = await api("/api/art?cat=" + cat); } catch { return; }
  if (token !== sceneToken) return;

  const p = data.palette || {};
  const root = document.documentElement.style;
  root.setProperty("--accent", p.accent || "#c9a227");
  root.setProperty("--deep", p.deep || "#0d2a21");
  root.setProperty("--glow", p.glow || "#17402f");
  document.getElementById("motif").style.backgroundImage = `url("${data.motif}")`;

  const cast = document.getElementById("cast");
  cast.innerHTML = "";
  const pics = shuffle(data.images).slice(0, SLOTS.length);
  pics.forEach((src, i) => {
    const s = SLOTS[i], img = new Image();
    img.src = src; img.alt = "";
    Object.assign(img.style, {height:s.height, zIndex:s.z}, s.left?{left:s.left}:{},
      s.right?{right:s.right}:{}, s.top?{top:s.top}:{}, s.bottom?{bottom:s.bottom}:{});
    img.style.setProperty("--o", s.o);
    cast.appendChild(img);
    img.decode ? img.decode().then(() => img.classList.add("in")).catch(()=>img.classList.add("in"))
               : img.onload = () => img.classList.add("in");
  });
  if (!pics.length) hintNoArt(cat);
}
const shuffle = a => a.map(v => [Math.random(), v]).sort((x,y)=>x[0]-y[0]).map(x=>x[1]);

function hintNoArt(cat) {
  if (cat === "pokemon") say(`Sección sin imágenes. Ejecuta <b>python3 tcg.py art</b> para traer las ilustraciones oficiales desde PokéAPI.`);
  else if (cat !== "all") say(`Sección sin imágenes. Deja las que quieras en <b>art/${cat}/</b> y recarga.`);
}

/* ------------------------------------------------------------ estado */

async function load() {
  try { STATE = await api("/api/state?basis=" + BASIS); render(); }
  catch (e) { say(e.message, true); }
}

function render() {
  document.getElementById("total").textContent = eur(STATE.total);
  const inv = STATE.invested, p = STATE.profit;
  document.getElementById("totalsub").innerHTML =
    `${STATE.cards.length} referencias · ${STATE.units} unidades` +
    (inv > 0 ? ` · invertido ${eur(inv)} <b class="${p>=0?"up":"down"}">(${p>=0?"+":""}${(p/inv*100).toFixed(0)}%)</b>` : "");

  const counts = {};
  STATE.cards.forEach(c => counts[c.category] = (counts[c.category]||0)+1);
  document.getElementById("tabs").innerHTML =
    [["all","Todo"]].concat(CATS).map(([id,label]) =>
      `<button class="tab ${CAT===id?"on":""}" data-cat="${id}">${label}<em>${id==="all"?STATE.cards.length:(counts[id]||0)}</em></button>`).join("");

  let list = STATE.cards.filter(c => CAT==="all" || c.category===CAT);
  if (Q.trim()) {
    const t = Q.toLowerCase();
    list = list.filter(c => [c.name,c.collection,c.number,c.rarity,c.cert,c.notes]
      .some(f => String(f||"").toLowerCase().includes(t)));
  }
  list.sort((a,b) => b.total_value - a.total_value);

  const groups = new Map();
  list.forEach(c => {
    const k = (c.collection || "Sin colección") + "|" + c.category;
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k).push(c);
  });
  const sum = l => l.reduce((a,c) => a + c.total_value, 0);

  document.getElementById("list").innerHTML = groups.size
    ? [...groups.entries()].sort((a,b) => sum(b[1]) - sum(a[1])).map(([k, cards]) => {
        const [coll, cat] = k.split("|");
        const label = (CATS.find(c => c[0]===cat)||[,cat])[1];
        return `<section><div class="ghead"><span class="gcat">${esc(label)}</span><h2>${esc(coll)}</h2>
          <span class="grule"></span><span class="gsum">${eur(sum(cards))}</span></div>
          ${cards.map(slab).join("")}</section>`;
      }).join("")
    : `<p class="empty">${STATE.cards.length ? "Ninguna carta coincide con ese filtro."
        : "Todavía no hay cartas. Empieza por la que más te guste."}</p>`;

  document.getElementById("breakdown").innerHTML = (STATE.by_category||[])
    .sort((a,b) => b.value - a.value).map(k => `<div class="brow">
      <span class="blabel">${esc(k.label)}</span>
      <span class="bbar"><span style="width:${STATE.total ? k.value/STATE.total*100 : 0}%"></span></span>
      <span class="bval">${eur(k.value)}</span></div>`).join("");

  document.getElementById("note").innerHTML = STATE.last_sync
    ? `Precios de Cardmarket del ${esc(STATE.last_sync)}${STATE.cm_linked ? " · API conectada" : ""}. Cardmarket no publica las ventas una a una: cada línea del historial es AVG1, el precio medio de lo vendido ese día. Fútbol, básquet y béisbol no están en Cardmarket, así que ahí las ventas se anotan a mano.`
    : `Sin sincronizar todavía. Descarga la guía de precios y el catálogo desde cardmarket.com/Data/Download, déjalos en <b>data/</b> y pulsa Actualizar precios.`;
}

function slab(c) {
  const qty = c.quantity || 1;
  const chips = (c.flags||[]).slice(0,3).map(f => `<span class="chip ${f.tone}">${esc(f.t)}</span>`).join("");
  const d = c.deltas;
  const dd = d && d.d1 != null
    ? `<span class="delta ${d.d1>=0?"up":"down"}">${pct(d.d1)} hoy</span>` : "";
  return `<article class="slab ${c.graded ? "graded" : "raw"}">
    <div class="slabmain" data-open="${c.id}" role="button" tabindex="0">
      <span class="meta"><span class="mline">${esc(c.number||"—")}</span>
        <span class="mline dim">${esc(c.lang||"")}${c.rarity ? " · " + esc(c.rarity) : ""}</span></span>
      <span class="title"><span class="cname">${esc(c.name)}</span>
        <span class="chips">${qty>1?`<span class="chip qty">×${qty}</span>`:""}${chips}</span></span>
      <span class="right">
        ${c.graded ? `<span class="gradebox"><em>${esc(c.grader||"")}</em><b>${esc(c.grade||"")}</b></span>`
                   : `<span class="condbox">${esc(c.condition||"—")}</span>`}
        <span><span class="price">${eur(c.total_value)}</span>${dd}</span></span>
    </div>
    ${OPEN === c.id ? detail(c) : ""}
  </article>`;
}

function detail(c) {
  const s = c.series || [], max = Math.max(1, ...s.map(x => x.price)), pr = c.price_row || {}, d = c.deltas;
  const drow = (label, v, base) => v == null ? "" :
    `<dt>${label}</dt><dd class="${v>=0?"up":"down"}">${pct(v)}${base?` · ${eur(base)}`:""}</dd>`;
  return `<div class="detail">
    <div>
      <h3>Precio real, día a día</h3>
      ${s.length ? `<ul class="sales">${s.map(x => `<li>
          <span class="sdate">${esc(x.date||"s/f")}</span>
          <span class="sbar" style="width:${x.price/max*100}%"></span>
          <span class="sprice">${eur(x.price)}</span></li>`).join("")}</ul>`
        : `<p class="dim">Sin historial aún. Actualiza precios cada día y esta lista se llena sola.</p>`}
      <dl class="facts" style="margin-top:.8rem">
        ${d ? drow("Frente a ayer", d.d1, d.d1_value) : ""}
        ${d ? drow("Frente a hace 7 días", d.d7, d.d7_value) : ""}
        ${d ? drow("Frente a hace 30 días", d.d30, d.d30_value) : ""}
        <dt>Valor unitario</dt><dd>${eur(c.unit_value)}</dd>
        <dt>Origen del precio</dt><dd>${esc(c.value_source)}</dd>
        ${pr.low!=null?`<dt>Más barata ahora</dt><dd>${eur(pr.low)}</dd>`:""}
        ${pr.trend!=null?`<dt>Trend</dt><dd>${eur(pr.trend)}</dd>`:""}
      </dl>
    </div>
    <div>
      <h3>Ficha</h3>
      <dl class="facts">
        ${c.graded ? `<dt>Población en ${esc(c.grader)} ${esc(c.grade)}</dt><dd>${c.pop_grade??"—"}</dd>
                      <dt>Población total</dt><dd>${c.pop_total??"—"}</dd>
                      <dt>Certificado</dt><dd>${esc(c.cert||"—")}</dd>` : ""}
        <dt>Cantidad</dt><dd>${c.quantity||1}</dd>
        <dt>Compra</dt><dd>${c.purchase!=null?eur(c.purchase):"—"}</dd>
        <dt>idProduct</dt><dd>${c.id_product??"sin enlazar"}</dd>
        ${c.notes?`<dt>Notas</dt><dd>${esc(c.notes)}</dd>`:""}
      </dl>
      <div class="dactions">
        <button class="ghost sm" data-edit="${c.id}">Editar</button>
        ${c.id_product?`<a class="ghost sm" target="_blank" rel="noreferrer"
           href="https://www.cardmarket.com/en/Pokemon/Products/Singles?idProduct=${c.id_product}">Ver en Cardmarket</a>`:""}
        ${c.cert?`<a class="ghost sm" target="_blank" rel="noreferrer"
           href="https://www.psacard.com/cert/${esc(c.cert)}">Verificar cert</a>`:""}
      </div>
    </div>
  </div>`;
}

/* ------------------------------------------------------------ editor */

function openEditor(card) {
  const d = Object.assign({
    id:null, category:CAT==="all"?"pokemon":CAT, collection:"", name:"", number:"", rarity:"", lang:"ES",
    quantity:1, condition:"NM", graded:0, grader:"PSA", grade:"10", cert:"", pop_grade:"",
    pop_total:"", purchase:"", id_product:"", grade_multiplier:1, manual_price:"", notes:"", manual_sales:[]
  }, card || {});
  const sales = (d.manual_sales||[]).map(s => ({price:s.price, date:s.date})).slice(0,5);
  if (!sales.length) sales.push({price:"",date:""});
  const field = (k, label, extra="") =>
    `<label class="f"><span>${label}</span><input name="${k}" value="${esc(d[k]??"")}" ${extra}></label>`;

  document.getElementById("modal").innerHTML = `<div class="scrim"><div class="sheet">
    <div class="sheethead"><h2>${d.id ? "Editar carta" : "Nueva carta"}</h2>
      <span class="linked ${d.id_product?"":"no"}" id="linked">${d.id_product ? "enlazada · idProduct " + d.id_product : "sin enlazar"}</span></div>

    <div class="block" id="finder">
      <div class="blockhead"><h3>Identificar la carta</h3><span class="hint" id="fsrc"></span></div>
      <div class="salerow">
        <input id="fq" placeholder="Escribe el nombre y elige la carta exacta…" value="${esc(d.name)}" autofocus>
        <button type="button" class="ghost sm" id="fbtn">Buscar</button>
      </div>
      <ul class="results" id="fres"></ul>
      <p class="hint" id="fhint">Busca a la vez en el catálogo de Cardmarket que tienes descargado y en su API. Al elegir un resultado se rellena la ficha y la carta queda atada a ese idProduct, que es lo que permite seguir su precio real cada día.</p>
    </div>

    <div class="fields">
      <label class="f wide"><span>Nombre</span><input name="name" value="${esc(d.name)}"></label>
      <label class="f"><span>Categoría</span><select name="category">
        ${CATS.map(([i,l]) => `<option value="${i}" ${d.category===i?"selected":""}>${l}</option>`).join("")}
      </select></label>
      ${field("collection","Colección / set")}
      ${field("number","Número")}
      ${field("rarity","Rareza")}
      ${field("lang","Idioma")}
      ${field("quantity","Cantidad",'type="number" min="1"')}
      <div class="f wide"><span>Estado</span><div class="segrow">
        <button type="button" class="seg ${!d.graded?"on":""}" data-graded="0">Sin graduar</button>
        <button type="button" class="seg ${d.graded?"on":""}" data-graded="1">Graduada</button>
      </div><input type="hidden" name="graded" value="${d.graded?1:0}"></div>
      <div id="gradedfields" class="fields wide" style="display:${d.graded?"grid":"none"}">
        ${field("grader","Graduadora")}${field("grade","Nota")}${field("cert","Nº de certificado")}
        ${field("pop_grade","POP en esa nota")}${field("pop_total","POP total")}
        ${field("grade_multiplier","Multiplicador de nota",'type="number" step="0.1" min="0"')}
      </div>
      <div id="condfield" class="f" style="display:${d.graded?"none":"flex"}">
        <span>Conservación</span><input name="condition" value="${esc(d.condition||"NM")}"></div>
      ${field("purchase","Precio de compra (€)")}
      ${field("manual_price","Precio fijado a mano (€)")}
      <input type="hidden" name="id_product" value="${esc(d.id_product??"")}">
    </div>

    <div class="block">
      <div class="blockhead"><h3>Ventas anotadas a mano</h3>
        <button type="button" class="ghost sm" id="addsale">+ Añadir venta</button></div>
      <div id="salesrows">${sales.map(saleRow).join("")}</div>
      <p class="hint">Para fútbol, básquet y béisbol: apunta aquí lo pagado (eBay vendidos, 130point, subastas).</p>
    </div>

    <label class="f wide"><span>Notas</span><textarea name="notes" rows="2">${esc(d.notes||"")}</textarea></label>

    <div class="sheetfoot">
      ${d.id ? `<button class="danger" id="del">Eliminar</button>` : ""}
      <span class="spacer"></span>
      <button class="ghost" id="cancel">Cancelar</button>
      <button class="primary" id="save">Guardar carta</button>
    </div>
  </div></div>`;

  const modal = document.getElementById("modal"), sheet = modal.querySelector(".sheet");
  const val = n => sheet.querySelector(`[name="${n}"]`);

  modal.querySelectorAll("[data-graded]").forEach(b => b.onclick = () => {
    const g = b.dataset.graded === "1";
    val("graded").value = g ? 1 : 0;
    modal.querySelectorAll("[data-graded]").forEach(x => x.classList.toggle("on", x === b));
    document.getElementById("gradedfields").style.display = g ? "grid" : "none";
    document.getElementById("condfield").style.display = g ? "none" : "flex";
  });
  val("category").onchange = () => runSearch();

  document.getElementById("addsale").onclick = () => {
    const rows = document.getElementById("salesrows");
    if (rows.children.length < 5) rows.insertAdjacentHTML("beforeend", saleRow({price:"",date:""}));
  };
  modal.addEventListener("click", e => {
    if (e.target.classList.contains("x")) e.target.closest(".salerow").remove();
  });

  /* --- buscador unificado --- */
  let timer = null;
  const fq = document.getElementById("fq");
  const runSearch = async () => {
    const q = fq.value.trim();
    const res = document.getElementById("fres"), src = document.getElementById("fsrc");
    if (q.length < 2) { res.innerHTML = ""; src.textContent = ""; return; }
    src.innerHTML = '<span class="spin"></span>';
    try {
      const r = await api(`/api/search?q=${encodeURIComponent(q)}&cat=${val("category").value}`);
      src.textContent = r.sources.length ? r.sources.join(" + ") : "sin resultados";
      res.innerHTML = r.results.map((p, i) => {
        const price = p.trend ?? p.avg7 ?? p.low;
        const tag = p.origin === "ya en tu colección" ? "mine" : (p.origin.includes("API") ? "api" : "");
        return `<li data-i="${i}" tabindex="0">
          <span><b class="rname">${esc(p.name)}</b>
            <small>${esc([p.expansion, p.number, p.rarity].filter(Boolean).join(" · ") || "—")}</small></span>
          <span class="origin ${tag}">${esc(p.origin)}</span>
          <span class="rprice">${price!=null?eur(price):"—"}${p.snapshot_date?`<br><small>${esc(p.snapshot_date)}</small>`:""}</span>
        </li>`;
      }).join("") || `<li><small>Nada encontrado.</small></li>`;
      if (r.notes.length) document.getElementById("fhint").innerHTML = r.notes.map(esc).join("<br>");
      res.querySelectorAll("li[data-i]").forEach(li => {
        const pick = () => choose(r.results[+li.dataset.i]);
        li.onclick = pick;
        li.onkeydown = e => { if (e.key === "Enter") pick(); };
      });
    } catch (e) { src.textContent = ""; say(e.message, true); }
  };
  fq.oninput = () => { clearTimeout(timer); timer = setTimeout(runSearch, 350); };
  fq.onkeydown = e => { if (e.key === "Enter") { e.preventDefault(); clearTimeout(timer); runSearch(); } };
  document.getElementById("fbtn").onclick = runSearch;

  function choose(p) {
    if (!p) return;
    val("name").value = p.name || val("name").value;
    if (p.expansion) val("collection").value = p.expansion;
    if (p.number) val("number").value = p.number;
    if (p.rarity) val("rarity").value = p.rarity;
    if (p.id_product) {
      val("id_product").value = p.id_product;
      const l = document.getElementById("linked");
      l.textContent = "enlazada · idProduct " + p.id_product; l.classList.remove("no");
    }
    document.getElementById("fres").innerHTML = "";
    document.getElementById("fhint").textContent =
      p.id_product ? "Enlazada. Su precio se comparará solo en cada actualización."
                   : "Sin idProduct: esta categoría no está en Cardmarket, usa las ventas de abajo.";
  }

  document.getElementById("cancel").onclick = () => modal.innerHTML = "";
  modal.querySelector(".scrim").onclick = e => { if (e.target === e.currentTarget) modal.innerHTML = ""; };
  if (d.id) document.getElementById("del").onclick = async () => {
    if (!confirm("¿Eliminar esta carta de la colección?")) return;
    await api("/api/card/" + d.id, {method:"DELETE"});
    modal.innerHTML = ""; load();
  };
  document.getElementById("save").onclick = async () => {
    const body = {id: d.id};
    sheet.querySelectorAll("[name]").forEach(el => body[el.name] = el.value);
    body.sales = [...document.querySelectorAll("#salesrows .salerow")].map(r => ({
      price: r.querySelector(".sp").value, date: r.querySelector(".sd").value
    })).filter(s => s.price !== "");
    try { await api("/api/card", {method:"POST", body: JSON.stringify(body)});
      modal.innerHTML = ""; say(""); load();
    } catch (e) { say(e.message, true); }
  };
  if (!d.id) runSearch();
}

const saleRow = s => `<div class="salerow">
  <input class="sp" value="${esc(s.price??"")}" placeholder="Precio €">
  <input class="sd" type="date" value="${esc(s.date??"")}">
  <button type="button" class="x">×</button></div>`;

/* ------------------------------------------------------------ eventos */

document.getElementById("tabs").addEventListener("click", e => {
  const b = e.target.closest("[data-cat]"); if (!b) return;
  CAT = b.dataset.cat; say(""); render(); setScene(CAT);
});
document.getElementById("list").addEventListener("click", e => {
  const o = e.target.closest("[data-open]"), ed = e.target.closest("[data-edit]");
  if (ed) { openEditor(STATE.cards.find(c => c.id == ed.dataset.edit)); return; }
  if (o) { const id = +o.dataset.open; OPEN = OPEN === id ? null : id; render(); }
});
document.getElementById("q").oninput = e => { Q = e.target.value; render(); };
document.getElementById("basis").onchange = e => { BASIS = e.target.value; load(); };
document.getElementById("add").onclick = () => openEditor(null);
document.getElementById("sync").onclick = async () => {
  say('<span class="spin"></span> Actualizando…');
  try {
    const r = await api("/api/sync", {method:"POST"});
    const live = r.live ? ` · ${r.live.refreshed} cartas refrescadas por API` : "";
    say(`${r.prices} precios y ${r.products} productos importados${live}. ` +
        (r.errors.length ? "Avisos: " + r.errors.map(esc).join(" | ") : r.files.map(esc).join(" · ")),
        r.errors.length > 0);
    load();
  } catch (e) { say(e.message, true); }
};
load(); setScene("all");
</script>
</body>
</html>
"""
