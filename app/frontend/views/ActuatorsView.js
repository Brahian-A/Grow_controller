import { mount } from "../core/dom.js";
import { getMech, putMech, getLatest } from "../api/index.js";

function clampPct(v){
  const n = Number(v);
  if (!Number.isFinite(n)) return 0;
  return Math.max(0, Math.min(100, n));
}
function nivelEtiqueta(p){
  if (p < 30) return "Tanque bajo";
  if (p < 70) return "Tanque medio";
  return "Tanque alto";
}

export default function ActuatorsView(container){
  const wrap = document.createElement("div");
  wrap.className = "actions-grid";
  mount(container, wrap);

  wrap.innerHTML = `
    <div class="a-card a-click" id="card-luces">
      <div class="a-icon"><img src="./assets/img/luces.png" alt="Luces"></div>
      <div class="a-title">Luces</div>
      <div class="a-status" id="status-luces">OFF</div>
    </div>

    <div class="a-card a-click" id="card-vent">
      <div class="a-icon"><img src="./assets/img/ventilacion.png" alt="Ventilación"></div>
      <div class="a-title">Ventilación</div>
      <div class="a-status" id="status-vent">OFF</div>
    </div>

    <div class="a-card a-click" id="card-riego">
      <div class="a-icon"><img src="./assets/img/regar.png" alt="Riego"></div>
      <div class="a-title">Riego</div>
      <div class="a-status" id="status-riego">OFF</div>
    </div>

    <div class="a-card" id="card-agua">
      <div class="a-title">🚿 Nivel de agua</div>
      <div class="progress"><div class="progress__bar" id="bar-agua" style="width:0%"></div></div>
      <div class="agua-meta">
        <span id="agua-porc">—%</span>
        <span id="agua-label" class="muted">—</span>
      </div>
    </div>

    <button class="big-danger" id="btn-stop">Detener todo</button>
  `;

  // refs
  const cardLuces = wrap.querySelector("#card-luces");
  const cardVent  = wrap.querySelector("#card-vent");
  const cardRiego = wrap.querySelector("#card-riego");
  const btnStop   = wrap.querySelector("#btn-stop");
  const bar       = wrap.querySelector("#bar-agua");
  const porc      = wrap.querySelector("#agua-porc");
  const label     = wrap.querySelector("#agua-label");

  const stLuces = wrap.querySelector("#status-luces");
  const stVent  = wrap.querySelector("#status-vent");
  const stRiego = wrap.querySelector("#status-riego");

  let mech = null;
  let timer = null;
  let running = true;
  let busy = false;

  function setStatus(el, on){
    if (!el) return;
    el.textContent = on ? "ON" : "OFF";
    el.classList.toggle("is-on", !!on);
  }

  function paintStates(){
    if (!mech) return;
    cardLuces.classList.toggle("active", !!mech.luz);
    setStatus(stLuces, mech.luz);

    cardVent.classList.toggle("active",  !!mech.ventilador);
    setStatus(stVent, mech.ventilador);

    cardRiego.classList.toggle("active", !!mech.bomba);
    setStatus(stRiego, mech.bomba);
  }
  function paintWater(pct){
    const p = clampPct(pct);
    bar.style.width = `${p}%`;
    porc.textContent = `${p}%`;
    label.textContent = nivelEtiqueta(p);
  }

  async function refresh(){
    try{
      const [m, latest] = await Promise.all([ getMech(), getLatest() ]);

      if (!m?.__error && m) {
        mech = m;
        paintStates();
      }
      if (!latest?.__error && latest?.nivel_de_agua != null) {
        paintWater(latest.nivel_de_agua);
      }
    }catch(e){
      // silenciar
    }finally{
      if (running) timer = setTimeout(refresh, 5000);
    }
  }

  async function toggle(field){
    if (!mech || busy) return;
    busy = true;
    try{
      const nextVal = !mech[field];
      mech = { ...mech, [field]: nextVal };
      paintStates();

      const updated = await putMech({ [field]: nextVal });

      if (updated?.__error) {
        return;
      }
      if (updated) {
        mech = { ...mech, ...updated };
        paintStates();
      }
    }catch(e){
    }finally{
      busy = false;
    }
  }

  async function stopAll(){
    if (!mech || busy) return;
    busy = true;
    try{
      mech = { ...mech, bomba:false, luz:false, ventilador:false };
      paintStates();

      const updated = await putMech({ bomba:false, luz:false, ventilador:false });

      if (updated?.__error) {
        return;
      }
      if (updated) {
        mech = { ...mech, ...updated };
        paintStates();
      }
    }catch(e){
    }finally{
      busy = false;
    }
  }

  wrap.addEventListener("click", (e)=>{
    if (e.target.closest("#card-luces")) toggle("luz");
    else if (e.target.closest("#card-vent"))  toggle("ventilador");
    else if (e.target.closest("#card-riego")) toggle("bomba");
    else if (e.target.closest("#btn-stop"))   stopAll();
  });

  // al cambiar de dispositivo limpiar UI y refresca
  window.addEventListener("esp:changed", () => {
    if (timer) clearTimeout(timer);
    mech = { luz:false, ventilador:false, bomba:false };
    paintStates();
    paintWater(0);
    refresh();
  }, { passive:true });

  refresh();
  return () => { running = false; if (timer) clearTimeout(timer); };
}