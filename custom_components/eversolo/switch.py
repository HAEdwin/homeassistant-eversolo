"""Switch platform for eversolo."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.components.persistent_notification import (
    async_create as async_create_notification,
)

from .const import CONF_ABLE_REMOTE_BOOT, DOMAIN, NOTIFICATION_ID_WOL
from .coordinator import EversoloDataUpdateCoordinator
from .entity import EversoloEntity


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the Switch platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []

    # Add power switch if device supports remote boot
    if entry.data.get(CONF_ABLE_REMOTE_BOOT, False):
        entities.append(EversoloPowerSwitch(coordinator))

    async_add_devices(entities)


class EversoloPowerSwitch(EversoloEntity, SwitchEntity):
    """Power switch for Eversolo with Wake-on-LAN support."""

    def __init__(self, coordinator: EversoloDataUpdateCoordinator) -> None:
        """Initialize Eversolo power switch."""
        super().__init__(coordinator)
        self._attr_name = "Eversolo Power Switch"
        self._attr_icon = "mdi:power"
        self._attr_device_class = SwitchDeviceClass.SWITCH
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_power_switch"

    @property
    def available(self) -> bool:
        """Return True - switch remains available to allow turning on via WoL."""
        return True

    def _set_optimistic_state(self, state: bool):
        """Set the switch state optimistically and schedule update."""
        self._optimistic_state = state
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        self._optimistic_state = None
        await super().async_added_to_hass()

    @property
    def is_on(self) -> bool:
        """Return True if the device is on (coordinator update successful),
        or use optimistic state if set."""
        if self._optimistic_state is not None:
            return self._optimistic_state
        return self.coordinator.last_update_success

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on the device via Wake-on-LAN."""
        self._set_optimistic_state(True)
        await self.coordinator.async_send_wol()
        async_create_notification(
            self.hass,
            "Wake-on-LAN packet sent to Eversolo device. "
            "Waiting for the device to come online...",
            title="Eversolo Power On",
            notification_id=NOTIFICATION_ID_WOL,
        )

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the device."""
        self._set_optimistic_state(False)
        await self.coordinator.client.async_trigger_power_off()
        await self.coordinator.async_request_refresh()

    async def async_update(self):
        """Clear optimistic state when coordinator updates."""
        self._optimistic_state = None
        await super().async_update()
