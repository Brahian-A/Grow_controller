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
      <div class="a-title">Encender luces</div>
    </div>

    <div class="a-card a-click" id="card-vent">
      <div class="a-icon"><img src="./assets/img/ventilacion.png" alt="Ventilación"></div>
      <div class="a-title">Ventilación</div>
    </div>

    <div class="a-card a-click" id="card-riego">
      <div class="a-icon"><img src="./assets/img/regar.png" alt="Riego"></div>
      <div class="a-title">Activar riego</div>
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

  let mech = null;
  let timer = null;
  let running = true;
  let busy = false;

  function paintStates(){
    if (!mech) return;
    cardLuces.classList.toggle("active", !!mech.luz);
    cardVent.classList.toggle("active",  !!mech.ventilador);
    cardRiego.classList.toggle("active", !!mech.bomba);
  }
  function paintWater(pct){
    const p = clampPct(pct);
    bar.style.width = `${p}%`;
    porc.textContent = `${p}%`;
    label.textContent = nivelEtiqueta(p);
  }

  async function refresh(){
    try{
      const [m, latest] = await Promise.all([
        getMech(),
        getLatest()
      ]);
      mech = m;
      paintStates();
      paintWater(latest?.nivel_de_agua);
    }catch(e){
    }finally{
      if (running) timer = setTimeout(refresh, 5000);
    }
  }

  async function toggle(field){
  if (!mech || busy) return;
  busy = true;
  try{
    const payload = { [field]: !mech[field] };
    const updated = await putMech(payload);
    mech = { ...mech, ...updated };
    paintStates();
  }catch(e){
    console.warn("toggle error", field, e);
  }finally{
    busy = false;
  }
}

async function stopAll(){
  if (!mech || busy) return;
  busy = true;
  try{
    const payload = { bomba:false, luz:false, ventilador:false };
    const updated = await putMech(payload);
    mech = { ...mech, ...updated };
    paintStates();
  }catch(e){
    console.warn("stopAll error", e);
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

  refresh();
  return () => { running = false; if (timer) clearTimeout(timer); };
}
