"""FastAPI web app: the remote UI plus a thin VLC HTTP client."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src import settings
from src.shortcuts import Shortcuts
from src.vlc_client import VLCClient

log = logging.getLogger(__name__)

shortcuts = Shortcuts(settings.DB)
vlc = VLCClient()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Optional "open" command, sent once at startup (empty by default).
    startup_command = shortcuts.get("open_vlc")
    if startup_command:
        ok, error = vlc.send(startup_command)
        if not ok:
            log.warning("Startup command failed: %s", error)
    yield


app = FastAPI(title="VLC remote control", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "templates")
)
# Local stylesheet: no CDN needed, so the UI works on an offline LAN.
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")),
    name="static",
)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/help", response_class=HTMLResponse)
async def help_page(request: Request):
    return templates.TemplateResponse(request=request, name="help.html")


@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)


@app.get("/health")
def health():
    """Liveness check for Docker and load balancers."""
    return {"status": "ok", "vlc_target": f"{settings.VLC_HOST}:{settings.VLC_HTTP_PORT}"}


@app.get("/status")
def status():
    """Debug endpoint showing what the app sees on the VLC machine."""
    return vlc.status()


@app.get("/action/{command}")
def action(command: str):
    configured = shortcuts.get_all()
    if command not in configured:
        return JSONResponse(
            {"ok": False, "error": f"Unknown command: {command}"}, status_code=404
        )

    ok, error = vlc.send(configured[command])
    if not ok:
        return JSONResponse({"ok": False, "error": error}, status_code=502)
    return {"ok": True, "command": command}


@app.get("/config", response_class=HTMLResponse)
async def config(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="config.html",
        context={"shortcuts": shortcuts.get_all()},
    )


@app.post("/config", response_class=HTMLResponse)
async def update_config(request: Request):
    form = await request.form()
    data = {key: str(value).strip() for key, value in form.items()}

    save = data.pop("save", None)
    reset = data.pop("reset", None)
    message = None

    if save is not None:
        shortcuts.update(data)
        message = (
            "Configurations updated successfully"
            if shortcuts.persistent
            else "Updated in memory only - config storage is not writable (see container logs)"
        )
    elif reset is not None:
        shortcuts.reset()
        message = (
            "Configuration reset successfully"
            if shortcuts.persistent
            else "Reset in memory only - config storage is not writable (see container logs)"
        )

    return templates.TemplateResponse(
        request=request,
        name="config.html",
        context={"shortcuts": shortcuts.get_all(), "message": message},
    )
