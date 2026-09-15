from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import httpx
from fastcs.attributes import AttrR, AttrRW, AttrW, Sender, Updater
from fastcs.controller import Controller, SubController
from fastcs.datatypes import Bool, Float, Int, String
from fastcs.wrappers import command

from carbide_fastcs.connection import DEFAULT_BASE_URL, CarbideConnection

LOGGER = logging.getLogger(__name__)


class ConnectedSubController(SubController):
    def __init__(self, conn: CarbideConnection) -> None:
        super().__init__()
        self.conn = conn


@dataclass
class PollingHandler(Updater):
    """Refreshes an ``AttrR`` by calling a named zero-arg method on the
    owning controller's ``CarbideConnection`` on a fixed period.

    Named by string rather than holding a bound method directly, since the
    connection is per-``CarbideController``-instance (unlike rtc6-fastcs's
    RTC6 bindings, which operate on a process-wide selected board) - the
    method is looked up on ``controller.conn`` at call time instead.
    """

    conn_method: str
    update_period: float | None = 1.0

    async def update(self, controller: ConnectedSubController, attr: AttrR) -> None:
        getter = getattr(controller.conn, self.conn_method)
        try:
            value = await getter()
        except httpx.HTTPError as exc:
            LOGGER.warning("Poll of %s failed: %s", self.conn_method, exc)
            return
        await attr.set(value)


@dataclass
class SetterHandler(Sender):
    """Writes an ``AttrW``'s value by calling a named async method on the
    owning controller's ``CarbideConnection`` with the new value."""

    conn_method: str

    async def put(
        self, controller: ConnectedSubController, attr: AttrW, value: Any
    ) -> None:
        setter = getattr(controller.conn, self.conn_method)
        await setter(value)


@dataclass
class ReadWriteHandler(Sender, Updater):
    """Combines ``PollingHandler`` and ``SetterHandler`` for an ``AttrRW`` -
    e.g. Carbide's ``Target*`` values, which are independently gettable and
    settable via the REST API."""

    getter_method: str
    setter_method: str
    update_period: float | None = 5.0

    async def put(
        self, controller: ConnectedSubController, attr: AttrW, value: Any
    ) -> None:
        setter = getattr(controller.conn, self.setter_method)
        await setter(value)

    async def update(self, controller: ConnectedSubController, attr: AttrR) -> None:
        getter = getattr(controller.conn, self.getter_method)
        try:
            value = await getter()
        except httpx.HTTPError as exc:
            LOGGER.warning("Poll of %s failed: %s", self.getter_method, exc)
            return
        await attr.set(value)


class CarbideInfoController(ConnectedSubController):
    """Identity fields that never change once connected - populated once at
    connect time rather than polled, matching rtc6-fastcs's
    ``proc_cardinfo`` pattern."""

    laser_identification_number = AttrR(String(), group="Info")
    serial_number = AttrR(String(), group="Info")

    async def populate(self) -> None:
        await self.laser_identification_number.set(
            await self.conn.laser_identification_number()
        )
        await self.serial_number.set(await self.conn.serial_number())


class CarbideStatusController(ConnectedSubController):
    actual_state_name = AttrR(
        String(), group="Status", handler=PollingHandler("actual_state_name", 1.0)
    )
    is_output_enabled = AttrR(
        Bool(znam="Closed", onam="Enabled"),
        group="Status",
        handler=PollingHandler("is_output_enabled", 1.0),
    )
    general_status = AttrR(
        String(), group="Status", handler=PollingHandler("general_status", 5.0)
    )
    warnings = AttrR(String(), group="Status", handler=PollingHandler("warnings", 5.0))
    errors = AttrR(String(), group="Status", handler=PollingHandler("errors", 5.0))

    async def wait_for_operational(self, poll_interval: float = 1.0) -> None:
        """Poll ``ActualStateName`` directly (not the cached PV) until the
        laser reaches "Operational", raising if it reaches "Failure" first.

        Ported from ``laserControl.py``'s ``waitForLaserOperational`` -
        the one piece of the original worth being most careful about
        porting faithfully, since a broken exit condition here would hang
        for real against real hardware.
        """
        state = await self.conn.actual_state_name()
        while state != "Operational":
            if state == "Failure":
                raise RuntimeError("Laser in Failure state, stopping wait")
            await asyncio.sleep(poll_interval)
            state = await self.conn.actual_state_name()


