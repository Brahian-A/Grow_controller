import { mount } from "../core/dom.js";
import { getConfig, putConfig } from "../api/index.js";

export default async function ConfigView(container){
  const form = document.createElement("form");
  form.className = "form";
  mount(container, form);

  const c = await getConfig();

  form.innerHTML = `
    <div class="card" style="padding:16px">
      <h3 style="margin:0 0 8px">Umbrales</h3>

      <label>Temperatura (°C)
        <input type="number" name="temperatura" value="${c?.temperatura ?? 35}">
      </label>

      <label>Humedad Ambiente (%)
        <input type="number" name="humedad_ambiente" value="${c?.humedad_ambiente ?? 30}">
      </label>

      <label>Humedad de Suelo (%)
        <input type="number" name="humedad_suelo" value="${c?.humedad_suelo ?? 55}">
      </label>

      <label>Margen (≥5)
        <input type="number" name="margen" min="5" value="${c?.margen ?? 5}">
      </label>
    </div>

    <button type="submit" class="btn" style="margin-top:6px">Guardar</button>
  `;

  form.addEventListener("submit", async (e)=>{
    e.preventDefault();
    const data = Object.fromEntries(new FormData(form).entries());
    const payload = {
      temperatura: Number(data.temperatura),
      humedad_ambiente: Number(data.humedad_ambiente),
      humedad_suelo: Number(data.humedad_suelo),
      margen: Number(data.margen),
    };
    await putConfig(payload);
    alert("Configuración guardada ✅");
  });


  window.addEventListener("esp:changed", async ()=>{
    const nc = await getConfig();
    if (!nc) return;
    form.querySelector('input[name="temperatura"]').value = nc.temperatura ?? 35;
    form.querySelector('input[name="humedad_ambiente"]').value = nc.humedad_ambiente ?? 30;
    form.querySelector('input[name="humedad_suelo"]').value = nc.humedad_suelo ?? 55;
    form.querySelector('input[name="margen"]').value = nc.margen ?? 5;
  }, { passive:true });
}
