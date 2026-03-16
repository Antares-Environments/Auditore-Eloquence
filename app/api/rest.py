# app/api/rest.py
from app.core.validators import ACTIVE_TEMPLATES

def setup_rest(app):
    @app.get("/api/templates")
    def list_templates():
        return list(ACTIVE_TEMPLATES.keys())

    @app.get("/api/templates/{name}")
    def get_template(name: str):
        template = ACTIVE_TEMPLATES.get(name)
        if template:
            return template.model_dump()
        return {"error": "not found"}