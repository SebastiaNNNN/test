"""Utility helpers shared by Vercel Python API endpoints."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, List, Tuple
from urllib.parse import quote

import requests

ADMIN_KEY = os.environ.get("ADMIN_KEY", "")
DATABASE_URL = os.environ.get(
    "FIREBASE_DATABASE_URL",
    "https://projsmprobl-default-rtdb.europe-west1.firebasedatabase.app/",
)
FIREBASE_DB_SECRET = os.environ.get("FIREBASE_DB_SECRET", "")
PANEL_ORIGIN = os.environ.get("PANEL_ORIGIN", "*")


def _base_url() -> str:
    return DATABASE_URL.rstrip("/")


def _with_auth(url: str) -> str:
    if not FIREBASE_DB_SECRET:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}auth={FIREBASE_DB_SECRET}"


def firebase_url(path: str) -> str:
    cleaned = path.strip("/")
    return _with_auth(f"{_base_url()}/{cleaned}.json")


def read_json(handler) -> Tuple[Dict[str, Any], str | None]:
    try:
        length = int(handler.headers.get("Content-Length", 0))
    except ValueError:
        return {}, "Content-Length invalid"

    if length <= 0:
        return {}, None

    try:
        raw = handler.rfile.read(length)
        return json.loads(raw), None
    except Exception:
        return {}, "JSON invalid"


def cors(handler) -> None:
    handler.send_header("Access-Control-Allow-Origin", PANEL_ORIGIN)
    handler.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")


def send_json(handler, status: int, payload: Dict[str, Any]) -> None:
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    cors(handler)
    handler.end_headers()
    handler.wfile.write(json.dumps(payload).encode("utf-8"))


def validate_admin(body: Dict[str, Any]) -> Tuple[bool, str]:
    if not ADMIN_KEY:
        return False, "ADMIN_KEY lipseste in Vercel env"
    if body.get("adminKey") != ADMIN_KEY:
        return False, "Cheie admin invalida"
    return True, ""


def firebase_get(path: str) -> Tuple[bool, Any, str]:
    try:
        response = requests.get(firebase_url(path), timeout=10)
    except Exception as exc:
        return False, None, f"Conexiune Firebase esuata: {exc}"

    if response.status_code != 200:
        text = response.text[:300]
        return False, None, f"Firebase HTTP {response.status_code}: {text}"

    try:
        return True, response.json(), ""
    except Exception:
        return False, None, "Raspuns Firebase invalid (nu e JSON)"


def player_summary(username: str, data: Dict[str, Any]) -> Dict[str, Any]:
    cars = data.get("masini")
    if not isinstance(cars, list):
        cars = []

    house_owned = data.get("casa_detinuta")
    if house_owned is None:
        house_owned = data.get("OwnedHouseID", 0)

    return {
        "username": username,
        "rp_name": data.get("nume_rp") or username,
        "avatar_url": data.get("avatar_url", ""),
        "last_online": data.get("last_online", "-"),
        "level": int(data.get("level", 0) or 0),
        "rp": int(data.get("rp", 0) or 0),
        "job": data.get("job_curent", "None"),
        "faction": data.get("factiune", "Civil"),
        "rank": int(data.get("rank", 0) or 0),
        "admin_level": int(data.get("admin", 0) or 0),
        "cash": int(data.get("banii_cash", 0) or 0),
        "bank": int(data.get("banii_banca", 0) or 0),
        "hours": float(data.get("ore_jucate", 0) or 0),
        "house_owned": int(house_owned or 0),
        "garage_slots": int(data.get("sloturi_garaj", 0) or 0),
        "cars_count": int(data.get("masini_detinute", len(cars)) or 0),
        "cars": cars,
    }


def compact_player(username: str, data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "username": username,
        "rp_name": data.get("nume_rp") or username,
        "faction": data.get("factiune", "Civil"),
        "level": int(data.get("level", 0) or 0),
        "admin_level": int(data.get("admin", 0) or 0),
        "cash": int(data.get("banii_cash", 0) or 0),
        "cars_count": int(data.get("masini_detinute", 0) or 0),
        "house_owned": int(data.get("casa_detinuta", 0) or 0),
        "last_online": data.get("last_online", "-"),
    }


def normalize_query(value: str) -> str:
    return (value or "").strip().lower()


def find_case_insensitive_key(keys: Iterable[str], target: str) -> str | None:
    normalized = normalize_query(target)
    for key in keys:
        if key.lower() == normalized:
            return key
    return None


def search_users(users: Dict[str, Dict[str, Any]], raw_query: str, limit: int) -> List[Dict[str, Any]]:
    query = normalize_query(raw_query)
    candidates: List[Tuple[int, str, Dict[str, Any]]] = []

    for username, data in users.items():
        uname = username.lower()
        if query:
            if uname.startswith(query):
                score = 0
            elif query in uname:
                score = 1
            else:
                continue
        else:
            score = 2

        candidates.append((score, username, data))

    candidates.sort(key=lambda item: (item[0], item[1].lower()))

    result: List[Dict[str, Any]] = []
    for _, username, data in candidates[:limit]:
        result.append(compact_player(username, data if isinstance(data, dict) else {}))

    return result


def safe_username_path(username: str) -> str:
    # Roblox usernames are URL-safe, but keep this defensive.
    return quote(username, safe="")
