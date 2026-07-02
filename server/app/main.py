"""FastAPI app entry. Wires the five roles from adaloghole.toml and mounts the
Brain's HTTP surface plus the admin portal.

    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

If you run uvicorn on a non-default port, set ADALOGHOLE_PORT to match so the
in-process sensor and the logged URLs point at the right place.
"""

import logging
import os
import socket
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from .bootstrap import build_state, start_sensor
from .config import Config, load_config
from .routes_brain import router as brain_router
from .roles.controller.admin import router as admin_router

logger = logging.getLogger("uvicorn.error")


def _lan_ip() -> str | None:
    """Best-effort primary outbound IPv4. Opens a UDP socket toward a public address
    (no packets are actually sent) and reads back which local interface would be used.
    Note: inside WSL2/containers this is the NAT address, not the host's LAN IP."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return None
    finally:
        sock.close()


def create_app(config: Config | None = None) -> FastAPI:
    cfg = config or load_config()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        port = os.environ.get("ADALOGHOLE_PORT") or str(cfg.server()["port"])
        ip = _lan_ip()
        if ip:
            logger.info("AdalogHole admin portal:    http://%s:%s/admin", ip, port)
            logger.info(
                "AdalogHole frame endpoint:  http://%s:%s/frame  "
                "(/classify kept as the firmware-compatible alias)", ip, port,
            )
        else:
            logger.info("AdalogHole running on port %s (could not detect a LAN IP)", port)

        sensor = start_sensor(cfg, brain_url=f"http://127.0.0.1:{port}")
        yield
        if sensor is not None:
            _, stop = sensor
            stop.set()

    app = FastAPI(title="AdalogHole", lifespan=lifespan)
    state = build_state(cfg)
    app.state.config = state.config
    app.state.classifier = state.classifier
    app.state.actuator = state.actuator
    app.state.brain = state.brain
    app.state.configurables = state.configurables
    app.include_router(brain_router)
    app.include_router(admin_router)

    @app.get("/", include_in_schema=False)
    def root():
        # The human entry point is the admin portal; sensors POST to /frame.
        return RedirectResponse("/admin")

    return app


app = create_app()
