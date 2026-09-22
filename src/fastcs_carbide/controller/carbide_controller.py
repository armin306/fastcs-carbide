from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import httpx
from fastcs.attributes import AttributeIO, AttributeIORef, AttrR, AttrRW, AttrW
from fastcs.controllers import Controller
from fastcs.datatypes import Bool, Float, Int, String
from fastcs.methods import command

from fastcs_carbide.connection import DEFAULT_BASE_URL, CarbideConnection

LOGGER = logging.getLogger(__name__)


@dataclass
class CarbideIORef(AttributeIORef):
    """Names the ``CarbideConnection`` method(s) backing an attribute.

    ``get_method`` drives ``AttrR``/``AttrRW`` polling, ``set_method`` drives
    ``AttrW``/``AttrRW`` puts - either or both may be set, since a single
    ``CarbideAttributeIO`` instance handles all three attribute shapes.
    """

    get_method: str | None = None
    set_method: str | None = None


class CarbideAttributeIO(AttributeIO[Any, CarbideIORef]):
    """Reads/writes attributes by calling the named method on a shared
    ``CarbideConnection`` - one instance is shared across all of a
    ``CarbideController``'s sub-controllers, since they all talk to the
    same REST API."""

    def __init__(self, conn: CarbideConnection) -> None:
        super().__init__()
        self.conn = conn

    async def update(self, attr: AttrR[Any, CarbideIORef]) -> None:
        method = attr.io_ref.get_method
        assert method is not None, f"{attr} has no get_method"
        getter = getattr(self.conn, method)
        try:
            value = await getter()
        except httpx.HTTPError as exc:
            LOGGER.warning("Poll of %s failed: %s", method, exc)
            return
        await attr.update(value)

    async def send(self, attr: AttrW[Any, CarbideIORef], value: Any) -> None:
        method = attr.io_ref.set_method
        assert method is not None, f"{attr} has no set_method"
        setter = getattr(self.conn, method)
        await setter(value)


class ConnectedSubController(Controller):
    def __init__(self, conn: CarbideConnection) -> None:
        self.conn = conn
        self.io = CarbideAttributeIO(conn)
        super().__init__(ios=[self.io])


class CarbideInfoController(ConnectedSubController):
    """Identity fields that never change once connected - populated once at
    connect time rather than polled, matching rtc6-fastcs's
    ``proc_cardinfo`` pattern."""

    laser_identification_number = AttrR(String(), group="Info")
    serial_number = AttrR(String(), group="Info")

    async def populate(self) -> None:
        await self.laser_identification_number.update(
            await self.conn.laser_identification_number()
        )
        await self.serial_number.update(await self.conn.serial_number())


