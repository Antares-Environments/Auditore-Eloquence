import asyncio
from typing import Optional, Dict
from app.core.validators import ACTIVE_TEMPLATES, AuditoreTemplate
from app.core.system_1_live import LiveSessionManager
from app.core.system_2_async import BackgroundCouncil
from app.core.threshold_math import ThresholdMonitor

class SessionOrchestrator:
    def __init__(self, template_name: str):
        self.template: Optional[AuditoreTemplate] = ACTIVE_TEMPLATES.get(template_name)
        if not self.template:
            raise ValueError(f"Template '{template_name}' not found.")
        
        self.live_socket_config = self.template.system_1_live_socket
        self.async_council_config = self.template.system_2_async_council
        self.thresholds = self.template.python_orchestrator_thresholds
        
        self.live_manager = LiveSessionManager(self.live_socket_config)
        self.background_council = BackgroundCouncil(self.async_council_config)
        
        self.monitor = ThresholdMonitor(self.thresholds.model_dump())

    async def process_audio_stream(self, audio_chunk: bytes):
        return await self.live_manager.evaluate_chunk(audio_chunk)

    # Inject the optional emitter parameter
    async def process_async_transcript(self, transcript: str, emit_event=None):
        word_count = len(transcript.split())
        self.monitor.update_words(word_count)
        
        if emit_event: 
            await emit_event(f"Calculating pacing telemetry for {word_count} incoming words...")
            
        pacing_state = self.monitor.evaluate_thresholds()
        
        if emit_event:
            await emit_event("Routing transcript to Background Council for async evaluation...")
            
        council_evaluations = await self.background_council.evaluate_transcript(transcript)
        
        if emit_event:
            await emit_event("Council consensus achieved. Dispatching intelligence payload to UI.")
            
        return {
            "pacing": pacing_state,
            "council": council_evaluations
        }

    def get_thresholds(self) -> Dict:
        return self.thresholds.model_dump()