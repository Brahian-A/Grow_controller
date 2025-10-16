import { mount } from "../core/dom.js";
import { getHistory } from "../api/index.js";
import { drawLine } from "../ui/Chart.js";

export default async function HistoryView(container){
  const wrap = document.createElement("div");
  wrap.className = "cards";
  wrap.innerHTML = `
    <section class="card"><h3>Temperatura (24)</h3><canvas id="c1" width="360" height="120"></canvas></section>
    <section class="card"><h3>Humedad (24)</h3><canvas id="c2" width="360" height="120"></canvas></section>
    <section class="card"><h3>Suelo (24)</h3><canvas id="c3" width="360" height="120"></canvas></section>
  `;
  mount(container, wrap);

  const history = (await getHistory()).slice(-24).sort((a,b)=> new Date(a.fecha_hora)-new Date(b.fecha_hora));
  drawLine(wrap.querySelector("#c1"), history.map(r=>r.temperatura));
  drawLine(wrap.querySelector("#c2"), history.map(r=>r.humedad));
  drawLine(wrap.querySelector("#c3"), history.map(r=>r.humedad_suelo));
}
