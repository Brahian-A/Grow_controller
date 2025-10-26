let devices = [];
let activeEsp = null;

export async function loadDevices() {
  const res = await fetch("/api/v1/dispositivos");
  const arr = await res.json();

  // Normalizamos por si el backend agrega/renombra algo en el futuro
  devices = arr.map(d => ({
    id: d.id,
    esp_id: d.esp_id,
    nombre: d.nombre ?? null,
    activo: !!d.activo,
    ultimo_contacto: d.ultimo_contacto ? new Date(d.ultimo_contacto) : null,
  }));


  if (!activeEsp && devices.length) activeEsp = devices[0].esp_id;
}

export function listDevices() { return devices; }
export function getActiveEsp() { return activeEsp; }
export function setActiveEsp(id) { activeEsp = id; }
