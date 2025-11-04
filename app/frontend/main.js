import { startRouter, addRoute } from "./core/router.js";
import DashboardView from "./views/DashboardView.js";
import HistoryView from "./views/HistoryView.js";
import LogsView from "./views/LogsView.js";
import ActuatorsView from "./views/ActuatorsView.js?v=13";
import ConfigView from "./views/ConfigView.js";
import { loadDevices, listDevices, getActiveEsp, setActiveEsp } from "./store/devices.js";
import { editDevice } from "./api/index.js";
import { toast } from "./ui/Toast.js";

const sidebar = document.getElementById("sidebar");
const btnMenu = document.getElementById("btn-menu");
const backdrop = document.getElementById("backdrop");

function openMenu() {
  document.body.classList.add("menu-open");
  if (sidebar) sidebar.hidden = false;
  if (backdrop) backdrop.style.display = "block";
  if (btnMenu) btnMenu.setAttribute("aria-expanded", "true");
}

function closeMenu() {
  document.body.classList.remove("menu-open");
  if (sidebar) sidebar.hidden = true;
  if (backdrop) backdrop.style.display = "none";
  if (btnMenu) btnMenu.setAttribute("aria-expanded", "false");
}

function toggleMenu() {
  const expanded = btnMenu?.getAttribute("aria-expanded") === "true";
  if (expanded) closeMenu();
  else openMenu();
}

document.addEventListener("click", (e) => {
  if (e.target.closest("#btn-menu")) {
    toggleMenu();
    return;
  }
  if (e.target.id === "backdrop") {
    closeMenu();
    return;
  }
  const link = e.target.closest("#sidebar nav a");
  if (link) {
    const href = link.getAttribute("href");
    if (href?.startsWith("#/")) {
      location.hash = href.slice(1);
    }
    closeMenu();
  }
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeMenu();
});

async function initDevicesUI() {
  const sel = document.getElementById("device-select");
  const btnEdit = document.getElementById("btn-edit-device");

  await loadDevices();
  const devices = listDevices();

  sel.innerHTML = devices
    .map((d) => `<option value="${d.esp_id}">${d.nombre || d.esp_id}</option>`)
    .join("");

  let active = getActiveEsp();
  if (active) sel.value = active;
  else sel.selectedIndex = devices.length ? 0 : -1;

  sel.addEventListener("change", () => {
    setActiveEsp(sel.value);
  });

  btnEdit.addEventListener("click", async () => {
    const currentEspId = getActiveEsp();
    if (!currentEspId) {
      toast("No hay ningún dispositivo seleccionado.", "warn");
      return;
    }

    const currentDevice = devices.find(d => d.esp_id === currentEspId);
    const newName = prompt("Ingresa el nuevo nombre para:", currentDevice.nombre || currentDevice.esp_id);

    if (newName === null || newName.trim() === "") return;

    const res = await editDevice(currentEspId, { nombre: newName });
    if (res && !res.__error) {
      toast("Nombre actualizado con éxito ✅");

      const opt = sel.querySelector(`option[value="${currentEspId}"]`);
      if (opt) opt.textContent = res.nombre || res.esp_id;

      currentDevice.nombre = res.nombre;
    } else {
      toast("No se pudo actualizar el nombre.", "err");
    }
  });
}

addRoute("/dashboard", DashboardView);
addRoute("/history", HistoryView);
addRoute("/logs", LogsView);
addRoute("/actuators", ActuatorsView);
addRoute("/config", ConfigView);

initDevicesUI()
  .catch(console.warn)
  .finally(() => {
    startRouter(document.getElementById("app"));
  });
