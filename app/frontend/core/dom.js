export const qs = (sel, ctx = document) => ctx.querySelector(sel);
export const mount = (container, el) => {
  container.innerHTML = "";
  container.appendChild(el);
};
