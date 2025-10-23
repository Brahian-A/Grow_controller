#!/bin/bash
# Inicia en modo CONFIGURATION si wlan0 no tiene IP; crea hotspot con nmcli.
# Si ya tiene IP, arranca modo NORMAL.

sleep 8

# Detecta IP de wlan0 (solo IPv4)
IP_WLAN=$(ip -4 addr show dev wlan0 | awk '/inet /{print $2}' | cut -d/ -f1)

if [ -z "$IP_WLAN" ]; then
  echo "[start] Sin IP en wlan0. Creando hotspot y entrando en CONFIGURATION."
  # Asegura que NM maneje la interfaz
  sudo /usr/bin/nmcli dev disconnect wlan0 2>/dev/null
  # Crea/levanta hotspot (SSID+clave puedes cambiarlos)
  sudo /usr/bin/nmcli dev wifi hotspot ifname wlan0 ssid Greenhouse_Setup password 12345678

  APP_MODE=CONFIGURATION /home/gibbs/Grow_controller/venv/bin/python3 /home/gibbs/Grow_controller/run.py
else
  echo "[start] wlan0 con IP ${IP_WLAN}. Entrando en NORMAL."
  # Apaga hotspot si existiera
  nmcli connection down Hotspot 2>/dev/null || true

  APP_MODE=NORMAL /home/gibbs/Grow_controller/venv/bin/python3 /home/gibbs/Grow_controller/run.py
fi
