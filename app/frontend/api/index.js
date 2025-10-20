import { getActiveEsp } from "../store/devices.js";

const API_PREFIX = "/api/v1";
const headers = { "Content-Type": "application/json" };

function q(obj){
  const p = new URLSearchParams(obj);
  const s = p.toString();
  return s ? `?${s}` : "";
}

async function req(path, opts = {}, attachEsp = true) {
  let url = API_PREFIX + path;
  const isGET = !opts.method || opts.method.toUpperCase() === "GET";

  //esp_id
  if (attachEsp && isGET) {
    const esp_id = getActiveEsp();
    if (esp_id) url += (url.includes("?") ? "&" : "?") + new URLSearchParams({ esp_id });
  }
  if (attachEsp && !isGET && opts.body && headers["Content-Type"]?.includes("application/json")) {
    try {
      const body = JSON.parse(opts.body);
      const esp = getActiveEsp();
      if (esp && body.esp_id == null) body.esp_id = esp;
      opts.body = JSON.stringify(body);
    } catch {}
  }

  // cache busting en get
  if (isGET) {
    url += (url.includes("?") ? "&" : "?") + `_t=${Date.now()}`;
  }

  // evitar cache del navegador/proxy
  const finalOpts = { ...opts, headers, cache: "no-store" };

  const res = await fetch(url, finalOpts);
  if (!res.ok) {
    console.warn("API error", url, res.status);
    return null;
  }
  try { return await res.json(); } catch { return null; }
}

// lecturas
export const getLatest  = () => req("/lecturas/ultima");
export const getHistory = () => req("/lecturas");

//config
export const getConfig  = () => req("/config");
export const putConfig  = (data) => req("/config", { method: "PUT", body: JSON.stringify(data) });

// mecanismos
export const getMech    = () => req("/mecanismos");
export const putMech    = (data) => req("/mecanismos", { method: "PUT", body: JSON.stringify(data) });

//dispositivos 
export const listDevices = () => req("/dispositivos", {}, false);
export const addDevice   = (data) => req("/dispositivos", { method:"POST", body: JSON.stringify(data) }, false);
export const getDevice   = (esp_id) => req(`/dispositivos/${encodeURIComponent(esp_id)}`, {}, false);
export const editDevice  = (esp_id, data) => req(`/dispositivos/${encodeURIComponent(esp_id)}`, { method:"PUT", body: JSON.stringify(data) }, false);
export const delDevice   = (esp_id) => req(`/dispositivos/${encodeURIComponent(esp_id)}`, { method:"DELETE" }, false);
