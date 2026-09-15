import httpx
import pytest
import respx

from carbide_fastcs.connection import CarbideConnection

BASE_URL = "http://192.168.240.10:20010"


@pytest.fixture
async def conn():
    connection = CarbideConnection(BASE_URL)
    yield connection
    await connection.close()


@respx.mock
async def test_serial_number_get(conn: CarbideConnection):
    route = respx.get(f"{BASE_URL}/v1/Basic/SerialNumber").mock(
        return_value=httpx.Response(200, json="SN12345")
    )
    assert await conn.serial_number() == "SN12345"
    assert route.called


@respx.mock
async def test_is_output_enabled_true(conn: CarbideConnection):
    respx.get(f"{BASE_URL}/v1/Basic/IsOutputEnabled").mock(
        return_value=httpx.Response(200, json=True)
    )
    assert await conn.is_output_enabled() is True


@respx.mock
async def test_is_output_enabled_false(conn: CarbideConnection):
    respx.get(f"{BASE_URL}/v1/Basic/IsOutputEnabled").mock(
        return_value=httpx.Response(200, json=False)
    )
    assert await conn.is_output_enabled() is False


@respx.mock
async def test_actual_state_name_unwraps_json_string(conn: CarbideConnection):
    """The original laserControl.py compared raw response text, which for a
    JSON string endpoint includes the quotes (e.g. '"Operational"'). This
    wrapper decodes with .json() instead, so the returned value should be
    the bare string with no quotes."""
    respx.get(f"{BASE_URL}/v1/Basic/ActualStateName").mock(
        return_value=httpx.Response(200, json="Operational")
    )
    assert await conn.actual_state_name() == "Operational"


@respx.mock
async def test_actual_shutter_state_is_string(conn: CarbideConnection):
    """The vendor API documents ActualShutterState as one of "Opened"/
    "Closed" - a JSON string, not an int (caught by cross-referencing the
    real DiamondLightSource/aithre production GUI, which compares against
    those exact strings)."""
    respx.get(f"{BASE_URL}/v1/Basic/ActualShutterState").mock(
        return_value=httpx.Response(200, json="Closed")
    )
    value = await conn.actual_shutter_state()
    assert value == "Closed"
    assert isinstance(value, str)


@respx.mock
async def test_actual_attenuator_percentage_is_float(conn: CarbideConnection):
    respx.get(f"{BASE_URL}/v1/Basic/ActualAttenuatorPercentage").mock(
        return_value=httpx.Response(200, json=42.5)
    )
    value = await conn.actual_attenuator_percentage()
    assert value == 42.5
    assert isinstance(value, float)


@respx.mock
async def test_set_selected_preset_index_sends_put_with_json_body(
    conn: CarbideConnection,
):
    route = respx.put(f"{BASE_URL}/v1/Basic/SelectedPresetIndex").mock(
        return_value=httpx.Response(200)
    )
    await conn.set_selected_preset_index(5)
    assert route.called
    request = route.calls.last.request
    assert request.headers["Content-Type"] == "application/json"
    assert request.content == b"5"


@respx.mock
async def test_apply_selected_preset_sends_post(conn: CarbideConnection):
    route = respx.post(f"{BASE_URL}/v1/Basic/ApplySelectedPreset").mock(
        return_value=httpx.Response(200)
    )
    await conn.apply_selected_preset()
    assert route.called


@respx.mock
async def test_403_response_raises(conn: CarbideConnection):
    respx.post(f"{BASE_URL}/v1/Basic/EnableOutput").mock(
        return_value=httpx.Response(403)
    )
    with pytest.raises(httpx.HTTPStatusError):
        await conn.enable_output()


@respx.mock
async def test_reduce_leak_sends_post_to_advanced_endpoint(conn: CarbideConnection):
    """Confirmed unused operationally, but the endpoint mapping should
    still be exactly right if it's ever needed."""
    route = respx.post(f"{BASE_URL}/v1/Advanced/ReduceLeak").mock(
        return_value=httpx.Response(200)
    )
    await conn.reduce_leak()
    assert route.called


@respx.mock
async def test_set_aom_trigger_source_sends_string_body(conn: CarbideConnection):
    route = respx.put(f"{BASE_URL}/v1/ExternalControl/AomTriggerSource").mock(
        return_value=httpx.Response(200)
    )
    await conn.set_aom_trigger_source("Internal")
    request = route.calls.last.request
    assert request.content == b'"Internal"'


@respx.mock
async def test_toggle_pulse_picker_endpoints_are_unambiguous(conn: CarbideConnection):
    """enable_pp/disable_pp map 1:1 to EnablePp/DisablePp - no inverted
    "toggle" semantics like the original togglePulsePicker(toggle="off")
    calling EnablePp."""
    enable_route = respx.post(f"{BASE_URL}/v1/Advanced/EnablePp").mock(
        return_value=httpx.Response(200)
    )
    disable_route = respx.post(f"{BASE_URL}/v1/Advanced/DisablePp").mock(
        return_value=httpx.Response(200)
    )
    await conn.enable_pp()
    await conn.disable_pp()
    assert enable_route.called
    assert disable_route.called
