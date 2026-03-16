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
        Link(rel="icon", href=f"/static/assets/favicon.ico?v={CACHE_BUSTER}")
        Link(rel="stylesheet", href=f"/static/css/style.css?v={CACHE_BUSTER}"),
        Script(src=f"/static/js/media_stream.js?v={CACHE_BUSTER}", type="module", defer=True)
    )
)

@rt("/static/{file_path:path}")
def serve_static(file_path: str):
    return FileResponse(f"static/{file_path}")

@rt("/favicon.ico")
def serve_favicon():
    return FileResponse("static/assets/favicon.ico")

setup_websockets(app)

import math

def get_svg_path(start_angle, end_angle, cx=150, cy=150, r_in=70, r_out=130):
    start_rad = math.radians(start_angle - 90)
    end_rad = math.radians(end_angle - 90)
    x1_out = cx + r_out * math.cos(start_rad)
    y1_out = cy + r_out * math.sin(start_rad)
    x2_out = cx + r_out * math.cos(end_rad)
    y2_out = cy + r_out * math.sin(end_rad)
    x1_in = cx + r_in * math.cos(end_rad)
    y1_in = cy + r_in * math.sin(end_rad)
    x2_in = cx + r_in * math.cos(start_rad)
    y2_in = cy + r_in * math.sin(start_rad)
    large_arc = 1 if (end_angle - start_angle) > 180 else 0
    return f"M {x1_out} {y1_out} A {r_out} {r_out} 0 {large_arc} 1 {x2_out} {y2_out} L {x1_in} {y1_in} A {r_in} {r_in} 0 {large_arc} 0 {x2_in} {y2_in} Z"

def generate_svg_segments(categories):
    num_slices = len(categories)
    segments = []
    if num_slices > 0:
        angle_per_slice = 360 / num_slices
        for i, category in enumerate(categories):
            start_angle = i * angle_per_slice
            end_angle = (i + 1) * angle_per_slice
            
            # Subtly separate segments using a 2-degree visual gap
            path_d = get_svg_path(start_angle + 1, end_angle - 1)
            segments.append({
                'id': f"template-{i + 1}",
                'label': category,
                'path': path_d
            })
    return segments

@rt("/")
def get():
    template_data = {
        name: {
            "description": tmpl.template_metadata.description,
            "requires_video_audit": tmpl.python_orchestrator_thresholds.requires_video_audit
        }
        for name, tmpl in ACTIVE_TEMPLATES.items()
    }
    
    # Generate SVG paths backend-side
    categories = list(ACTIVE_TEMPLATES.keys())
    segments = generate_svg_segments(categories)
    
    from fasthtml.common import NotStr
    
    # Assemble the SVG string manually since FastHTML SVGs can be convoluted for purely geometric paths
    svg_content = '<svg id="donut-svg" width="300" height="300" viewBox="0 0 300 300">'
    for segment in segments:
        label = segment['label']
        sid = segment['id']
        path = segment['path']
        # The javascript port will need hoverRingItem(id, label), resetRingItem(id), and clickRingItem(id, label)
        svg_content += f"""
        <path id="slice-{sid}" d="{path}" fill="#3f2a03" class="donut-slice"
            style="cursor: pointer; transition: fill 0.3s ease, transform 0.3s ease; transform-origin: 150px 150px;"
            onmouseover="hoverRingItem('{sid}', '{label}')"
            onmouseout="resetRingItem('{sid}')"
            onclick="clickRingItem('{sid}', '{label}')">
            <title>{label}</title>
        </path>
        """
    svg_content += '</svg>'

    return Titled(
        "Auditore Eloquence",
        Script(f"window.TEMPLATE_DATA = {json.dumps(template_data)};"),
        Div("SYSTEM IDLE", id="status-indicator", cls="white"),
        
        Div(
            Div(
                Div("SELECT TEMPLATE", id="donut-center-text"),
                NotStr(svg_content),
                id="donut-container"
            ),
            Div(id="template-details", cls="white", style="display: none; padding: 1rem; margin-bottom: 1rem; width: 100%; max-width: 600px; box-sizing: border-box; text-align: center; border-radius: 4px; font-weight: bold; border: 1px solid var(--indicator-gray);"),
            id="idle-panel",
            style="display: flex; flex-direction: column; align-items: center; width: 100%;"
        ),

        Div(
            Video(id="video-feed", autoplay=True, muted=True),
            id="active-session-panel",
            style="display: none; flex-direction: column; align-items: center; width: 100%;"
        ),
        
        Div(id="live-event-log", style="width: 100%; max-width: 600px; height: 150px; overflow-y: auto; margin-top: 1rem; padding: 1rem; background-color: var(--indicator-white); border: 2px solid var(--indicator-gray); border-radius: 4px; font-family: monospace; font-size: 0.85rem; color: var(--element-brown); box-sizing: border-box; text-align: left;"),
        
        Div(
            Button("START SESSION", id="session-toggle"),
            cls="button-container"
        )
    )

if __name__ == "__main__":
    serve()