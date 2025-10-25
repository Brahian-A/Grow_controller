import { startRouter, addRoute } from "./core/router.js";
import DashboardView from "./views/DashboardView.js";
import HistoryView from "./views/HistoryView.js";
import LogsView from "./views/LogsView.js";
import ActuatorsView from "./views/ActuatorsView.js?v=13";
import ConfigView from "./views/ConfigView.js";
import { fetchDevices } from "./store/devices.js";
import { getActiveEsp, setActiveEsp } from "./store/devices.js";
import { addDevice } from "./api/index.js";

function toggleMenu(){ document.body.classList.toggle('menu-open'); }
function closeMenu(){ document.body.classList.remove('menu-open'); }

document.addEventListener('click', e=>{
  if (e.target.closest('#btn-menu')) { toggleMenu(); return; }
  if (e.target.id === 'backdrop') { closeMenu(); return; }
  const link = e.target.closest('#sidebar nav a');
  if (link) {
    const href = link.getAttribute('href');
    if (href?.startsWith('#/')) location.hash = href.slice(1);
    closeMenu();
  }
});
document.addEventListener('keydown', e=>{ if (e.key === 'Escape') closeMenu(); });


async function initDevicesUI(){
  const sel = document.getElementById("device-select");
  const btnAdd = document.getElementById("btn-add-device");
  const devices = await fetchDevices();

  // poblar selector
  sel.innerHTML = devices.map(d => `<option value="${d.esp_id}">${d.nombre || d.esp_id}</option>`).join("");

  
  let active = getActiveEsp();
  if (!active && devices.length === 1) active = devices[0].esp_id;
  if (active) sel.value = active; else sel.selectedIndex = -1;

  sel.addEventListener("change", () => {
    setActiveEsp(sel.value);
  });

  // agregar dispositivo
  btnAdd.addEventListener("click", async () => {
    const esp_id = prompt("ESP ID (ej: esp32s3-ABC123):");
    if (!esp_id) return;
    const nombre = prompt("Nombre (opcional):") || null;
    const res = await addDevice({ esp_id, nombre });
    if (res) {
      const opt = document.createElement("option");
      opt.value = res.esp_id;
      opt.textContent = res.nombre || res.esp_id;
      sel.appendChild(opt);
      sel.value = res.esp_id;
      setActiveEsp(res.esp_id);
    } else {
      alert("No se pudo crear el dispositivo (quizás ya existe).");
    }
  });
}

addRoute("/dashboard", DashboardView);
addRoute("/history",   HistoryView);
addRoute("/logs",      LogsView);
addRoute("/actuators", ActuatorsView);
addRoute("/config",    ConfigView);

initDevicesUI().then(() => {
  startRouter(document.getElementById("app"));
});
