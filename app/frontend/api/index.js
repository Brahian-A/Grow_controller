const API_PREFIX = "/api/v1";
const headers = { "Content-Type": "application/json" };

async function req(path, opts = {}) {
  const url = API_PREFIX + path;
  console.log("[API]", url);
  const res = await fetch(url, { ...opts, headers });
  if (!res.ok) {
    console.warn("Error en", url, res.status);
    return null;
  }
  try {
    return await res.json();
  } catch {
    return null;
  }
}

export const getLatest  = () => req("/lecturas/ultima");
export const getHistory = () => req("/lecturas");
export const getConfig  = () => req("/config");
export const putConfig  = (data) => req("/config", { method: "PUT", body: JSON.stringify(data) });
export const getMech    = () => req("/mecanismos");
export const putMech    = (data) => req("/mecanismos", { method: "PUT", body: JSON.stringify(data) });
