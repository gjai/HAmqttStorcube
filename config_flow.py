import voluptuous as vol
import logging
from homeassistant import config_entries
from homeassistant.core import callback
from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({
    vol.Required("id_storcube"): str,
    vol.Optional("name", default="Storcube"): str
})

class MqttStorcubeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gérer l'ajout de l'intégration via l'UI."""

    async def async_step_user(self, user_input=None):
        """Demander l'ID et le nom de l'appareil."""
        errors = {}

        if user_input is not None:
            id_storcube = user_input["id_storcube"]
            name = user_input["name"]

            existing_entries = [entry for entry in self._async_current_entries() if entry.data.get("id_storcube") == id_storcube]
            if existing_entries:
                errors["base"] = "already_configured"
            else:
                return self.async_create_entry(title=name, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors
        )