class CarbideBasicController(ConnectedSubController):
    selected_preset_index = AttrW(
        Int(), group="Presets", handler=SetterHandler("set_selected_preset_index")
    )
    last_executed_preset_index = AttrR(
        Int(),
        group="Presets",
        handler=PollingHandler("last_executed_preset_index", 5.0),
    )

    actual_attenuator_percentage = AttrR(
        Float(units="%"),
        group="ActualValues",
        handler=PollingHandler("actual_attenuator_percentage", 2.0),
    )
    actual_output_energy = AttrR(
        Float(units="uJ"),
        group="ActualValues",
        handler=PollingHandler("actual_output_energy", 2.0),
    )
    actual_output_frequency = AttrR(
        Float(units="kHz"),
        group="ActualValues",
        handler=PollingHandler("actual_output_frequency", 2.0),
    )
    actual_output_power = AttrR(
        Float(units="W"),
        group="ActualValues",
        handler=PollingHandler("actual_output_power", 2.0),
    )
    actual_pulse_duration = AttrR(
        Float(units="fs"),
        group="ActualValues",
        handler=PollingHandler("actual_pulse_duration", 2.0),
    )
    actual_pp_divider = AttrR(
        Int(), group="ActualValues", handler=PollingHandler("actual_pp_divider", 2.0)
    )
    actual_shutter_state = AttrR(
        Int(),
        group="ActualValues",
        handler=PollingHandler("actual_shutter_state", 2.0),
    )
    actual_ra_frequency = AttrR(
        Float(units="Hz"),
        group="ActualValues",
        handler=PollingHandler("actual_ra_frequency", 2.0),
    )
    actual_harmonic = AttrR(
        Int(), group="ActualValues", handler=PollingHandler("actual_harmonic", 2.0)
    )

    target_attenuator_percentage = AttrRW(
        Float(units="%"),
        group="Targets",
        handler=ReadWriteHandler(
            "target_attenuator_percentage", "set_target_attenuator_percentage"
        ),
    )
    target_pulse_duration = AttrRW(
        Float(units="fs"),
        group="Targets",
        handler=ReadWriteHandler("target_pulse_duration", "set_target_pulse_duration"),
    )
    target_pp_divider = AttrRW(
        Int(),
        group="Targets",
        handler=ReadWriteHandler("target_pp_divider", "set_target_pp_divider"),
    )
    target_ra_frequency = AttrRW(
        Float(units="Hz"),
        group="Targets",
        handler=ReadWriteHandler("target_ra_frequency", "set_target_ra_frequency"),
    )


class CarbideAdvancedController(ConnectedSubController):
    is_remote_interlock_active = AttrR(
        Bool(znam="Not armed", onam="Armed"),
        group="Interlock",
        handler=PollingHandler("is_remote_interlock_active", 1.0),
    )
    is_pp_enabled = AttrR(
        Bool(),
        group="PulsePicker",
        handler=PollingHandler("is_pp_enabled", 2.0),
    )
    is_powerlock_enabled = AttrR(
        Bool(),
        group="Powerlock",
        handler=PollingHandler("is_powerlock_enabled", 2.0),
    )
    # Manual §confirms this stays "Internal" - standalone operation, not
    # synced to beamline timing. Kept read/write rather than read-only in
    # case that's ever revisited.
    aom_trigger_source = AttrRW(
        String(),
        group="ExternalControl",
        handler=ReadWriteHandler("aom_trigger_source", "set_aom_trigger_source"),
    )


class CarbideActionsController(ConnectedSubController):
    """Zero-argument actions - one ``@command()`` per REST POST endpoint,
    kept separate rather than combined into ambiguous "toggle" methods
    (the original ``togglePulsePicker(toggle="off")`` called ``EnablePp``,
    which reads backwards at first glance - exposing both actions directly
    avoids that ambiguity)."""

    @command(group="Presets")
    async def apply_selected_preset(self) -> None:
        await self.conn.apply_selected_preset()

    @command(group="Output")
    async def enable_output(self) -> None:
        await self.conn.enable_output()

    @command(group="Output")
    async def close_output(self) -> None:
        await self.conn.close_output()

    @command(group="Output")
    async def go_to_standby(self) -> None:
        await self.conn.go_to_standby()

    @command(group="Interlock")
    async def reset_remote_interlock(self) -> None:
        await self.conn.reset_remote_interlock()

    @command(group="PulsePicker")
    async def enable_pp(self) -> None:
        await self.conn.enable_pp()

    @command(group="PulsePicker")
    async def disable_pp(self) -> None:
        await self.conn.disable_pp()

    @command(group="Powerlock")
    async def enable_powerlock(self) -> None:
        await self.conn.enable_powerlock()

    @command(group="Powerlock")
    async def disable_powerlock(self) -> None:
        await self.conn.disable_powerlock()

    @command(group="Maintenance")
    async def reduce_leak(self) -> None:
        """Confirmed unused operationally (Chris Orr, 2026-09-15) - see
        ``CarbideConnection.reduce_leak``."""
        await self.conn.reduce_leak()


class CarbideController(Controller):
    def __init__(self, base_url: str = DEFAULT_BASE_URL) -> None:
        super().__init__()
        self.conn = CarbideConnection(base_url)

        # Kept as typed attributes (not just registered by name) so callers
        # - including tests - can reach a sub-controller's own methods
        # without going through get_sub_controllers()'s base SubController
        # return type.
        self.info = CarbideInfoController(self.conn)
        self.status = CarbideStatusController(self.conn)
        self.basic = CarbideBasicController(self.conn)
        self.advanced = CarbideAdvancedController(self.conn)
        self.actions = CarbideActionsController(self.conn)

        self.register_sub_controller("INFO", self.info)
        self.register_sub_controller("STATUS", self.status)
        self.register_sub_controller("BASIC", self.basic)
        self.register_sub_controller("ADVANCED", self.advanced)
        self.register_sub_controller("ACTIONS", self.actions)

    async def connect(self) -> None:
        await self.info.populate()

    async def close(self) -> None:
        await self.conn.close()
