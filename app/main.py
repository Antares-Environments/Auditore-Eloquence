import json
import time
from dotenv import load_dotenv

load_dotenv() 

from fasthtml.common import fast_app, serve, Link, Script, Div, Button, Video, Titled, FileResponse
from app.api.websockets import setup_websockets
from app.core.validators import load_templates, ACTIVE_TEMPLATES

load_templates()

CACHE_BUSTER = int(time.time())

app, rt = fast_app(
    pico=False,
    hdrs=(
        Link(rel="stylesheet", href=f"/static/css/style.css?v={CACHE_BUSTER}"),
        Script(src=f"/static/js/media_stream.js?v={CACHE_BUSTER}", defer=True)
    )
)

@rt("/static/{file_path:path}")
def serve_static(file_path: str):
    return FileResponse(f"static/{file_path}")

@rt("/favicon.ico")
def serve_favicon():
    return FileResponse("static/assets/favicon.ico")

setup_websockets(app)

@rt("/")
def get():
    template_data = {
        name: tmpl.template_metadata.description 
        for name, tmpl in ACTIVE_TEMPLATES.items()
    }
    
    return Titled(
        "Auditore Eloquence",
        Div("SYSTEM IDLE", id="status-indicator", cls="white"),
        
        Div(
            Div(
                Div("SELECT TEMPLATE", id="donut-center-text"),
                id="donut-container",
                data_templates=json.dumps(template_data)
            ),
            Div(id="template-details", cls="white", style="display: none; padding: 1rem; margin-bottom: 1rem; width: 100%; max-width: 600px; box-sizing: border-box; text-align: center; border-radius: 4px; font-weight: bold; border: 1px solid var(--indicator-gray);"),
            id="idle-panel",
            style="display: flex; flex-direction: column; align-items: center; width: 100%;"
        ),

        Div(
            Video(id="video-feed", autoplay=True, muted=True),
            Div(id="live-event-log", style="width: 100%; max-width: 600px; height: 150px; overflow-y: auto; margin-top: 1rem; padding: 1rem; background-color: var(--indicator-white); border: 2px solid var(--indicator-gray); border-radius: 4px; font-family: monospace; font-size: 0.85rem; color: var(--element-brown); box-sizing: border-box; text-align: left;"),
            id="active-session-panel",
            style="display: none; flex-direction: column; align-items: center; width: 100%;"
        ),
        
        Div(
            Button("START SESSION", id="session-toggle"),
            cls="button-container"
        )
    )

if __name__ == "__main__":
    serve()