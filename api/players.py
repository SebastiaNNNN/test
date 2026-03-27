from http.server import BaseHTTPRequestHandler

from api._common import firebase_get, read_json, search_users, send_json, validate_admin


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

        query = str(body.get("query", "")).strip()
        try:
            limit = int(body.get("limit", 20) or 20)
        except Exception:
            limit = 20
        limit = max(1, min(limit, 50))

        all_ok, all_users, all_err = firebase_get("users")
        if not all_ok:
            send_json(self, 502, {"ok": False, "msg": all_err})
            return

        if not isinstance(all_users, dict):
            send_json(self, 200, {"ok": True, "count": 0, "users": []})
            return

        found = search_users(all_users, query, limit)
        send_json(self, 200, {"ok": True, "count": len(found), "users": found})
