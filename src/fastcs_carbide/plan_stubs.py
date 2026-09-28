"""Bluesky plan stubs for ``CarbideLaser``.

Unlike RTC6's jump/line/arc command-list plans, Carbide has no scan-head-style
command sequence - just settable parameters and discrete actions - so these
are small, named plans rather than geometry builders, closer to
``fastcs_rtc6.cut_shapes``'s domain-specific helpers than to
``fastcs_rtc6.plan_stubs``'s ``jump``/``line``/``arc``.

Not yet consumed by any ``mx-bluesky`` plan - see ``aithre_lasercontrols``'s
``WAY_FORWARD.md``.
"""

import bluesky.plan_stubs as bps

from fastcs_carbide.device import CarbideLaser


def apply_preset_and_enable(carbide: CarbideLaser, preset_index: int):
    """Select a preset, apply it, wait for Operational, then enable output."""
    yield from bps.abs_set(
        carbide.basic_settings.selected_preset_index, preset_index, wait=True
    )
    yield from bps.stage(carbide)
    yield from bps.trigger(carbide, wait=True)


def close_and_standby(carbide: CarbideLaser):
    """Close output and return to standby."""
    yield from bps.unstage(carbide)
    yield from bps.trigger(carbide.actions.go_to_standby, wait=True)


def set_attenuator(carbide: CarbideLaser, percentage: float):
    yield from bps.abs_set(
        carbide.basic_settings.target_attenuator_percentage, percentage, wait=True
    )


def reset_interlock(carbide: CarbideLaser):
    yield from bps.trigger(carbide.actions.reset_remote_interlock, wait=True)
