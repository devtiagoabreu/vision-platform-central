import logging

import httpx

from src.config.settings import settings

logger = logging.getLogger(__name__)


class LocalClient:
    def __init__(self, base_url: str | None = None, token: str | None = None):
        self.base_url = (base_url or settings.local_api_base_url).rstrip("/")
        self.token = token or settings.local_api_token

    def _headers(self) -> dict:
        return {"X-Api-Token": self.token}

    def health(self) -> dict | None:
        try:
            resp = httpx.get(f"{self.base_url}/health", timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("Failed to reach local health: %s", e)
            return None

    def list_observations(self, cursor: str | None = None) -> dict:
        params = {}
        if cursor:
            params["cursor"] = cursor
        try:
            resp = httpx.get(
                f"{self.base_url}/api/v1/observations",
                params=params,
                headers=self._headers(),
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("Failed to list observations: %s", e)
            return {"observations": [], "next_cursor": None}

    def ack_observation(self, observation_id: str) -> bool:
        try:
            resp = httpx.post(
                f"{self.base_url}/api/v1/observations/{observation_id}/ack",
                headers=self._headers(),
                timeout=10,
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error("Failed to ack observation %s: %s", observation_id, e)
            return False
