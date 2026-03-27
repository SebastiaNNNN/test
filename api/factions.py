from http.server import BaseHTTPRequestHandler

from api._common import firebase_get, read_json, send_json, validate_admin


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        send_json(self, 200, {"ok": True})

    def do_POST(self):
        body, err = read_json(self)
        if err:
            send_json(self, 400, {"ok": False, "msg": err})
            return

        ok, auth_err = validate_admin(body)
        if not ok:
            send_json(self, 401, {"ok": False, "msg": auth_err})
            return

        all_ok, all_users, all_err = firebase_get("users")
        if not all_ok:
            send_json(self, 502, {"ok": False, "msg": all_err})
            return

        if not isinstance(all_users, dict):
            send_json(self, 200, {"ok": True, "total_players": 0, "factions": []})
            return

        counters = {}
        for _, payload in all_users.items():
            if not isinstance(payload, dict):
                continue
            faction_name = str(payload.get("factiune", "Civil") or "Civil").strip() or "Civil"
            counters[faction_name] = counters.get(faction_name, 0) + 1

        rows = [{"name": name, "members": members} for name, members in counters.items()]
        rows.sort(key=lambda item: (-item["members"], item["name"].lower()))

        send_json(
            self,
            200,
            {
                "ok": True,
                "total_players": len(all_users),
                "factions": rows,
            },
        )
