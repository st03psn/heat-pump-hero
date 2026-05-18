#!/usr/bin/env python3
"""Install required HPH Lovelace frontend cards via HACS WebSocket API."""
import asyncio
import json
import sys

try:
    import websockets
except ImportError:
    print("ERROR: websockets not installed. Run: pip install websockets")
    sys.exit(1)

import os
from pathlib import Path

# Auto-load scripts/local.ps1 values if a .env companion exists.
# Create scripts/local.env (gitignored) with KEY=VALUE lines as an alternative
# to setting environment variables manually.
_env_file = Path(__file__).parent / "local.env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

HA_URL   = os.environ.get("HA_URL", "http://homeassistant.local:8123")
HA_URL   = HA_URL.replace("http://", "ws://").replace("https://", "wss://")
if not HA_URL.endswith("/api/websocket"):
    HA_URL = HA_URL.rstrip("/") + "/api/websocket"

HA_TOKEN = os.environ.get("HA_TOKEN", "")
if not HA_TOKEN:
    print("ERROR: HA_TOKEN not set.")
    print("  Option A: copy scripts/local.ps1.example → scripts/local.ps1 and fill in values")
    print("  Option B: create scripts/local.env with HA_URL=... and HA_TOKEN=... lines")
    print("  Option C: set $env:HA_TOKEN manually in your shell")
    sys.exit(1)

# full_name (GitHub owner/repo) for precise matching
REQUIRED_CARDS = [
    "piitaya/lovelace-mushroom",
    "RomRider/apexcharts-card",
    "Clooos/Bubble-Card",
    "custom-cards/button-card",
    "thomasloven/lovelace-auto-entities",
    "thomasloven/lovelace-card-mod",
]


async def send(ws, msg_id, msg_type, **kwargs):
    payload = {"id": msg_id, "type": msg_type, **kwargs}
    await ws.send(json.dumps(payload))
    while True:
        raw = await ws.recv()
        data = json.loads(raw)
        if data.get("id") == msg_id:
            return data


async def main():
    print(f"Connecting to {HA_URL} …")
    async with websockets.connect(HA_URL) as ws:
        # ── Auth ──────────────────────────────────────────────────────────────
        hello = json.loads(await ws.recv())
        print(f"HA version: {hello.get('ha_version', '?')}")

        await ws.send(json.dumps({"type": "auth", "access_token": HA_TOKEN}))
        auth_result = json.loads(await ws.recv())
        if auth_result.get("type") != "auth_ok":
            print(f"Auth failed: {auth_result}")
            return

        print("Authenticated.\n")

        # ── List HACS frontend repos ──────────────────────────────────────────
        print("Fetching HACS frontend repository list …")
        resp = await send(ws, 1, "hacs/repositories/list", categories=["plugin"])
        if not resp.get("success"):
            print(f"ERROR listing repos: {resp}")
            return

        repos = resp["result"]
        print(f"Found {len(repos)} plugin repositories in HACS.\n")

        # ── Match and install ─────────────────────────────────────────────────
        msg_id = 2
        for full_name in REQUIRED_CARDS:
            matches = [
                r for r in repos
                if r.get("full_name", "").lower() == full_name.lower()
            ]
            if not matches:
                print(f"  [?] {full_name:<45} — not found in HACS repo list")
                continue

            repo      = matches[0]
            repo_id   = str(repo["id"])
            name      = repo.get("name", repo_id)
            installed = repo.get("installed", False)
            version   = (
                repo.get("available_version")
                or repo.get("last_version")
                or repo.get("releases", [None])[0]
                or ""
            )

            if installed:
                print(f"  [OK] {name:<30} already installed (v{repo.get('installed_version', '?')})")
                continue

            if not version:
                # Fetch latest version info first
                info = await send(ws, msg_id, "hacs/repository/info", repository_id=repo_id)
                msg_id += 1
                if info.get("success"):
                    version = info["result"].get("available_version", "")

            print(f"  --> Installing {name:<28} (id={repo_id}, version={version}) …", end="", flush=True)
            kwargs = {"repository": repo_id}
            if version:
                kwargs["version"] = version
            result = await send(ws, msg_id, "hacs/repository/download", **kwargs)
            msg_id += 1

            if result.get("success"):
                print(" done.")
            else:
                err = result.get("error", {}).get("message", str(result))
                print(f" FAILED: {err}")

        print("\nDone. Reload the browser (Ctrl+Shift+R) to apply frontend resources.")


if __name__ == "__main__":
    asyncio.run(main())
