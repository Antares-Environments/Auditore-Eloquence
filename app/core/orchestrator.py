import asyncio
from typing import Optional, Dict
from app.core.validators import ACTIVE_TEMPLATES, AuditoreTemplate
from app.core.system_1_live import LiveSessionManager
from app.core.system_2_async import BackgroundCouncil

class SessionOrchestrator:
    def __init__(self, template_name: str):
        self.template: Optional[AuditoreTemplate] = ACTIVE_TEMPLATES.get(template_name)
        if not self.template:
            raise ValueError()
        
        self.live_socket_config = self.template.system_1_live_socket
        self.async_council_config = self.template.system_2_async_council
        self.thresholds = self.template.python_orchestrator_thresholds
        
        self.live_manager = LiveSessionManager(self.live_socket_config)
        self.background_council = BackgroundCouncil(self.async_council_config)

    async def process_audio_stream(self, audio_chunk: bytes):
        return await self.live_manager.evaluate_chunk(audio_chunk)

    async def process_async_transcript(self, transcript: str):
        return await self.background_council.evaluate_transcript(transcript)

    def get_thresholds(self) -> Dict:
        return self.thresholds.model_dump()