#!/bin/bash

# Este comando hace que el script se detenga si cualquier comando falla.
set -e

sleep 8

IP_WLAN=$(ip -4 addr show dev wlan0 | awk '/inet /{print $2}' | cut -d/ -f1 || true)

if [ -z "$IP_WLAN" ];
then
  echo "[start] Sin IP en wlan0. Asegurando hotspot y entrando en CONFIGURATION."

  # Usaremos un perfil de conexión persistente para el hotspot, es más estable.
  # Primero, comprobamos si el perfil ya existe.
  if ! nmcli connection show "Greenhouse-Hotspot" &> /dev/null; then
    echo "[start] Creando perfil de hotspot 'Greenhouse-Hotspot' por primera vez."
    sudo nmcli connection add type wifi ifname wlan0 con-name "Greenhouse-Hotspot" autoconnect no ssid "Greenhouse_Setup"
    sudo nmcli connection modify "Greenhouse-Hotspot" 802-11-wireless.mode ap 802-11-wireless.band bg ipv4.method shared
    sudo nmcli connection modify "Greenhouse-Hotspot" wifi-sec.key-mgmt wpa-psk
    sudo nmcli connection modify "Greenhouse-Hotspot" wifi-sec.psk "12345678"
  fi

  # Activamos el hotspot usando el perfil.
  echo "[start] Activando hotspot..."
  sudo nmcli connection up "Greenhouse-Hotspot"

  echo "[start] Hotspot activado. Lanzando la aplicación en modo CONFIGURATION."
  APP_MODE=CONFIGURATION /home/gibbs/Grow_controller/venv/bin/python3 /home/gibbs/Grow_controller/run.py

else
  echo "[start] wlan0 con IP ${IP_WLAN}. Entrando en NORMAL."
  # Nos aseguramos de que el hotspot esté apagado.
  sudo nmcli connection down "Greenhouse-Hotspot" 2>/dev/null || true

  APP_MODE=NORMAL /home/gibbs/Grow_controller/venv/bin/python3 /home/gibbs/Grow_controller/run.py
fi