import { mount } from "../core/dom.js";
import { getLatest, getHistory } from "../api/index.js";
import { drawLine } from "../ui/Chart.js";

export default function DashboardView(container){
  const wrap = document.createElement("div");
  wrap.className = "cards";
  wrap.innerHTML = `
    <section class="kpi"><div class="label">Temperatura</div><div class="value" id="kpi-temp">—</div><div class="sub" id="ts" style="color:#6b7280;font-size:12px;margin-top:4px;"></div></section>
    <section class="kpi"><div class="label">Humedad ambiente</div><div class="value" id="kpi-hum">—</div></section>
    <section class="kpi"><div class="label">Humedad de suelo</div><div class="value" id="kpi-soil">—</div></section>
    <section class="card"><h3>Histórico 24 lecturas (temperatura)</h3><canvas id="chart" width="360" height="120"></canvas></section>
  `;
  mount(container, wrap);

  const elTemp = wrap.querySelector("#kpi-temp");
  const elHum  = wrap.querySelector("#kpi-hum");
  const elSoil = wrap.querySelector("#kpi-soil");
  const elTs   = wrap.querySelector("#ts");
  const canvas = wrap.querySelector("#chart");

  const fmt = (v, suf="") => (v==null || Number.isNaN(+v)) ? "—" : `${Math.round(+v*10)/10}${suf}`;

  let timer = null;
  let running = true;

  async function refresh(){
    try{
      const [latest, historyRaw] = await Promise.all([ getLatest(), getHistory() ]);

      const okLatest = latest && !latest.__error ? latest : null;
      if (okLatest){
        const tempTxt = fmt(okLatest.temperatura,"°C"); if (elTemp.textContent !== tempTxt) elTemp.textContent = tempTxt;
        const humTxt  = fmt(okLatest.humedad,"%");       if (elHum.textContent  !== humTxt)  elHum.textContent  = humTxt;
        const soilTxt = fmt(okLatest.humedad_suelo,"%"); if (elSoil.textContent !== soilTxt) elSoil.textContent = soilTxt;
        const ts = okLatest.fecha_hora ? new Date(okLatest.fecha_hora).toLocaleTimeString() : "";
        elTs.textContent = ts ? `Actualizado ${ts}` : "";
      } else {
        elTemp.textContent = "—"; elHum.textContent = "—"; elSoil.textContent = "—"; elTs.textContent = "";
      }

      const history = Array.isArray(historyRaw) ? historyRaw : [];
      const last24 = history.slice(-24).sort((a,b)=> new Date(a.fecha_hora)-new Date(b.fecha_hora));
      drawLine(canvas, last24.map(r => r.temperatura ?? null));
    }catch(e){
    }finally{
      if (running) timer = setTimeout(refresh, 4000);
    }
  }

  const onEspChanged = () => { if (timer) clearTimeout(timer); refresh(); };
  window.addEventListener("esp:changed", onEspChanged, { passive:true });

  refresh();

  return () => {
    running = false;
    if (timer) clearTimeout(timer);
    window.removeEventListener("esp:changed", onEspChanged);
  };
}
