#!/bin/bash
set -e
sleep 8

IP_WLAN=$(ip -4 addr show dev wlan0 | awk '/inet /{print $2}' | cut -d/ -f1 || true)

# Limpieza (como root, no necesitamos sudo)
killall hostapd 2>/dev/null || true
systemctl stop dnsmasq 2>/dev/null || true

if [ -z "$IP_WLAN" ];
then
  echo "[start] Sin IP en wlan0. Lanzando hotspot con hostapd."

  # 1. Asignamos una IP estática a wlan0
  ip addr flush dev wlan0
  ip addr add 10.42.0.1/24 dev wlan0

  # 2. Creamos configs si no existen
  if [ ! -f /etc/hostapd/hostapd.conf ]; then
    echo "interface=wlan0
driver=nl80211
ssid=GrowController
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=12345678
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP" > /etc/hostapd/hostapd.conf
  fi
  
  if [ ! -f /etc/dnsmasq.d/090-hotspot.conf ]; then
     echo "interface=wlan0
dhcp-range=10.42.0.50,10.42.0.150,255.255.255.0,24h" > /etc/dnsmasq.d/090-hotspot.conf
  fi

  # 3. Iniciamos los servicios
  systemctl start dnsmasq
  nohup hostapd /etc/hostapd/hostapd.conf &

  echo "[start] Hotspot activado. Lanzando la aplicación en modo CONFIGURATION."
  APP_MODE=CONFIGURATION /home/gibbs/Grow_controller/venv/bin/python3 /home/gibbs/Grow_controller/run.py

else
  echo "[start] wlan0 con IP ${IP_WLAN}. Entrando en NORMAL."
  APP_MODE=NORMAL /home/gibbs/Grow_controller/venv/bin/python3 /home/gibbs/Grow_controller/run.py
fi