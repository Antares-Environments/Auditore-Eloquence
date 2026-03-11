import json
from fasthtml.common import fast_app, serve, Link, Script, Div, Button, Video, Titled, FileResponse
from app.api.websockets import setup_websockets
from app.core.validators import load_templates, ACTIVE_TEMPLATES

load_templates()

app, rt = fast_app(
    pico=False,
    hdrs=(
        Link(rel="stylesheet", href="/static/css/style.css?v=5"),
        Script(src="/static/js/media_stream.js?v=5", defer=True)
    )
)

@rt("/static/{file_path:path}")
def serve_static(file_path: str):
    return FileResponse(f"static/{file_path}")

setup_websockets(app)

@rt("/")
def get():
    # Extract template names and their descriptions to serve as the "content"
    template_data = {
        name: tmpl.template_metadata.description 
        for name, tmpl in ACTIVE_TEMPLATES.items()
    }
    
    return Titled(
        "Auditore Eloquence",
        Div("SYSTEM IDLE", id="status-indicator", cls="white"),
        
        # The SVG Anchor now carries the full JSON payload
        Div(
            Div("SELECT TEMPLATE", id="donut-center-text"),
            id="donut-container",
            data_templates=json.dumps(template_data)
        ),
        
        # The hidden content block that mirrors your portfolio logic
        Div(id="template-details", cls="white", style="display: none; padding: 1rem; margin-bottom: 1rem; width: 100%; max-width: 600px; box-sizing: border-box; text-align: center; border-radius: 4px; font-weight: bold; border: 1px solid var(--indicator-gray);"),
        
        Div(
            Button("Start Session", id="start-session"),
            Button("Terminate Session", id="end-session"),
            cls="button-container"
        ),
        Video(id="video-feed", autoplay=True, muted=True)
    )

if __name__ == "__main__":
    serve()