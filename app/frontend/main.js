import { startRouter, addRoute } from "./core/router.js";
import DashboardView from "./views/DashboardView.js";
import HistoryView from "./views/HistoryView.js";
import LogsView from "./views/LogsView.js";
import ActuatorsView from "./views/ActuatorsView.js";
import ConfigView from "./views/ConfigView.js";

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

// Rutas
addRoute("/dashboard", DashboardView);
addRoute("/history",   HistoryView);
addRoute("/logs",      LogsView);
addRoute("/actuators", ActuatorsView);
addRoute("/config",    ConfigView);

startRouter(document.getElementById("app"));
