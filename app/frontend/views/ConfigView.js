import { mount } from "../core/dom.js";
import { getConfig, putConfig } from "../api/index.js";

async function suggestByPlant(plantName){
  const res = await fetch("/ai/planta", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ planta: plantName })
  });
  return res.json();
}

export default async function ConfigView(container){
  const form = document.createElement("form");
  form.className = "form";
  mount(container, form);

  const c = await getConfig();

  form.innerHTML = `
    <div class="card" style="padding:16px">
      <h3 style="margin:0 0 8px">Umbrales</h3>

      <label>Temp. umbral alto (°C)
        <input type="number" name="temperatura_umbral_alto" value="${c.temperatura_umbral_alto}">
      </label>
      <label>Temp. umbral bajo (°C)
        <input type="number" name="temperatura_umbral_bajo" value="${c.temperatura_umbral_bajo}">
      </label>

      <label>Humedad umbral alto (%)
        <input type="number" name="humedad_umbral_alto" value="${c.humedad_umbral_alto}">
      </label>
      <label>Humedad umbral bajo (%)
        <input type="number" name="humedad_umbral_bajo" value="${c.humedad_umbral_bajo}">
      </label>

      <label>Suelo umbral alto (%)
        <input type="number" name="humedad_suelo_umbral_alto" value="${c.humedad_suelo_umbral_alto}">
      </label>
      <label>Suelo umbral bajo (%)
        <input type="number" name="humedad_suelo_umbral_bajo" value="${c.humedad_suelo_umbral_bajo}">
      </label>
    </div>

    <div class="card" style="padding:16px">
      <h3 style="margin:0 0 8px">¿Cuál es tu planta?</h3>
      <input type="text" name="planta" placeholder="ej: tomate cherry" style="opacity:.9" />
    </div>

    <button type="submit" class="btn" style="margin-top:6px">Guardar</button>
  `;

  form.addEventListener("submit", async (e)=>{
    e.preventDefault();
    const raw = Object.fromEntries(new FormData(form).entries());

    const plant = (raw.planta || "").trim();
    if (plant){
      const suggested = await suggestByPlant(plant);
      ["temperatura_umbral_alto","temperatura_umbral_bajo",
       "humedad_umbral_alto","humedad_umbral_bajo",
       "humedad_suelo_umbral_alto","humedad_suelo_umbral_bajo"
      ].forEach(k=>{
        const v = suggested?.[k];
        const inp = form.querySelector(`input[name="${k}"]`);
        if (inp && v != null) inp.value = v;
      });
    }

    const data = Object.fromEntries(new FormData(form).entries());
    await putConfig({
      id: c.id,
      temperatura_umbral_alto: Number(data.temperatura_umbral_alto),
      temperatura_umbral_bajo: Number(data.temperatura_umbral_bajo),
      humedad_umbral_alto: Number(data.humedad_umbral_alto),
      humedad_umbral_bajo: Number(data.humedad_umbral_bajo),
      humedad_suelo_umbral_alto: Number(data.humedad_suelo_umbral_alto),
      humedad_suelo_umbral_bajo: Number(data.humedad_suelo_umbral_bajo),
    });
  });
}
