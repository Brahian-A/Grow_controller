const headers = { "Content-Type": "application/json" };
async function req(path, opts = {}) {
  const res = await fetch(path, { ...opts, headers });
  return res.ok ? res.json() : null;
}

export const getLatest  = () => req("/lecturas/ultima");
export const getHistory = () => req("/lecturas");
export const getConfig  = () => req("/config");
export const putConfig  = data => req("/config", { method: "PUT", body: JSON.stringify(data) });
export const getMech    = () => req("/mecanismos");
export const putMech    = data => req("/mecanismos", { method: "PUT", body: JSON.stringify(data) });
