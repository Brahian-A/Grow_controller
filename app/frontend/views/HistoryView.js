import { mount } from "../core/dom.js";
import { getHistory } from "../api/index.js";
import { drawLine } from "../ui/Chart.js";

export default function HistoryView(container){
  const wrap = document.createElement("div");
  wrap.className = "cards";
  wrap.innerHTML = `
    <section class="card"><h3>Temperatura (24)</h3><canvas id="c1" width="360" height="120"></canvas></section>
    <section class="card"><h3>Humedad (24)</h3><canvas id="c2" width="360" height="120"></canvas></section>
    <section class="card"><h3>Suelo (24)</h3><canvas id="c3" width="360" height="120"></canvas></section>
  `;
  mount(container, wrap);

  const c1 = wrap.querySelector("#c1");
  const c2 = wrap.querySelector("#c2");
  const c3 = wrap.querySelector("#c3");

  let timer = null;
  let running = true;

  async function refresh(){
    try{
      const history = (await getHistory()) || [];
      const last24 = history.slice(-24).sort((a,b)=> new Date(a.fecha_hora)-new Date(b.fecha_hora));
      drawLine(c1, last24.map(r=>r.temperatura));
      drawLine(c2, last24.map(r=>r.humedad));
      drawLine(c3, last24.map(r=>r.humedad_suelo));
    }catch(e){
      // silencioso
    }finally{
      if (running) timer = setTimeout(refresh, 5000);
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
