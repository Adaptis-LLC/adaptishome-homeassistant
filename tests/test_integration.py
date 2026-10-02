"""Інтеграція в живому HA: config flow, сутності з відповіді хаба, подія на шині, повторний вхід."""
import json

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.adaptishome.const import CONF_OBJECTS, DOMAIN, EVENT, HUB

SNAP = {
    "id": "HHT0TEST001", "name": "Будинок · Тест", "status": "failover", "last_seen": 1790782902, "active": "wan2", "primary": "wan1",
    "rx_mbps": 12, "tx_mbps": 3, "rtt_ms": 14,
    "channels": [
        {"id": "wan1", "kind": "cable", "name": "Провайдер 1", "desc": "Порт 1", "state": "down", "rtt_ms": None, "loss_pct": None, "month_gb": 1.5, "avail": "-" * 40 + "oooooxxx", "link_mbps": None},
        {"id": "wan2", "kind": "cable", "name": "Провайдер 2", "desc": "Порт 2", "state": "active", "rtt_ms": 14, "loss_pct": 0, "month_gb": 0.2, "avail": "-" * 40 + "oooooooo", "link_mbps": None},
        {"id": "wan4", "kind": "lte", "name": "LTE", "desc": "USB-модем", "state": "ready", "rtt_ms": 40, "loss_pct": 1, "month_gb": 0.0, "avail": "-" * 48, "rsrp_dbm": -88},
    ],
    "events": [{"ts": 1790782800, "kind": "failover", "to": "wan2", "from": ["wan1"]}, {"ts": 1790782700, "kind": "boot"}],
    "traffic_days": [{"date": "2026-09-30", "gb": 0.4}, {"date": "2026-10-01", "gb": 1.2}],
    "uptime30": {"total_pct": 99.9, "primary_pct": 97.5, "saved_s": 3600, "saves": 2},
    "device": {"model": "hAP ac^2", "serial": "HHT0TEST001", "config_version": 3, "uptime_s": 93784},
}


def mock_hub(aioclient_mock, snap=SNAP, login_status=200, hub_url=None):
    aioclient_mock.get(f"{HUB}/api/hub", json={"url": hub_url})
    aioclient_mock.post(f"{HUB}/api/login", status=login_status, json={"token": "t0k", "name": "Олена", "role": "client"})
    aioclient_mock.get(f"{HUB}/api/devices", json=[{"id": snap["id"], "name": snap["name"], "status": snap["status"], "demo": False, "access": "manage"}])
    aioclient_mock.get(f"{HUB}/api/device?id={snap['id']}", json=snap)


async def setup_entry(hass: HomeAssistant, aioclient_mock) -> MockConfigEntry:
    mock_hub(aioclient_mock)
    entry = MockConfigEntry(domain=DOMAIN, data={"username": "olena@x", "password": "pw", "name": "Олена"}, options={CONF_OBJECTS: [SNAP["id"]]})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_config_flow_creates_entry(hass: HomeAssistant, aioclient_mock) -> None:
    mock_hub(aioclient_mock)
    r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert r["type"] == FlowResultType.FORM and r["step_id"] == "user"
    assert "hub" not in r["data_schema"].schema                      # адреса хаба зашита: лише логін і пароль
    r = await hass.config_entries.flow.async_configure(r["flow_id"], {"username": "olena@x", "password": "pw"})
    assert r["type"] == FlowResultType.CREATE_ENTRY
    assert r["title"] == "AdaptisHome · Олена" and r["options"] == {CONF_OBJECTS: [SNAP["id"]]}
    assert json.loads(aioclient_mock.mock_calls[0][2].decode() if isinstance(aioclient_mock.mock_calls[0][2], bytes) else json.dumps(aioclient_mock.mock_calls[0][2]))["login"] == "olena@x"


async def test_config_flow_bad_password(hass: HomeAssistant, aioclient_mock) -> None:
    mock_hub(aioclient_mock, login_status=401)
    r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    r = await hass.config_entries.flow.async_configure(r["flow_id"], {"username": "olena@x", "password": "bad"})
    assert r["type"] == FlowResultType.FORM and r["errors"] == {"base": "invalid_auth"}


