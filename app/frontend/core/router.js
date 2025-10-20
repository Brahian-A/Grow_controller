const routes = new Map();
let currentCleanup = null;

export function addRoute(path, renderFn) {
  routes.set(path, renderFn);
}

export function startRouter(container) {
  const render = () => {
    if (typeof currentCleanup === "function") {
      try { currentCleanup(); } catch {}
    }

    let path = location.hash.replace(/^#/, "");
    if (!path) path = "/dashboard";

    const view = routes.get(path) || routes.get("/dashboard");
    container.innerHTML = "";
    currentCleanup = view ? view(container) : null;

    document.querySelectorAll("#sidebar nav a").forEach(a => {
      a.classList.toggle("is-active", a.getAttribute("href") === `#${path}`);
    });
  };

  window.addEventListener("hashchange", render);
  window.addEventListener("esp:changed", render, { passive: true });

  render();
}
