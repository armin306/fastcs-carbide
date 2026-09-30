"""Async wrapper around the Light Conversion CARBIDE Supervisor REST API.

Ported from the original ``laserControl.py``'s ``carbide`` class in the
``aithre_lasercontrols`` repo (see that repo's ``docs/CARBIDE_FASTCS_DESIGN.md``
for the full endpoint-by-endpoint mapping this is based on). Two deliberate
differences from the original:

- Uses ``httpx.AsyncClient`` rather than synchronous ``requests`` calls,
  since FastCS attribute handlers are async and some of these calls (notably
  waiting for the laser to reach "Operational") poll in a loop - a
  synchronous call there would block the whole IOC's event loop.
- Response bodies are decoded with ``.json()`` rather than compared/cast as
  raw text (e.g. the original compared ``response.text == "true"`` and did
  ``float(response.text)``). The API returns JSON scalars, so this is a
  behavior-preserving cleanup, not a change to what the API is asked for.
"""

from __future__ import annotations

import logging

import httpx

LOGGER = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://192.168.240.10:20010"


class CarbideConnectionError(Exception):
    """Raised when the CARBIDE Supervisor REST API returns an unexpected result."""


class CarbideConnection:
    """Thin async wrapper over the CARBIDE Supervisor REST API.

    One method per endpoint, named after the endpoint rather than grouped
    into higher-level behaviors (e.g. no combined "toggle pulse picker"
    method) - that grouping is left to the FastCS controller layer, so the
    mapping from method to REST call stays unambiguous here.
    """

    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: float = 10.0) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> CarbideConnection:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    # --- low-level helpers --------------------------------------------------

    async def _get(self, path: str) -> httpx.Response:
        response = await self._client.get(path)
        response.raise_for_status()
        return response

    async def _put(self, path: str, value: bool | int | float | str) -> None:
        response = await self._client.put(
            path, json=value, headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()

    async def _post(self, path: str) -> None:
        response = await self._client.post(
            path, headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()

    async def _get_str(self, path: str) -> str:
        return str((await self._get(path)).json())

    async def _get_bool(self, path: str) -> bool:
        return bool((await self._get(path)).json())

    async def _get_float(self, path: str) -> float:
        return float((await self._get(path)).json())

    async def _get_int(self, path: str) -> int:
        return int((await self._get(path)).json())

    # --- Info -----------------------------------------------------------------

    async def laser_identification_number(self) -> str:
        return await self._get_str("/v1/Basic/LaserIdentificationNumber")

    async def serial_number(self) -> str:
        return await self._get_str("/v1/Basic/SerialNumber")

    # --- Status ---------------------------------------------------------------

    async def actual_state_name(self) -> str:
        return await self._get_str("/v1/Basic/ActualStateName")

    async def actual_state_id(self) -> int:
        return await self._get_int("/v1/Advanced/ActualStateId")

    async def is_output_enabled(self) -> bool:
        return await self._get_bool("/v1/Basic/IsOutputEnabled")

    async def general_status(self) -> str:
        return await self._get_str("/v1/Basic/GeneralStatus")

    async def warnings(self) -> str:
        return await self._get_str("/v1/Basic/Warnings")

    async def errors(self) -> str:
        return await self._get_str("/v1/Basic/Errors")

    # --- Presets ----------------------------------------------------------

    async def selected_preset_index(self) -> int:
        return await self._get_int("/v1/Basic/SelectedPresetIndex")

    async def set_selected_preset_index(self, index: int) -> None:
        await self._put("/v1/Basic/SelectedPresetIndex", index)

    async def last_executed_preset_index(self) -> int:
        return await self._get_int("/v1/Basic/LastExecutedPresetIndex")

    async def apply_selected_preset(self) -> None:
        await self._post("/v1/Basic/ApplySelectedPreset")

    # --- Output -----------------------------------------------------------

    async def enable_output(self) -> None:
        await self._post("/v1/Basic/EnableOutput")

    async def close_output(self) -> None:
        await self._post("/v1/Basic/CloseOutput")

    async def go_to_standby(self) -> None:
        await self._post("/v1/Basic/GoToStandby")

    # --- Actual values ------------------------------------------------------

    async def actual_attenuator_percentage(self) -> float:
        return await self._get_float("/v1/Basic/ActualAttenuatorPercentage")

    async def actual_output_energy(self) -> float:
        return await self._get_float("/v1/Basic/ActualOutputEnergy")

    async def actual_output_frequency(self) -> float:
        return await self._get_float("/v1/Basic/ActualOutputFrequency")

    async def actual_output_power(self) -> float:
        return await self._get_float("/v1/Basic/ActualOutputPower")

    async def actual_pulse_duration(self) -> float:
        return await self._get_float("/v1/Basic/ActualPulseDuration")

    async def actual_pp_divider(self) -> int:
        return await self._get_int("/v1/Basic/ActualPpDivider")

    async def actual_shutter_state(self) -> str:
        return await self._get_str("/v1/Basic/ActualShutterState")

    async def actual_ra_frequency(self) -> float:
        return await self._get_float("/v1/Advanced/ActualRaFrequency")

    async def actual_harmonic(self) -> int:
        return await self._get_int("/v1/Basic/ActualHarmonic")

    # --- Targets ------------------------------------------------------------

    async def target_attenuator_percentage(self) -> float:
        return await self._get_float("/v1/Basic/TargetAttenuatorPercentage")

    async def set_target_attenuator_percentage(self, percentage: float) -> None:
        await self._put("/v1/Basic/TargetAttenuatorPercentage", percentage)

    async def target_pulse_duration(self) -> float:
        return await self._get_float("/v1/Basic/TargetPulseDuration")

    async def set_target_pulse_duration(self, length: float) -> None:
        await self._put("/v1/Basic/TargetPulseDuration", length)

    async def target_pp_divider(self) -> int:
        return await self._get_int("/v1/Basic/TargetPpDivider")

    async def set_target_pp_divider(self, divider: int) -> None:
        await self._put("/v1/Basic/TargetPpDivider", divider)

    async def target_ra_frequency(self) -> float:
        return await self._get_float("/v1/Advanced/TargetRaFrequency")

    async def set_target_ra_frequency(self, frequency: float) -> None:
        await self._put("/v1/Advanced/TargetRaFrequency", frequency)

    # --- Interlock / pulse picker / powerlock ------------------------------

    async def is_remote_interlock_active(self) -> bool:
        return await self._get_bool("/v1/Advanced/IsRemoteInterlockActive")

    async def reset_remote_interlock(self) -> None:
        await self._post("/v1/Advanced/ResetRemoteInterlock")

    async def is_pp_enabled(self) -> bool:
        return await self._get_bool("/v1/Advanced/IsPpEnabled")

    async def enable_pp(self) -> None:
        await self._post("/v1/Advanced/EnablePp")

    async def disable_pp(self) -> None:
        await self._post("/v1/Advanced/DisablePp")

    async def is_powerlock_enabled(self) -> bool:
        return await self._get_bool("/v1/Basic/IsPowerlockEnabled")

    async def enable_powerlock(self) -> None:
        await self._post("/v1/Basic/EnablePowerlock")

    async def disable_powerlock(self) -> None:
        await self._post("/v1/Basic/DisablePowerlock")

    # --- AOM trigger source -------------------------------------------------

    async def aom_trigger_source(self) -> str:
        return await self._get_str("/v1/ExternalControl/AomTriggerSource")

    async def set_aom_trigger_source(self, source: str) -> None:
        """``source`` must be one of "Internal", "ExternalHigh", "ExternalLow"."""
        await self._put("/v1/ExternalControl/AomTriggerSource", source)

    # --- Reduce leak --------------------------------------------------------

    async def reduce_leak(self) -> None:
        """Run the Reduce Leak procedure.

        Confirmed unused operationally at Aithre (Chris Orr, 2026-09-15) -
        kept here for API completeness only. Don't build anything on top of
        this without checking with Chris/Photonics first (see
        ``aithre_lasercontrols``'s ``QUESTIONS_FOR_CHRIS.md`` #1).
        """
        await self._post("/v1/Advanced/ReduceLeak")
