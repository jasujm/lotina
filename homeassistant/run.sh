#!/usr/bin/with-contenv bashio

export MQTT_BROKER=$(bashio::services mqtt "host")
export MQTT_USER=$(bashio::services mqtt "username")
export MQTT_PASSWD=$(bashio::services mqtt "password")

python3 -m lotina process --classify
