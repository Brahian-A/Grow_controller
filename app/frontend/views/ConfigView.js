import { mount } from "../core/dom.js";
import { getConfig, putConfig, queryPlant } from "../api/index.js";
import { toast } from "../ui/Toast.js";

export default async function ConfigView(container){
  const form = document.createElement("form");
  form.className = "form";
  mount(container, form);

  const c = await getConfig();

  form.innerHTML = `
    <div class="card" style="padding:16px; margin-bottom: 16px;">
      <h3 style="margin:0 0 8px">✨ Autoconfiguración con IA</h3>
      <label for="plant-name">Ingresa el nombre de una planta</label>
      <div style="display:flex; gap: 8px; margin-top: 4px;">
        <input type="text" id="plant-name" placeholder="Ej: Lechuga, Tomate, etc." style="flex-grow: 1;">
        <button type="button" id="btn-autoconfig" class="btn">Aplicar</button>
      </div>
    </div>

    <div class="card" style="padding:16px">
      <h3 style="margin:0 0 8px">Umbrales Manuales</h3>

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

    <button type="submit" class="btn" style="margin-top:6px">Guardar Cambios Manuales</button>
  `;

  const btnAutoconfig = form.querySelector("#btn-autoconfig");
  const inputPlantName = form.querySelector("#plant-name");

  btnAutoconfig.addEventListener("click", async () => {
    const plantName = inputPlantName.value.trim();
    if (!plantName) {
      toast("Por favor, ingresa el nombre de una planta.", "warn");
      return;
    }

    btnAutoconfig.disabled = true;
    btnAutoconfig.textContent = "Consultando...";

    try {
      // 1. Llama a la API de Gemini
      const conditions = await queryPlant(plantName);
      if (conditions.__error) {
        throw new Error(conditions.detail || "No se pudo obtener la configuración.");
      }

      // 2. Llama a la API para guardar la nueva configuración
      const updatedConfig = await putConfig(conditions);
      if (updatedConfig.__error) {
        throw new Error(updatedConfig.detail || "No se pudo guardar la configuración.");
      }
      
      // 3. Actualiza los valores en el formulario
      form.querySelector('input[name="temperatura"]').value = updatedConfig.temperatura;
      form.querySelector('input[name="humedad_ambiente"]').value = updatedConfig.humedad_ambiente;
      form.querySelector('input[name="humedad_suelo"]').value = updatedConfig.humedad_suelo;

      toast(`✅ Configuración para '${plantName}' aplicada con éxito.`);

    } catch (err) {
      toast(`❌ Error: ${err.message}`, "err");
    } finally {
      btnAutoconfig.disabled = false;
      btnAutoconfig.textContent = "Aplicar";
    }
  });

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
    toast("Configuración guardada ✅");
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
