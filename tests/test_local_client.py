from unittest.mock import MagicMock, patch

import pytest

from src.collector.local_client import LocalClient


@pytest.fixture
def client():
    return LocalClient(
        base_url="http://localhost:8080",
        token="test-token",
    )


class TestLocalClientHealth:
    @patch("src.collector.local_client.httpx.get")
    def test_health_success(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": "ok"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = client.health()
        assert result == {"status": "ok"}
        mock_get.assert_called_once_with("http://localhost:8080/health", timeout=10)

    @patch("src.collector.local_client.httpx.get")
    def test_health_failure(self, mock_get, client):
        mock_get.side_effect = Exception("connection refused")

        result = client.health()
        assert result is None


class TestLocalClientListObservations:
    @patch("src.collector.local_client.httpx.get")
    def test_list_observations(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "observations": [{"observation_id": "obs1"}],
            "next_cursor": None,
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = client.list_observations()
        assert len(result["observations"]) == 1

    @patch("src.collector.local_client.httpx.get")
    def test_list_observations_with_cursor(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"observations": [], "next_cursor": None}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        client.list_observations(cursor="obs_abc")
        call_params = mock_get.call_args
        assert call_params[1]["params"] == {"cursor": "obs_abc"}

    @patch("src.collector.local_client.httpx.get")
    def test_list_observations_failure(self, mock_get, client):
        mock_get.side_effect = Exception("timeout")

        result = client.list_observations()
        assert result["observations"] == []
        assert result["next_cursor"] is None


class TestLocalClientAckObservation:
    @patch("src.collector.local_client.httpx.post")
    def test_ack_success(self, mock_post, client):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = client.ack_observation("obs123")
        assert result is True
        mock_post.assert_called_once_with(
            "http://localhost:8080/api/v1/observations/obs123/ack",
            headers={"X-Api-Token": "test-token"},
            timeout=10,
        )

    @patch("src.collector.local_client.httpx.post")
    def test_ack_failure(self, mock_post, client):
        mock_post.side_effect = Exception("connection refused")

        result = client.ack_observation("obs123")
        assert result is False
