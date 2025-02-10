import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Configurer les capteurs MQTT Storcube à partir d'une entrée de configuration."""
    id_storcube = entry.data["id_storcube"]
    name = entry.data.get("name", f"Storcube {id_storcube}")

    sensors = {}

    @callback
    def update_sensors(data):
        """Met à jour ou ajoute dynamiquement des capteurs pour `realTimeData` et `attr`."""
        for key, value in data.items():
            if key not in sensors:
                _LOGGER.info(f"📡 Ajout d'un nouveau capteur `{key}` pour {id_storcube}")
                sensor = StorcubeSensor(id_storcube, name, key, "%" if key == "batsoc" else None, None)
                sensors[key] = sensor
                async_add_entities([sensor])

            hass.async_create_task(sensors[key].async_update_state(value))

    async_dispatcher_connect(hass, f"mqttstorcube_update_{id_storcube}", update_sensors)

    _LOGGER.info(f"✅ Capteurs configurés pour {name} (ID: {id_storcube})")

class StorcubeSensor(SensorEntity):
    """Capteur représentant une valeur des messages `realTimeData` et `attr` de Storcube."""

    def __init__(self, id_storcube, name, sensor_type, unit, device_class):
        """Initialiser le capteur."""
        self._id_storcube = id_storcube
        self._name = f"{name} {sensor_type.replace('_', ' ').title()}"
        self._sensor_type = sensor_type
        self._unit = unit
        self._device_class = device_class
        self._state = None
        self._attr_unique_id = f"storcube_{id_storcube}_{sensor_type}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, id_storcube)},
            "name": name,
            "manufacturer": "Storcube",
            "model": "S1000"
        }

    @property
    def name(self):
        """Retourne le nom du capteur."""
        return self._name

    @property
    def state(self):
        """Retourne l'état actuel du capteur."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Retourne l'unité de mesure."""
        return self._unit

    @property
    def device_class(self):
        """Retourne la classe du capteur."""
        return self._device_class

    @property
    def should_poll(self):
        """Indique que l'entité ne doit pas être interrogée, elle sera mise à jour via MQTT."""
        return False

    async def async_update_state(self, value):
        """Met à jour l'état du capteur de manière asynchrone."""
        if self.hass is None:
            _LOGGER.warning(f"⚠️ `hass` est `None` pour {self._name}, mise à jour ignorée.")
            return

        self._state = value
        self.async_write_ha_state()
