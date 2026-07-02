"""Controller role: the web admin portal — override knob, status display, settings.

    GET  /admin           status strip + settings forms
    POST /admin           save generic Settings + any implementation-private
                          fieldsets (fields named "<admin_id>__<field>")
    POST /admin/control   override knob (auto / force mute / force unmute / lock)
    POST /admin/test      classify one uploaded frame (does not touch mute state)

No auth — LAN-trust. Secrets are never echoed back into the form.
"""

from pathlib import Path

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool

from ...contracts import Context, Control, GenericSettings

TEMPLATES_DIR = Path(__file__).resolve().parents[3] / "templates"

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _context(request: Request, test_result=None) -> dict:
    brain = request.app.state.brain
    return {
        "s": brain.get_settings(),
        "status": brain.status(),
        "configurables": [
            {"admin_id": c.admin_id, "title": c.admin_title, "fields": c.admin_fields()}
            for c in request.app.state.configurables
        ],
        "test_result": test_result,
    }


@router.get("", response_class=HTMLResponse)
def admin_get(request: Request):
    return templates.TemplateResponse(request, "admin.html", _context(request))


@router.post("")
async def admin_post(request: Request):
    form = {k: v for k, v in (await request.form()).items() if isinstance(v, str)}
    brain = request.app.state.brain

    current = brain.get_settings()
    brain.put_settings(GenericSettings(
        sample_interval_s=float(form.get("sample_interval_s", current.sample_interval_s)),
        flip_threshold=int(form.get("flip_threshold", current.flip_threshold)),
        program=form.get("program", current.program),
        soundbar_music_enabled=current.soundbar_music_enabled,
    ))

    for c in request.app.state.configurables:
        prefix = f"{c.admin_id}__"
        fields = {k[len(prefix):]: v for k, v in form.items() if k.startswith(prefix)}
        if fields:
            c.apply_admin_fields(fields)

    return RedirectResponse("/admin", status_code=303)  # POST -> redirect -> GET


@router.post("/control")
async def admin_control(request: Request):
    form = await request.form()
    choice = form.get("override", "auto")
    if choice == "lock":
        control = Control(override="auto", lock=True)
    else:
        control = Control(override=choice)
    request.app.state.brain.control(control)
    return RedirectResponse("/admin", status_code=303)


@router.post("/test", response_class=HTMLResponse)
async def admin_test(request: Request, frame: UploadFile = File(...)):
    data = await frame.read()
    brain = request.app.state.brain
    classifier = request.app.state.classifier
    context = Context(program=brain.get_settings().program)
    verdict = await run_in_threadpool(
        classifier.classify, data, frame.content_type or "image/jpeg", context
    )
    return templates.TemplateResponse(
        request, "admin.html", _context(request, test_result=verdict)
    )
