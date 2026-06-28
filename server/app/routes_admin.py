"""Admin portal — the user's control panel.

    GET  /admin           render the current settings form
    POST /admin           save edited settings (key, model, prompt, program, thresholds)
    POST /admin/test      upload one frame and show the live classification (no muting)

Lets a user enter their own Anthropic key and tune the prompt without touching code.
No auth — LAN-trust. The API key is never echoed back into the form.
"""

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from . import routes_device
from .classifier import classify_frame
from .settings import Settings, get_settings, save_settings, set_settings

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
def admin_get(request: Request):
    return templates.TemplateResponse(
        request,
        "admin.html",
        {
            "s": get_settings(),
            "muted": routes_device.engine.muted,
            "test_result": None,
        },
    )


@router.post("")
def admin_post(
    request: Request,
    api_key: str = Form(""),
    model: str = Form(...),
    program: str = Form(...),
    system_prompt: str = Form(...),
    flip_threshold: int = Form(...),
    sample_interval_ms: int = Form(...),
):
    current = get_settings()
    new = Settings(
        api_key=api_key or current.api_key,  # blank field keeps the existing key
        model=model,
        program=program,
        system_prompt=system_prompt,
        flip_threshold=flip_threshold,
        sample_interval_ms=sample_interval_ms,
    )
    save_settings(new)
    set_settings(new)
    if new.flip_threshold != current.flip_threshold:
        routes_device.rebuild_engine()
    return RedirectResponse("/admin", status_code=303)  # POST -> redirect -> GET


@router.post("/test", response_class=HTMLResponse)
async def admin_test(request: Request, frame: UploadFile = File(...)):
    data = await frame.read()
    result = classify_frame(data, media_type=frame.content_type or "image/jpeg")
    return templates.TemplateResponse(
        request,
        "admin.html",
        {
            "s": get_settings(),
            "muted": routes_device.engine.muted,
            "test_result": result,
        },
    )
