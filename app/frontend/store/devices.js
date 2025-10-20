const KEY = "active_esp_id";

export async function fetchDevices(){
  const res = await fetch("/api/v1/dispositivos");
  if (!res.ok) return [];
  return res.json();
}

export function getActiveEsp(){
  return localStorage.getItem(KEY);
}

export function setActiveEsp(esp_id){
  localStorage.setItem(KEY, esp_id);
  window.dispatchEvent(new CustomEvent("esp:changed", { detail:{ esp_id } }));
}
