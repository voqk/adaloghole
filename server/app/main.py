"""FastAPI app entry. Mounts the device API and the admin portal.

    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"""

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from .routes_admin import router as admin_router
from .routes_device import router as device_router

app = FastAPI(title="AdalogHole")
app.include_router(device_router)
app.include_router(admin_router)


@app.get("/", include_in_schema=False)
def root():
    # The human entry point is the admin portal; the device POSTs to /classify.
    return RedirectResponse("/admin")
