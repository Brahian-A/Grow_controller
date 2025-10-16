import { mount } from "../core/dom.js";
import { getHistory } from "../api/index.js";

export default async function LogsView(container){
  const wrap = document.createElement("div");
  wrap.className = "cards";
  mount(container, wrap);

  wrap.innerHTML = `
    <div class="card">
      <h3>Alertas recientes</h3>
      <div id="alert-container" class="alerts"></div>
    </div>
  `;

  const cont = wrap.querySelector("#alert-container");
  const lecturas = await getHistory();
  const recientes = lecturas.slice(0, 10);

  cont.innerHTML = recientes.map(r => {
    const fecha = new Date(r.fecha_hora).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    let tipo = "ok";
    let mensaje = "✅ Condiciones normales.";

    if (r.nivel_de_agua < 30)      { tipo = "err";  mensaje = "⚠️ Nivel de agua muy bajo."; }
    else if (r.humedad_suelo < 30) { tipo = "warn"; mensaje = "💧 Suelo demasiado seco."; }
    else if (r.temperatura > 35)   { tipo = "warn"; mensaje = "🌡️ Temperatura elevada."; }
    else if (r.humedad > 90)       { tipo = "warn"; mensaje = "☁️ Humedad ambiental muy alta."; }

    return `
      <div class="alert alert--${tipo}">
        <div class="alert-header">
          <span class="alert-time">${fecha}</span>
          <span class="alert-status">${mensaje}</span>
        </div>
        <div class="alert-data">
          🌡️ ${r.temperatura}°C • 💧 Humedad: ${r.humedad}% • 🌱 Suelo: ${r.humedad_suelo}% • 🚿 Agua: ${r.nivel_de_agua}%
        </div>
      </div>
    `;
  }).join("");
}