async def test_entities_from_snapshot(hass: HomeAssistant, aioclient_mock) -> None:
    await setup_entry(hass, aioclient_mock)
    st = hass.states
    assert st.get("sensor.budinok_test_status").state == "failover"
    assert st.get("sensor.budinok_test_status").attributes["serial"] == "HHT0TEST001"
    assert st.get("sensor.budinok_test_active_channel").state == "Провайдер 2"
    assert st.get("sensor.budinok_test_latency").state == "14"
    assert st.get("sensor.budinok_test_traffic_today").state == "1.2"
    assert st.get("sensor.budinok_test_internet_uptime_30_days").state == "99.9"
    assert st.get("binary_sensor.budinok_test_internet_via_backup").state == "on"
    assert st.get("binary_sensor.budinok_test_online").state == "on"
    assert st.get("sensor.budinok_test_provaider_1_state").state == "down"
    assert st.get("sensor.budinok_test_provaider_1_state").attributes["channel"] == "wan1"
    assert st.get("sensor.budinok_test_provaider_2_state").attributes["priority"] == 2
    assert st.get("sensor.budinok_test_lte_signal").state == "-88"                # лише в LTE-каналу
    assert st.get("sensor.budinok_test_provaider_1_signal") is None
    assert st.get("binary_sensor.budinok_test_provaider_2").state == "on"
    assert st.get("binary_sensor.budinok_test_provaider_1").state == "off"
    # вимкнені за замовчуванням не створюють стану, поки їх не ввімкнуть
    assert st.get("sensor.budinok_test_download") is None


async def test_new_event_on_bus_and_event_entity(hass: HomeAssistant, aioclient_mock) -> None:
    entry = await setup_entry(hass, aioclient_mock)
    seen = []
    hass.bus.async_listen(EVENT, lambda e: seen.append(e.data))
    # нова подія на хабі: повернення на основний канал
    snap = {**SNAP, "status": "ok", "active": "wan1", "events": [{"ts": 1790783000, "kind": "return", "to": "wan1"}] + SNAP["events"]}
    aioclient_mock.clear_requests(); mock_hub(aioclient_mock, snap)
    await entry.runtime_data.async_refresh(); await hass.async_block_till_done()
    assert seen == [{"object_id": SNAP["id"], "object": "Будинок · Тест", "kind": "return", "ts": 1790783000, "to": "Провайдер 1", "from": []}]
    assert hass.states.get("sensor.budinok_test_status").state == "ok"
    ev = hass.states.get("event.budinok_test_event")
    assert ev.attributes["event_type"] == "return" and ev.attributes["to"] == "Провайдер 1"
    # перше опитування старих подій не переказує: лише одна подія на шині
    assert len(seen) == 1


async def test_follows_moved_hub(hass: HomeAssistant, aioclient_mock) -> None:
    # хаб віддає нову адресу — інтеграція запам'ятовує її і далі ходить туди
    new = "https://home.adaptis.example"
    aioclient_mock.get(f"{HUB}/api/hub", json={"url": new + "/"})
    aioclient_mock.post(f"{HUB}/api/login", json={"token": "t0k", "name": "Олена", "role": "client"})
    aioclient_mock.get(f"{new}/api/device?id={SNAP['id']}", json=SNAP)
    entry = MockConfigEntry(domain=DOMAIN, data={"username": "olena@x", "password": "pw", "name": "Олена"}, options={CONF_OBJECTS: [SNAP["id"]]})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.data["hub"] == new
    assert hass.states.get("sensor.budinok_test_status").state == "failover"   # дані вже з нової адреси


async def test_card_resource_registered(hass: HomeAssistant, aioclient_mock, hass_client) -> None:
    await setup_entry(hass, aioclient_mock)
    client = await hass_client()
    r = await client.get("/adaptishome/adaptishome-card.js")
    assert r.status == 200 and "customElements.define('adaptishome-card'" in await r.text()


async def test_reauth_on_expired_session(hass: HomeAssistant, aioclient_mock) -> None:
    entry = await setup_entry(hass, aioclient_mock)
    aioclient_mock.clear_requests()
    aioclient_mock.post(f"{HUB}/api/login", status=401, json={"error": "невірний логін або пароль"})
    aioclient_mock.get(f"{HUB}/api/device?id={SNAP['id']}", status=401, json={"error": "потрібен вхід"})
    await entry.runtime_data.async_refresh(); await hass.async_block_till_done()
    flows = [f for f in hass.config_entries.flow.async_progress() if f["handler"] == DOMAIN]
    assert flows and flows[0]["context"]["source"] == "reauth"
