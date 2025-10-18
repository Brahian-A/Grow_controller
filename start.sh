#!/bin/bash

# Esperamos 5 segundos a que conecte a la red
#Wait for 5 seconds to stablish network connection
sleep 5

#Obtenemos la IP de la WAN
#Obtain the WAN IP
IP_WAN=$(hostname -I | awk '{print $1}')

#Si no hay IP, iniciamos en modo configuracion
#if there is not IP, start un configuration mode
if [ -z "$IP_WAN" ]; then
    echo "Sin conexión a la red. Iniciando en modo configuración."

    sudo systemctl start hostapd
    sudo systemctl start dnsmasq

    APP_MODE=CONFIGURATION /home/gibbs/Grow_controller/venv/bin/python3 /home/gibbs/Grow_controller/run.py

#si hay IP, iniciamos en modo normal
#if there is an IP, start in normal mode
else
    echo "Conexión establecida. Iniciando en modo normal."

    sudo systemctl stop hostapd
    sudo systemctl stop dnsmasq

    APP_MODE=NORMAL /home/gibbs/Grow_controller/venv/bin/python3 /home/gibbs/Grow_controller/run.py
fi
