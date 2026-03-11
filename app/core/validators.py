import json
from pathlib import Path
from pydantic import BaseModel
from typing import List, Dict, Optional

class TemplateMetadata(BaseModel):
    name: str
    version: str
    author: str
    description: str

class ModelParameters(BaseModel):
    temperature: float
    interruption_priority: str

class ExpectedOutput(BaseModel):
    flaw: Optional[str] = None
    status: Optional[str] = None
    indicator: str
    interruption: bool
    message: str

class FewShotCalibration(BaseModel):
    user_input: str
    expected_output: ExpectedOutput

class RagDictionaryItem(BaseModel):
    rule: str
    definition: str
    ui_trigger: str

class System1LiveSocket(BaseModel):
    specialist_role: str
    primary_objective: str
    model_parameters: ModelParameters
    few_shot_calibration: List[FewShotCalibration]
    rag_dictionary_injected: List[RagDictionaryItem]

class System2AsyncCouncilItem(BaseModel):
    specialist_role: str
    primary_objective: str
    rag_dictionary_injected: List[RagDictionaryItem]

class PythonOrchestratorThresholds(BaseModel):
    track_wpm: bool
    wpm_upper_limit: int
    wpm_lower_limit: int
    wpm_violation_trigger: str
    enforce_time_limit_seconds: int

class AuditoreTemplate(BaseModel):
    template_metadata: TemplateMetadata
    system_1_live_socket: System1LiveSocket
    system_2_async_council: List[System2AsyncCouncilItem]
    python_orchestrator_thresholds: PythonOrchestratorThresholds

ACTIVE_TEMPLATES: Dict[str, AuditoreTemplate] = {}

def load_templates():
    template_dir = Path("app/templates")
    if not template_dir.exists():
        return
    
    for file_path in template_dir.glob("*.json"):
        if file_path.name == "schema.json":
            continue
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            validated_template = AuditoreTemplate(**raw_data)
            ACTIVE_TEMPLATES[validated_template.template_metadata.name] = validated_template
        except Exception as e:
            # DIAGNOSTIC EXPOSURE
            print(f"\n[VALIDATOR ERROR] Failed to load template '{file_path.name}': {e}\n")