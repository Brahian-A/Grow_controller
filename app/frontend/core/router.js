const routes = new Map();

export function addRoute(path, renderFn) {
  routes.set(path, renderFn);
}

export function startRouter(container) {
  const render = () => {
    let path = location.hash.replace(/^#/, "");
    if (!path) path = "/dashboard";
    const view = routes.get(path) || routes.get("/dashboard");
    container.innerHTML = "";
    if (view) view(container);
    document.querySelectorAll("#sidebar nav a").forEach(a => {
      a.classList.toggle("is-active", a.getAttribute("href") === `#${path}`);
    });
  };
  window.addEventListener("hashchange", render);
  render();
}
