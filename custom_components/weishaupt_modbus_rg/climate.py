"""Climate platform for Weishaupt heat pump."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .configentry import MyConfigEntry
from .const import CONST, DEVICES
from .coordinator import MyCoordinator, check_configured
from .entities import MyEntity
from .items import ModbusItem
from .modbusobject import ModbusAPI, ModbusObject

_LOGGER = logging.getLogger(__name__)

# Mapping between HA HVAC modes and Weishaupt operation modes
HVAC_MODE_TO_WEISHAUPT = {
    HVACMode.AUTO: 0,  # Automatik
    HVACMode.HEAT: 2,  # Normal
    HVACMode.OFF: 4,  # Standby
}

WEISHAUPT_TO_HVAC_MODE = {
    0: HVACMode.AUTO,  # Automatik
    1: HVACMode.HEAT,  # Komfort
    2: HVACMode.HEAT,  # Normal
    3: HVACMode.HEAT,  # Absenkbetrieb
    4: HVACMode.OFF,  # Standby
}

# Preset modes for temperature setpoints
PRESET_COMFORT = "comfort"
PRESET_NORMAL = "normal"
PRESET_ECO = "eco"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: MyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the climate platform."""
    coordinator = config_entry.runtime_data.coordinator
    entries: list[WeishauptClimate] = []

    # Get all modbus items for heating circuits
    modbus_items = coordinator.modbus_items

    # Create climate entity for HZ (Heizkreis 1)
    hz_items = {
        item.address: item for item in modbus_items if item.device == DEVICES.HZ
    }
    if hz_items:
        entries.append(
            WeishauptClimate(
                config_entry=config_entry,
                coordinator=coordinator,
                hz_items=hz_items,
                circuit_number=1,
                device_key=DEVICES.HZ,
            )
        )

    # Create climate entities for HZ2-HZ5 if configured
    for circuit_num, device_key in [
        (2, DEVICES.HZ2),
        (3, DEVICES.HZ3),
        (4, DEVICES.HZ4),
        (5, DEVICES.HZ5),
    ]:
        hz_items = {
            item.address: item for item in modbus_items if item.device == device_key
        }
        if hz_items:
            # Check if this heating circuit is configured
            dummy_item = ModbusItem(
                address=0,
                name="dummy",
                mformat="",
                mtype="",
                device=device_key,
                translation_key="dummy",
            )
            if await check_configured(dummy_item, config_entry):
                entries.append(
                    WeishauptClimate(
                        config_entry=config_entry,
                        coordinator=coordinator,
                        hz_items=hz_items,
                        circuit_number=circuit_num,
                        device_key=device_key,
                    )
                )

    async_add_entities(entries, update_before_add=True)


class WeishauptClimate(CoordinatorEntity, ClimateEntity, MyEntity):
    """Representation of a Weishaupt heating circuit as a climate entity."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.AUTO, HVACMode.HEAT, HVACMode.OFF]
    _attr_preset_modes = [PRESET_COMFORT, PRESET_NORMAL, PRESET_ECO]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    )

    def __init__(
        self,
        config_entry: MyConfigEntry,
        coordinator: MyCoordinator,
        hz_items: dict[int, ModbusItem],
        circuit_number: int,
        device_key: str,
    ) -> None:
        """Initialize the climate entity."""
        CoordinatorEntity.__init__(self, coordinator)

        # Find the required modbus items by address offset
        base_offset = (circuit_number - 1) * 100

        # Current temperature sensor (31102, 31202, etc.)
        self._current_temp_item = hz_items.get(31102 + base_offset)

        # Target temperature numbers (41105-41107 for HZ1, etc.)
        self._comfort_temp_item = hz_items.get(41105 + base_offset)
        self._normal_temp_item = hz_items.get(41106 + base_offset)
        self._eco_temp_item = hz_items.get(41107 + base_offset)

        # Operation mode select (41103, 41203, etc.)
        self._mode_item = hz_items.get(41103 + base_offset)

        # Use the mode item as the primary item for MyEntity initialization
        if self._mode_item:
            MyEntity.__init__(self, config_entry, self._mode_item, coordinator)

        self._circuit_number = circuit_number
        self._device_key = device_key

        # Override unique ID and name for climate entity
        self._attr_unique_id = f"{config_entry.data.get('prefix', 'weishaupt')}_climate_hk{circuit_number}"
        self._attr_translation_key = f"climate_hk{circuit_number}"
        self._attr_name = f"Heizkreis {circuit_number}"

        # Current preset mode
        self._attr_preset_mode = PRESET_NORMAL

        self._modbus_api: ModbusAPI = coordinator.modbus_api

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        if self._current_temp_item and self._current_temp_item.state is not None:
            return float(self._current_temp_item.state) / 10
        return None

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        preset_item_map = {
            PRESET_COMFORT: self._comfort_temp_item,
            PRESET_NORMAL: self._normal_temp_item,
            PRESET_ECO: self._eco_temp_item,
        }

        item = preset_item_map.get(self._attr_preset_mode)
        if item and item.state is not None:
            return float(item.state) / 10
        return None

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        if self._mode_item and self._mode_item.state is not None:
            return WEISHAUPT_TO_HVAC_MODE.get(
                self._mode_item.state, HVACMode.HEAT
            )
        return HVACMode.HEAT

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        return 10.0

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        return 30.0

    @property
    def target_temperature_step(self) -> float:
        """Return the supported step of target temperature."""
        return 0.5

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return

        preset_item_map = {
            PRESET_COMFORT: self._comfort_temp_item,
            PRESET_NORMAL: self._normal_temp_item,
            PRESET_ECO: self._eco_temp_item,
        }

        item = preset_item_map.get(self._attr_preset_mode)
        if item is None:
            _LOGGER.warning(
                "Cannot set temperature: no item for preset %s", self._attr_preset_mode
            )
            return

        # Convert to modbus value (multiply by 10)
        modbus_value = int(temperature * 10)

        await self._modbus_api.connect()
        mbo = ModbusObject(self._modbus_api, item)
        await mbo.set_value(modbus_value)

        # Update the item state
        item.state = modbus_value

        # Request coordinator update
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode."""
        if self._mode_item is None:
            _LOGGER.warning("Cannot set HVAC mode: mode item not found")
            return

        modbus_value = HVAC_MODE_TO_WEISHAUPT.get(hvac_mode)
        if modbus_value is None:
            _LOGGER.warning("Unknown HVAC mode: %s", hvac_mode)
            return

        await self._modbus_api.connect()
        mbo = ModbusObject(self._modbus_api, self._mode_item)
        await mbo.set_value(modbus_value)

        # Update the item state
        self._mode_item.state = modbus_value

        # Request coordinator update
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode not in self._attr_preset_modes:
            _LOGGER.warning("Unknown preset mode: %s", preset_mode)
            return

        self._attr_preset_mode = preset_mode

        # When changing preset, also update the operation mode
        mode_map = {
            PRESET_COMFORT: 1,  # Komfort
            PRESET_NORMAL: 2,  # Normal
            PRESET_ECO: 3,  # Absenkbetrieb
        }

        if self._mode_item is not None:
            modbus_value = mode_map.get(preset_mode)
            if modbus_value is not None:
                await self._modbus_api.connect()
                mbo = ModbusObject(self._modbus_api, self._mode_item)
                await mbo.set_value(modbus_value)
                self._mode_item.state = modbus_value

        # Request coordinator update
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()
