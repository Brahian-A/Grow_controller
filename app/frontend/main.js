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

function showNamePrompt(currentName) {
  return new Promise((resolve) => {
    const modal = document.createElement("div");
    modal.className = "edit-prompt";
    modal.innerHTML = `
      <h3 style="margin-top:0">Editar Nombre</h3>
      <input type="text" id="modal-input-name" value="">
      <div class="modal-actions">
        <button id="modal-btn-cancel" class="btn btn-secondary">Cancelar</button>
        <button id="modal-btn-save" class="btn">Guardar</button>
      </div>
    `;
    document.body.appendChild(modal);

    const backdrop = document.getElementById("backdrop");
    if (backdrop) backdrop.style.display = "block";

    const input = modal.querySelector("#modal-input-name");
    input.value = currentName;
    input.focus();
    input.select();

    const cleanup = (value) => {
      if (backdrop) backdrop.style.display = "none";
      modal.remove();
      resolve(value);
    };

    modal.querySelector("#modal-btn-save").onclick = () => {
      cleanup(input.value);
    };
    modal.querySelector("#modal-btn-cancel").onclick = () => {
      cleanup(null);
    };
    if (backdrop) {
      backdrop.onclick = () => cleanup(null);
    }
  });
}

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
    
    const newName = await showNamePrompt(currentDevice.nombre || currentDevice.esp_id);

    if (newName === null) {
      return; 
    }

    const res = await editDevice(currentEspId, { nombre: newName.trim() });
    if (res && !res.__error) {
      toast("Nombre actualizado con éxito ✅");
      const opt = sel.querySelector(`option[value="${currentEspId}"]`);
      if (opt) opt.textContent = res.nombre || res.esp_id;
      if (currentDevice) currentDevice.nombre = res.nombre;
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
