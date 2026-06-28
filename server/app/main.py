"""FastAPI app entry. Mounts the device API and the admin portal.

    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"""

import logging
import os
import socket
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from .routes_admin import router as admin_router
from .routes_device import router as device_router

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    port = os.environ.get("ADALOGHOLE_PORT", "8000")
    ip = _lan_ip()
    if ip:
        logger.info("AdalogHole admin portal:    http://%s:%s/admin", ip, port)
        logger.info(
            "AdalogHole device endpoint: http://%s:%s/classify  "
            "(use as SERVER_URL in firmware/include/config.h)",
            ip,
            port,
        )
    else:
        logger.info("AdalogHole running on port %s (could not detect a LAN IP)", port)
    yield


app = FastAPI(title="AdalogHole", lifespan=lifespan)
app.include_router(device_router)
app.include_router(admin_router)


@app.get("/", include_in_schema=False)
def root():
    # The human entry point is the admin portal; the device POSTs to /classify.
    return RedirectResponse("/admin")
