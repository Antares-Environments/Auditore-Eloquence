from fasthtml.common import fast_app, serve, Link, Script, Div, Button, Video, Titled, FileResponse
from app.api.websockets import setup_websockets
from app.core.validators import load_templates

load_templates()

app, rt = fast_app(
    pico=False
    hdrs=(
        Link(rel="stylesheet", href="/static/css/style.css"),
        Script(src="/static/js/media_stream.js", defer=True)
    )
)

# THE BRIDGE: Explicitly expose the static folder to the browser
@rt("/static/{file_path:path}")
def serve_static(file_path: str):
    return FileResponse(f"static/{file_path}")

setup_websockets(app)

@rt("/")
def get():
    return Titled(
        "Auditore Eloquence",
        Div(id="status-indicator", cls="white"),
        Button("Start Session", id="start-session"),
        Video(id="video-feed", autoplay=True, muted=True)
    )

if __name__ == "__main__":
    serve()