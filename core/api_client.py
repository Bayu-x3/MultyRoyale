import time
import logging
import requests
from typing import Dict, Any

logger = logging.getLogger("MoltyBot.API")


class APIError(Exception):
    def __init__(self, message: str, code: str = "UNKNOWN"):
        self.code = code
        super().__init__(f"[{code}] {message}")


class APIClient:

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "X-API-Key": api_key
        })
        self._last_request_time = 0.0

    # ================= CORE =================

    def _request(self, method: str, path: str, max_retries: int = 3,
                 retry_delay: float = 2.0, timeout: int = 10, **kwargs) -> Dict[str, Any]:

        url = f"{self.base_url}{path}"
        last_error = None

        for attempt in range(max_retries):
            try:
                # rate limit
                elapsed = time.time() - self._last_request_time
                if elapsed < 0.1:
                    time.sleep(0.1 - elapsed)

                res = self.session.request(method, url, timeout=timeout, **kwargs)
                self._last_request_time = time.time()

                data = res.json()

                if not data.get("success", True):
                    error = data.get("error", {})
                    code = error.get("code", "UNKNOWN")
                    msg = error.get("message", "Unknown error")

                    raise APIError(msg, code)

                return data

            except Exception as e:
                last_error = e
                logger.warning(f"Retry {attempt+1}/{max_retries} → {e}")
                time.sleep(retry_delay)

        raise last_error
    
    def register_agent_fast(self, game_id: str, agent_name: str):
        """Fast register: no retry, cepat buat sniping"""
        return self._request(
        "POST",
        f"/games/{game_id}/agents/register",
        max_retries=1,
        timeout=5,
        retry_delay=0,
        json={"name": agent_name}
    ).get("data", {})

    def get(self, path: str, **kwargs):
        return self._request("GET", path, **kwargs)

    def post(self, path: str, json: Dict = None, **kwargs):
        return self._request("POST", path, json=json, **kwargs)

    def put(self, path: str, json: Dict = None, **kwargs):
        return self._request("PUT", path, json=json, **kwargs)

    # ================= ACCOUNT =================

    def create_account(self, name: str = None) -> Dict:
        payload = {}
        if name:
            payload["name"] = name
        return self.post("/accounts", json=payload).get("data", {})

    def get_account(self) -> Dict:
        res = self.get("/accounts/me")

        print("\n=== DEBUG ACCOUNT ===")
        print(res)
        print("=====================\n")

        if not res or "data" not in res:
            logger.error(f"Invalid account response: {res}")
            return {}

        return res["data"]

    def set_wallet(self, wallet_address: str) -> Dict:
        return self.put("/accounts/wallet", json={
            "wallet_address": wallet_address
        }).get("data", {})

    def get_history(self, limit: int = 50):
        return self.get(f"/accounts/history?limit={limit}").get("data", [])

    # ================= GAME =================

    def list_games(self, status: str = "waiting"):
        try:
            return self.get(f"/games?status={status}", timeout=8).get("data", [])
        except:
            return []

    def list_games_fast(self, status: str = "waiting"):
        try:
            return self._request(
                "GET",
                f"/games?status={status}",
                max_retries=1,
                timeout=3,
                retry_delay=0
            ).get("data", [])
        except:
            return []

    def get_game(self, game_id: str):
        return self.get(f"/games/{game_id}").get("data", {})

    def create_game(self, host_name=None, map_size="medium", entry_type="free"):
        payload = {
            "mapSize": map_size,
            "entryType": entry_type
        }
        if host_name:
            payload["hostName"] = host_name

        return self.post("/games", json=payload).get("data", {})

    def register_agent(self, game_id: str, agent_name: str):
        return self.post(
            f"/games/{game_id}/agents/register",
            json={"name": agent_name}
        ).get("data", {})

    # ================= ACTION =================

    def get_state(self, game_id: str, agent_id: str):
        return self.get(f"/games/{game_id}/agents/{agent_id}/state").get("data", {})

    def take_action(self, game_id: str, agent_id: str, action: Dict):
        return self.post(
            f"/games/{game_id}/agents/{agent_id}/action",
            json={"action": action}
        )

    # ================= HELPER =================

    def move(self, game_id, agent_id, region_id):
        return self.take_action(game_id, agent_id, {
            "type": "move",
            "regionId": region_id
        })

    def explore(self, game_id, agent_id):
        return self.take_action(game_id, agent_id, {
            "type": "explore"
        })

    def attack(self, game_id, agent_id, target_id):
        return self.take_action(game_id, agent_id, {
            "type": "attack",
            "targetId": target_id,
            "targetType": "agent"
        })

    def rest(self, game_id, agent_id):
        return self.take_action(game_id, agent_id, {
            "type": "rest"
        })