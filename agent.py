#!/usr/bin/env python3
"""
node-device-guard — runs on each VPN node.
Receives a list of IPs to kick via HTTP POST /kick and calls:
    conntrack -D -s <ip>
to immediately drop existing connections for banned users.

Environment variables:
  NODE_KICK_PORT   (default: 9977) — port to listen on
  NODE_KICK_TOKEN  (required)      — shared secret, checked as Bearer token
"""
import asyncio
import hmac
import ipaddress
import logging
import os

from aiohttp import web

TOKEN: str = os.getenv("NODE_KICK_TOKEN", "").strip()
PORT: int = int(os.getenv("NODE_KICK_PORT", "9977"))
CONNTRACK_TIMEOUT: float = 5.0

logger = logging.getLogger(__name__)


def _is_valid_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


async def handle_kick(request: web.Request) -> web.Response:
    if TOKEN:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer ") or not hmac.compare_digest(auth[7:], TOKEN):
            logger.warning("kick rejected: bad token from %s", request.remote)
            return web.Response(status=401, text="Unauthorized")

    try:
        data = await request.json()
    except Exception:
        return web.Response(status=400, text="Invalid JSON")

    if not isinstance(data, dict):
        return web.Response(status=400, text="JSON body must be an object")

    ips = data.get("ips", [])
    if not isinstance(ips, list):
        return web.Response(status=400, text="'ips' must be a list")

    results: dict[str, str] = {}
    for raw in ips:
        addr = str(raw).strip()
        if not _is_valid_ip(addr):
            logger.warning("kick: invalid ip skipped: %r", addr)
            results[addr] = "invalid"
            continue

        try:
            proc = await asyncio.create_subprocess_exec(
                "ss", "-K", f"dst {addr}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=CONNTRACK_TIMEOUT)
            rc = proc.returncode
            if rc == 0:
                logger.info("kicked ip=%s", addr)
                results[addr] = "ok"
            else:
                logger.debug("ss -K ip=%s rc=%s stderr=%s", addr, rc, stderr.decode().strip())
                results[addr] = "not_found"
        except asyncio.TimeoutError:
            logger.error("ss -K timeout ip=%s", addr)
            results[addr] = "timeout"
        except FileNotFoundError:
            logger.error("ss not found — install iproute2 on this node")
            results[addr] = "ss_missing"
            break
        except Exception as exc:
            logger.error("ss -K error ip=%s: %r", addr, exc)
            results[addr] = "error"

    return web.json_response({"results": results})


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response({"ok": True})


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if not TOKEN:
        logger.warning("NODE_KICK_TOKEN is not set — /kick endpoint is unprotected!")

    app = web.Application()
    app.router.add_get("/health", handle_health)
    app.router.add_post("/kick", handle_kick)

    logger.info("node-device-guard listening on 0.0.0.0:%s", PORT)
    web.run_app(app, host="0.0.0.0", port=PORT, print=None)


if __name__ == "__main__":
    main()
