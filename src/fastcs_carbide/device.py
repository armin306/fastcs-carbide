"""ophyd-async device wrapping the ``fastcs-carbide`` IOC's EPICS PVs.

Mirrors ``fastcs_rtc6.device.Rtc6Eth``'s shape closely - one ``StandardReadable``
sub-device per PV sub-namespace, an outer device composing them with a
``stage``/``trigger``/``unstage`` lifecycle. Not yet wired into ``dodal`` (see
``aithre_lasercontrols``'s ``WAY_FORWARD.md`` - that's the next step, not this
one), but built ready for it.
"""

import asyncio

from bluesky.protocols import Triggerable
from ophyd_async.core import AsyncStageable, AsyncStatus, StandardReadable
from ophyd_async.epics.core import (
    epics_signal_r,
    epics_signal_rw,
    epics_signal_w,
    epics_signal_x,
)


class CarbideInfo(StandardReadable):
    def __init__(self, prefix: str = "INFO:", name: str = "") -> None:
        super().__init__(name)
        with self.add_children_as_readables():
            self.laser_identification_number = epics_signal_r(
                str, prefix + "LaserIdentificationNumber"
            )
            self.serial_number = epics_signal_r(str, prefix + "SerialNumber")


class CarbideStatus(StandardReadable):
    def __init__(self, prefix: str = "STATUS:", name: str = "") -> None:
        super().__init__(name)
        with self.add_children_as_readables():
            self.actual_state_name = epics_signal_r(str, prefix + "ActualStateName")
            self.is_output_enabled = epics_signal_r(bool, prefix + "IsOutputEnabled")
            self.general_status = epics_signal_r(str, prefix + "GeneralStatus")
            self.warnings = epics_signal_r(str, prefix + "Warnings")
            self.errors = epics_signal_r(str, prefix + "Errors")


class CarbideBasicSettings(StandardReadable):
    def __init__(self, prefix: str = "BASIC:", name: str = "") -> None:
        super().__init__(name)
        with self.add_children_as_readables():
            self.selected_preset_index = epics_signal_w(
                int, prefix + "SelectedPresetIndex"
            )
            self.last_executed_preset_index = epics_signal_r(
                int, prefix + "LastExecutedPresetIndex"
            )
            self.actual_attenuator_percentage = epics_signal_r(
                float, prefix + "ActualAttenuatorPercentage"
            )
            self.actual_output_energy = epics_signal_r(
                float, prefix + "ActualOutputEnergy"
            )
            self.actual_output_frequency = epics_signal_r(
                float, prefix + "ActualOutputFrequency"
            )
            self.actual_output_power = epics_signal_r(
                float, prefix + "ActualOutputPower"
            )
            self.actual_pulse_duration = epics_signal_r(
                float, prefix + "ActualPulseDuration"
            )
            self.actual_pp_divider = epics_signal_r(int, prefix + "ActualPpDivider")
            self.actual_shutter_state = epics_signal_r(
                str, prefix + "ActualShutterState"
            )
            self.actual_ra_frequency = epics_signal_r(
                float, prefix + "ActualRaFrequency"
            )
            self.actual_harmonic = epics_signal_r(int, prefix + "ActualHarmonic")
            self.target_attenuator_percentage = epics_signal_rw(
                float, prefix + "TargetAttenuatorPercentage"
            )
            self.target_pulse_duration = epics_signal_rw(
                float, prefix + "TargetPulseDuration"
            )
            self.target_pp_divider = epics_signal_rw(int, prefix + "TargetPpDivider")
            self.target_ra_frequency = epics_signal_rw(
                float, prefix + "TargetRaFrequency"
            )


class CarbideAdvancedSettings(StandardReadable):
    def __init__(self, prefix: str = "ADVANCED:", name: str = "") -> None:
        super().__init__(name)
        with self.add_children_as_readables():
            self.is_remote_interlock_active = epics_signal_r(
                bool, prefix + "IsRemoteInterlockActive"
            )
            self.is_pp_enabled = epics_signal_r(bool, prefix + "IsPpEnabled")
            self.is_powerlock_enabled = epics_signal_r(
                bool, prefix + "IsPowerlockEnabled"
            )
            self.aom_trigger_source = epics_signal_rw(str, prefix + "AomTriggerSource")


class CarbideActions(StandardReadable):
    def __init__(self, prefix: str = "ACTIONS:", name: str = "") -> None:
        super().__init__(name)
        with self.add_children_as_readables():
            self.apply_selected_preset = epics_signal_x(prefix + "ApplySelectedPreset")
            self.enable_output = epics_signal_x(prefix + "EnableOutput")
            self.close_output = epics_signal_x(prefix + "CloseOutput")
            self.go_to_standby = epics_signal_x(prefix + "GoToStandby")
            self.reset_remote_interlock = epics_signal_x(
                prefix + "ResetRemoteInterlock"
            )
            self.enable_pp = epics_signal_x(prefix + "EnablePp")
            self.disable_pp = epics_signal_x(prefix + "DisablePp")
            self.enable_powerlock = epics_signal_x(prefix + "EnablePowerlock")
            self.disable_powerlock = epics_signal_x(prefix + "DisablePowerlock")
            # Confirmed unused operationally (Chris Orr, 2026-09-15) - kept
            # for API completeness, see CarbideConnection.reduce_leak.
            self.reduce_leak = epics_signal_x(prefix + "ReduceLeak")


class CarbideLaser(StandardReadable, AsyncStageable, Triggerable):
    def __init__(self, prefix: str = "CARBIDE:", name: str = "") -> None:
        super().__init__(name)
        with self.add_children_as_readables():
            self.info = CarbideInfo(prefix + "INFO:")
            self.status = CarbideStatus(prefix + "STATUS:")
            self.basic_settings = CarbideBasicSettings(prefix + "BASIC:")
            self.advanced_settings = CarbideAdvancedSettings(prefix + "ADVANCED:")
            self.actions = CarbideActions(prefix + "ACTIONS:")

    async def wait_for_operational(
        self, poll_interval: float = 1.0, timeout: float = 120.0
    ) -> None:
        """Poll the cached ``ActualStateName`` PV until "Operational",
        raising on "Failure" or on timeout.

        Ported from ``laserControl.py``'s ``waitForLaserOperational`` via
        the IOC's own equivalent
        (``CarbideStatusController.wait_for_operational``) - this version
        polls the EPICS PV rather than making its own REST calls, so it
        doesn't duplicate the IOC's own polling of the laser.
        """

        async def _poll() -> None:
            state = await self.status.actual_state_name.get_value()
            while state != "Operational":
                if state == "Failure":
                    raise RuntimeError("Laser in Failure state, stopping wait")
                await asyncio.sleep(poll_interval)
                state = await self.status.actual_state_name.get_value()

        await asyncio.wait_for(_poll(), timeout=timeout)

    @AsyncStatus.wrap
    async def stage(self) -> None:
        """Apply the selected preset and wait for the laser to become
        operational."""
        await self.actions.apply_selected_preset.trigger()
        await self.wait_for_operational()

    @AsyncStatus.wrap
    async def trigger(self) -> None:
        """Enable output."""
        await self.actions.enable_output.trigger()

    @AsyncStatus.wrap
    async def unstage(self) -> None:
        """Close output."""
        await self.actions.close_output.trigger()

    @AsyncStatus.wrap
    async def set_attenuator_percentage(self, percentage: float) -> None:
        await self.basic_settings.target_attenuator_percentage.set(percentage)

    @AsyncStatus.wrap
    async def set_preset(self, index: int) -> None:
        await self.basic_settings.selected_preset_index.set(index)
