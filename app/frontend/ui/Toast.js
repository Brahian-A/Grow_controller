let wrap = null;
function ensureWrap(){
  if (!wrap){
    wrap = document.createElement("div");
    wrap.id = "toast-wrap";
    document.body.appendChild(wrap);
  }
}
export function toast(msg, type="info"){
  ensureWrap();
  const t = document.createElement("div");
  t.className = `toast toast--${type}`;
  t.innerHTML = `<div class="toast-msg">${msg}</div>`;
  wrap.appendChild(t);
  requestAnimationFrame(()=> t.classList.add("in"));
  setTimeout(()=> t.classList.remove("in"), 2500);
  setTimeout(()=> t.remove(), 2800);
}
