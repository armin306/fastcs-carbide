import httpx
import pytest
import respx

from fastcs_carbide.controller.carbide_controller import CarbideController

BASE_URL = "http://192.168.240.10:20010"


@pytest.fixture
async def controller():
    ctrl = CarbideController(BASE_URL)
    yield ctrl
    await ctrl.close()


@respx.mock
async def test_wait_for_operational_exits_on_operational(
    controller: CarbideController,
):
    respx.get(f"{BASE_URL}/v1/Basic/ActualStateName").mock(
        return_value=httpx.Response(200, json="Operational")
    )
    status_controller = controller.status
    # Should return immediately, not hang - this is the regression this
    # test exists to catch.
    await status_controller.wait_for_operational(poll_interval=0)


@respx.mock
async def test_wait_for_operational_raises_on_failure(
    controller: CarbideController,
):
    respx.get(f"{BASE_URL}/v1/Basic/ActualStateName").mock(
        return_value=httpx.Response(200, json="Failure")
    )
    status_controller = controller.status
    with pytest.raises(RuntimeError, match="Failure"):
        await status_controller.wait_for_operational(poll_interval=0)


@respx.mock
async def test_wait_for_operational_polls_until_operational(
    controller: CarbideController,
):
    """Simulates the state transitioning through a couple of intermediate
    states before reaching Operational - the loop must keep polling, not
    exit early or misinterpret an intermediate state as terminal."""
    states = iter(["Initializing", "Housekeeping", "Operational"])
    route = respx.get(f"{BASE_URL}/v1/Basic/ActualStateName")
    route.mock(side_effect=lambda request: httpx.Response(200, json=next(states)))

    status_controller = controller.status
    await status_controller.wait_for_operational(poll_interval=0)
    assert route.call_count == 3


@respx.mock
async def test_connect_populates_info(controller: CarbideController):
    respx.get(f"{BASE_URL}/v1/Basic/LaserIdentificationNumber").mock(
        return_value=httpx.Response(200, json="LID-1")
    )
    respx.get(f"{BASE_URL}/v1/Basic/SerialNumber").mock(
        return_value=httpx.Response(200, json="SN-1")
    )
    await controller.connect()
    info = controller.info
    assert info.laser_identification_number.get() == "LID-1"
    assert info.serial_number.get() == "SN-1"


@respx.mock
async def test_polling_handler_updates_attribute(controller: CarbideController):
    """One representative PollingHandler-backed AttrR, to check the
    handler/attribute wiring actually works end to end, not just that the
    connection method it delegates to works (covered in test_connection.py)."""
    respx.get(f"{BASE_URL}/v1/Basic/ActualStateName").mock(
        return_value=httpx.Response(200, json="Operational")
    )
    status_controller = controller.status
    attr = status_controller.actual_state_name
    handler = attr.updater
    assert handler is not None
    await handler.update(status_controller, attr)
    assert attr.get() == "Operational"


@respx.mock
async def test_polling_handler_survives_http_error(controller: CarbideController):
    """A failed poll should be logged and skipped, not raised - a
    transient network error shouldn't crash the IOC's scan loop."""
    respx.get(f"{BASE_URL}/v1/Basic/ActualStateName").mock(
        return_value=httpx.Response(500)
    )
    status_controller = controller.status
    attr = status_controller.actual_state_name
    handler = attr.updater
    assert handler is not None
    await handler.update(status_controller, attr)  # should not raise
