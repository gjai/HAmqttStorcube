import os
import logging
import paho.mqtt.client as mqtt
import json
import uuid
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers import device_registry as dr

DOMAIN = "mqttstorcube"
PLATFORMS = ["sensor"]
_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Configuration générale du composant."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Configuration spécifique lors de l'ajout via l'UI."""
    hass.data.setdefault(DOMAIN, {})

    broker = "sonicpo.com"
    port = 1883
    username = "znst"
    password = "znst@2022"
    id_storcube = entry.data["id_storcube"]
    name = entry.data.get("name", f"Storcube {id_storcube}")

    hass.data[DOMAIN][id_storcube] = {
        "entry_id": entry.entry_id,
        "name": name
    }

    client = mqtt.Client(client_id=f"mqttstorcube_{id_storcube}_{uuid.uuid4().hex[:8]}")
    client.username_pw_set(username, password)

    client.user_data_set({"hass": hass, "id_storcube": id_storcube})
    client.on_message = on_message
    client.connect(broker, port, 60)
    client.loop_start()

    topic = f"energy/HES/{id_storcube}/#"
    client.subscribe(topic)

    _LOGGER.info(f"✅ Connexion MQTT à {broker}:{port} et abonnement au topic : {topic}")

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_create_storcube_device(hass, entry.entry_id, id_storcube, name)
    await async_add_dashboard(hass)

    return True

async def async_create_storcube_device(hass, entry_id, id_storcube, name):
    """Créer un appareil Storcube dans Home Assistant."""
    device_registry = dr.async_get(hass)

    device_registry.async_get_or_create(
        config_entry_id=entry_id,
        identifiers={(DOMAIN, id_storcube)},
        name=name,
        manufacturer="Storcube",
        model="S1000",
        sw_version="1.0"
    )

def on_message(client, userdata, message):
    """Callback exécuté lorsqu'un message MQTT est reçu."""
    _LOGGER.info(f"📡 MESSAGE MQTT REÇU : {message.topic}")

    try:
        payload = message.payload.decode("utf-8")
        data = json.loads(payload)
        hass = userdata["hass"]
        id_storcube = userdata["id_storcube"]

        sensor_data = {}

        if "realTimeData" in data:
            keys = ["battery_power", "battery_temp", "battery_status", "pv_input_power", "pv_status",
                    "grid_input_power", "grid_status", "load_power", "grid_injection"]
            
            for item in data["realTimeData"]:
                if len(item) >= len(keys) + 1:
                    sensor_data.update(dict(zip(keys, item[1:])))

        if "attr" in data:
            attributes = data["attr"]
            if "sw" in attributes:
                attributes["firmware"] = attributes.pop("sw")

            sensor_data.update(attributes)

        if sensor_data:
            hass.loop.call_soon_threadsafe(
                hass.async_create_task, dispatch_sensor_update(hass, id_storcube, sensor_data)
            )
            _LOGGER.info(f"✅ Mise à jour des capteurs pour {id_storcube}")

    except Exception as e:
        _LOGGER.error(f"❌ Erreur : {e}")

@callback
async def dispatch_sensor_update(hass, id_storcube, sensor_data):
    """Envoie la mise à jour des capteurs dans l'event loop principal."""
    async_dispatcher_send(hass, f"mqttstorcube_update_{id_storcube}", sensor_data)

async def async_add_dashboard(hass):
    """Créer et enregistrer un tableau de bord Lovelace pour Storcube."""
    dashboard_path = hass.config.path("www/storcube_dashboard.yaml")

    dashboard_content = """title: Storcube
views:
  - title: Batterie Storcube
    path: storcube
    icon: mdi:battery
    type: panel
    cards:
      - type: vertical-stack
        cards:
          - type: gauge
            entity: sensor.storcube_9105231027496711_battery_power
            name: Puissance Batterie
            unit: W
            min: 0
            max: 5000
            severity:
              green: 0
              yellow: 3000
              red: 4500

          - type: gauge
            entity: sensor.storcube_9105231027496711_batsoc
            name: Charge Batterie
            unit: "%"
            min: 0
            max: 100
            severity:
              green: 50
              yellow: 20
              red: 10

          - type: entities
            title: État de la Batterie
            show_header_toggle: false
            entities:
              - entity: sensor.storcube_9105231027496711_battery_temp
                name: Température Batterie
              - entity: sensor.storcube_9105231027496711_grid_input_power
                name: Puissance Réseau
              - entity: sensor.storcube_9105231027496711_load_power
                name: Charge Actuelle
              - entity: sensor.storcube_9105231027496711_firmware
                name: Version Firmware
"""

    if not os.path.exists(hass.config.path("www")):
        os.makedirs(hass.config.path("www"))

    if not os.path.exists(dashboard_path):
        with open(dashboard_path, "w") as dashboard_file:
            dashboard_file.write(dashboard_content)

    _LOGGER.info("✅ Tableau de bord Storcube créé à : www/storcube_dashboard.yaml")
