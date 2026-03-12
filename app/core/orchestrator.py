import asyncio
import json
import time
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
        
        self.audio_queue = asyncio.Queue()
        self.live_task = None
        
        self.transcript_buffer = ""
        self.last_council_time = 0.0
        self.COUNCIL_COOLDOWN = 15.0 

    async def start_live_stream(self, emit_event, send_json):
        self.live_task = asyncio.create_task(self._run_live_loop(emit_event, send_json))

    async def _run_live_loop(self, emit_event, send_json):
        try:
            await emit_event("Opening continuous WebSocket to Gemini Multimodal Live API...")
            async with self.live_manager.get_session() as session:
                await emit_event("Live API pipeline established. Streaming audio direct to matrix...")
                
                async def sender():
                    while True:
                        chunk = await self.audio_queue.get()
                        if chunk is None:
                            break
                        await session.send(input={"data": chunk, "mime_type": "audio/webm"})

                async def receiver():
                    buffer = ""
                    async for response in session.receive():
                        if response.server_content and response.server_content.model_turn:
                            for part in response.server_content.model_turn.parts:
                                if part.text:
                                    buffer += part.text
                                    clean_text = buffer.strip()
                                    
                                    if "{" in clean_text and "}" in clean_text:
                                        try:
                                            start = clean_text.find("{")
                                            end = clean_text.rfind("}") + 1
                                            json_str = clean_text[start:end]
                                            parsed = json.loads(json_str)
                                            buffer = "" 
                                            
                                            await emit_event("System 1 live evaluation captured.")
                                            print(f"SYSTEM 1 OUTPUT: {parsed}", flush=True)
                                            await send_json(parsed)
                                        except json.JSONDecodeError as decode_error:
                                            print(f"[JSON STREAM BUFFER] Accumulating chunk payload: {decode_error}", flush=True)
                
                await asyncio.gather(sender(), receiver())
                
        except asyncio.CancelledError as cancel_error:
            print(f"\n[LIVE STREAM] Pipeline task cancelled: {cancel_error}", flush=True)
            raise cancel_error
        except Exception as e:
            print(f"\n!!! [LIVE API ERROR] {e} !!!\n", flush=True)
            await emit_event(f"CRITICAL: Live API connection severed: {e}")
            raise e

    async def process_audio_stream(self, audio_chunk: bytes):
        await self.audio_queue.put(audio_chunk)

    async def process_async_transcript(self, transcript: str, emit_event=None):
        self.transcript_buffer += transcript + " "
        word_count = len(transcript.split())
        self.monitor.update_words(word_count)
        
        if emit_event: 
            await emit_event(f"Calculating pacing telemetry for {word_count} incoming words...")
            
        pacing_state = self.monitor.evaluate_thresholds()
        council_evaluations = None
        
        current_time = time.time()
        
        if current_time - self.last_council_time >= self.COUNCIL_COOLDOWN:
            if emit_event:
                await emit_event("Routing accumulated transcript buffer to Background Council...")
            
            council_evaluations = await self.background_council.evaluate_transcript(self.transcript_buffer)
            
            self.transcript_buffer = "" 
            self.last_council_time = current_time
            
            if emit_event:
                await emit_event("Council consensus achieved. Dispatching intelligence payload to UI.")
                
        return {
            "pacing": pacing_state,
            "council": council_evaluations 
        }

    async def terminate(self):
        await self.audio_queue.put(None)
        if self.live_task:
            self.live_task.cancel()

    def get_thresholds(self) -> Dict:
        return self.thresholds.model_dump()