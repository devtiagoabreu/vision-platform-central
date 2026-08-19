
from src.auth.password import hash_password
from src.storage.database import DeviceRecord, User
from tests.conftest import TestSession


def _create_admin():
    db = TestSession()
    if not db.query(User).filter(User.username == "admin").first():
        db.add(User(username="admin", password_hash=hash_password("admin"), role="admin"))
        db.commit()
    db.close()


def _login(client):
    _create_admin()
    client.post("/login", data={"username": "admin", "password": "admin"})


def _create_device(**kwargs):
    db = TestSession()
    defaults = {
        "device_id": "test_dev_001",
        "local_id": "LOCAL-001",
        "name": "Test Device",
        "device_type": "camera",
        "task_type": "fissure",
        "is_active": True,
    }
    defaults.update(kwargs)
    d = DeviceRecord(**defaults)
    db.add(d)
    db.commit()
    db.refresh(d)
    db.close()
    return d


# ── Page rendering ──

class TestDevicesPage:
    def test_devices_page_renders(self, client):
        _login(client)
        resp = client.get("/dashboard/devices")
        assert resp.status_code == 200
        assert "Devices" in resp.text

    def test_devices_page_shows_empty(self, client):
        _login(client)
        resp = client.get("/dashboard/devices")
        assert "Nenhum device registrado" in resp.text

    def test_devices_page_shows_device(self, client):
        _login(client)
        _create_device(device_id="cam_001", name="Camera 01", local_id="LOCAL-001")
        resp = client.get("/dashboard/devices")
        assert "cam_001" in resp.text
        assert "Camera 01" in resp.text
        assert "LOCAL-001" in resp.text

    def test_devices_page_requires_auth(self, client):
        resp = client.get("/dashboard/devices", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["location"] == "/login"


# ── Task types display ──

class TestTaskTypes:
    def test_all_task_types_in_template(self, client):
        _login(client)
        _create_device(device_id="d1", task_type="fissure")
        _create_device(device_id="d2", task_type="ppe")
        _create_device(device_id="d3", task_type="fabric_quality")
        _create_device(device_id="d4", task_type="structural")
        resp = client.get("/dashboard/devices")
        assert "fissure" in resp.text
        assert "ppe" in resp.text
        assert "fabric_quality" in resp.text
        assert "structural" in resp.text

    def test_multiple_device_types(self, client):
        _login(client)
        _create_device(device_id="cam1", device_type="camera")
        _create_device(device_id="sens1", device_type="sensor")
        _create_device(device_id="other1", device_type="other")
        resp = client.get("/dashboard/devices")
        assert "camera" in resp.text
        assert "sensor" in resp.text
        assert "other" in resp.text


# ── Multiple locals ──

class TestMultipleLocals:
    def test_devices_from_different_locals(self, client):
        _login(client)
        _create_device(device_id="d1", local_id="LOCAL-001")
        _create_device(device_id="d2", local_id="LOCAL-002")
        resp = client.get("/dashboard/devices")
        assert "LOCAL-001" in resp.text
        assert "LOCAL-002" in resp.text


# ── Active/inactive ──

class TestDeviceStatus:
    def test_inactive_device_shows(self, client):
        _login(client)
        _create_device(device_id="d_off", is_active=False)
        resp = client.get("/dashboard/devices")
        assert "d_off" in resp.text
        assert "Inativo" in resp.text