class CarbideStatusController(ConnectedSubController):
    actual_state_name = AttrR(
        String(),
        group="Status",
        io_ref=CarbideIORef(get_method="actual_state_name", update_period=1.0),
    )
    is_output_enabled = AttrR(
        Bool(),
        group="Status",
        io_ref=CarbideIORef(get_method="is_output_enabled", update_period=1.0),
    )
    general_status = AttrR(
        String(),
        group="Status",
        io_ref=CarbideIORef(get_method="general_status", update_period=5.0),
    )
    warnings = AttrR(
        String(),
        group="Status",
        io_ref=CarbideIORef(get_method="warnings", update_period=5.0),
    )
    errors = AttrR(
        String(),
        group="Status",
        io_ref=CarbideIORef(get_method="errors", update_period=5.0),
    )

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
        Int(),
        group="Presets",
        io_ref=CarbideIORef(set_method="set_selected_preset_index"),
    )
    last_executed_preset_index = AttrR(
        Int(),
        group="Presets",
        io_ref=CarbideIORef(get_method="last_executed_preset_index", update_period=5.0),
    )

    actual_attenuator_percentage = AttrR(
        Float(units="%"),
        group="ActualValues",
        io_ref=CarbideIORef(
            get_method="actual_attenuator_percentage", update_period=2.0
        ),
    )
    actual_output_energy = AttrR(
        Float(units="uJ"),
        group="ActualValues",
        io_ref=CarbideIORef(get_method="actual_output_energy", update_period=2.0),
    )
    actual_output_frequency = AttrR(
        Float(units="kHz"),
        group="ActualValues",
        io_ref=CarbideIORef(get_method="actual_output_frequency", update_period=2.0),
    )
    actual_output_power = AttrR(
        Float(units="W"),
        group="ActualValues",
        io_ref=CarbideIORef(get_method="actual_output_power", update_period=2.0),
    )
    actual_pulse_duration = AttrR(
        Float(units="fs"),
        group="ActualValues",
        io_ref=CarbideIORef(get_method="actual_pulse_duration", update_period=2.0),
    )
    actual_pp_divider = AttrR(
        Int(),
        group="ActualValues",
        io_ref=CarbideIORef(get_method="actual_pp_divider", update_period=2.0),
    )
    actual_shutter_state = AttrR(
        String(),
        group="ActualValues",
        io_ref=CarbideIORef(get_method="actual_shutter_state", update_period=2.0),
    )
    actual_ra_frequency = AttrR(
        Float(units="Hz"),
        group="ActualValues",
        io_ref=CarbideIORef(get_method="actual_ra_frequency", update_period=2.0),
    )
    actual_harmonic = AttrR(
        Int(),
        group="ActualValues",
        io_ref=CarbideIORef(get_method="actual_harmonic", update_period=2.0),
    )

    target_attenuator_percentage = AttrRW(
        Float(units="%"),
        group="Targets",
        io_ref=CarbideIORef(
            get_method="target_attenuator_percentage",
            set_method="set_target_attenuator_percentage",
            update_period=5.0,
        ),
    )
    target_pulse_duration = AttrRW(
        Float(units="fs"),
        group="Targets",
        io_ref=CarbideIORef(
            get_method="target_pulse_duration",
            set_method="set_target_pulse_duration",
            update_period=5.0,
        ),
    )
    target_pp_divider = AttrRW(
        Int(),
        group="Targets",
        io_ref=CarbideIORef(
            get_method="target_pp_divider",
            set_method="set_target_pp_divider",
            update_period=5.0,
        ),
    )
    target_ra_frequency = AttrRW(
        Float(units="Hz"),
        group="Targets",
        io_ref=CarbideIORef(
            get_method="target_ra_frequency",
            set_method="set_target_ra_frequency",
            update_period=5.0,
        ),
    )


class CarbideAdvancedController(ConnectedSubController):
    is_remote_interlock_active = AttrR(
        Bool(),
        group="Interlock",
        io_ref=CarbideIORef(get_method="is_remote_interlock_active", update_period=1.0),
    )
    is_pp_enabled = AttrR(
        Bool(),
        group="PulsePicker",
        io_ref=CarbideIORef(get_method="is_pp_enabled", update_period=2.0),
    )
    is_powerlock_enabled = AttrR(
        Bool(),
        group="Powerlock",
        io_ref=CarbideIORef(get_method="is_powerlock_enabled", update_period=2.0),
    )
    # Manual confirms this stays "Internal" - standalone operation, not
    # synced to beamline timing. Kept read/write rather than read-only in
    # case that's ever revisited.
    aom_trigger_source = AttrRW(
        String(),
        group="ExternalControl",
        io_ref=CarbideIORef(
            get_method="aom_trigger_source",
            set_method="set_aom_trigger_source",
            update_period=5.0,
        ),
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


@dataclass
class CarbideControllerOptions:
    base_url: str = DEFAULT_BASE_URL


class CarbideController(Controller):
    # Type-hinted (not just registered by name) so callers - including
    # tests - can reach a sub-controller's own methods without going
    # through get_sub_controllers()'s base BaseController return type.
    info: CarbideInfoController
    status: CarbideStatusController
    basic: CarbideBasicController
    advanced: CarbideAdvancedController
    actions: CarbideActionsController

    def __init__(self, options: CarbideControllerOptions) -> None:
        super().__init__()
        self.conn = CarbideConnection(options.base_url)

        for path_segment, sub_controller, attr_name in (
            ("INFO", CarbideInfoController(self.conn), "info"),
            ("STATUS", CarbideStatusController(self.conn), "status"),
            ("BASIC", CarbideBasicController(self.conn), "basic"),
            ("ADVANCED", CarbideAdvancedController(self.conn), "advanced"),
            ("ACTIONS", CarbideActionsController(self.conn), "actions"),
        ):
            self.add_sub_controller(path_segment, sub_controller)
            # Controller.__setattr__ auto-registers any BaseController
            # assigned to it under the attribute's own name (lower-case
            # here), which would collide with the upper-case PV path
            # segment just registered above - bypass it to keep the two
            # independent.
            object.__setattr__(self, attr_name, sub_controller)

    async def connect(self) -> None:
        await self.info.populate()
        await super().connect()

    async def close(self) -> None:
        await self.conn.close()
