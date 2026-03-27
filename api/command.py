from http.server import BaseHTTPRequestHandler
import json
import os
import requests

from api._common import read_json, send_json, validate_admin

ROBLOX_API_KEY = os.environ.get("ROBLOX_API_KEY", "")
UNIVERSE_ID = os.environ.get("UNIVERSE_ID", "")
ROBLOX_URL = (
    f"https://apis.roblox.com/messaging-service/v1/universes/{UNIVERSE_ID}/topics/DiscordCommands"
)


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        send_json(self, 200, {"ok": True})

    def do_POST(self):
        body, err = read_json(self)
        if err:
            send_json(self, 400, {"ok": False, "msg": err, "message": err})
            return

        ok, auth_err = validate_admin(body)
        if not ok:
            send_json(self, 401, {"ok": False, "msg": auth_err, "message": auth_err})
            return

        cmd_type = str(body.get("type", "")).strip()
        target = str(body.get("target", "")).strip()

        if not cmd_type or not target:
            msg = "type si target sunt obligatorii"
            send_json(self, 400, {"ok": False, "msg": msg, "message": msg})
            return

        if not ROBLOX_API_KEY or not UNIVERSE_ID:
            msg = "Lipsesc ROBLOX_API_KEY / UNIVERSE_ID in env vars"
            send_json(self, 500, {"ok": False, "msg": msg, "message": msg})
            return

        payload = {
            "Admin": body.get("adminName", "WebPanel"),
            "Type": cmd_type,
            "Target": target,
            "Value": str(body.get("value", "0")),
            "Reason": body.get("reason", "Admin Panel"),
        }

        request_body = {"message": json.dumps(payload)}
        headers = {"x-api-key": ROBLOX_API_KEY, "Content-Type": "application/json"}

        try:
            response = requests.post(ROBLOX_URL, headers=headers, json=request_body, timeout=10)
        except requests.exceptions.Timeout:
            msg = "Timeout la conexiunea cu Roblox API"
            send_json(self, 200, {"ok": False, "msg": msg, "message": msg})
            return
        except Exception as exc:
            msg = f"Eroare la trimitere: {exc}"
            send_json(self, 500, {"ok": False, "msg": msg, "message": msg})
            return

        if response.status_code == 200:
            msg = "Comanda trimisa cu succes"
            send_json(self, 200, {"ok": True, "msg": msg, "message": msg})
            return

        msg = f"Roblox API HTTP {response.status_code}: {response.text[:220]}"
        send_json(self, 200, {"ok": False, "msg": msg, "message": msg})
