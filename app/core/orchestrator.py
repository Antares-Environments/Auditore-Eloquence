# app/core/orchestrator.py
import asyncio
import time
from typing import Optional, Dict, Any
from google.genai import types
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
        
        self.media_queue: asyncio.Queue[Optional[Any]] = asyncio.Queue()
        self.transcript_queue: asyncio.Queue[Optional[str]] = asyncio.Queue()
        self.live_task: Optional[asyncio.Task] = None
        
        self.transcript_buffer = ""
        self.last_council_time = 0.0
        self.COUNCIL_COOLDOWN = 15.0 
        self.visual_buffer = []

    async def start_live_stream(self, emit_event, send_json, send_audio):
        self.live_task = asyncio.create_task(self._run_live_loop(emit_event, send_json, send_audio))

    async def _run_live_loop(self, emit_event, send_json, send_audio):
        try:
            await emit_event("Opening continuous WebSocket to Gemini Multimodal Live API...")
            async with self.live_manager.get_session() as session:
                await emit_event("Live API pipeline established. Streaming audio direct to matrix...")
                
                async def sender():
                    while True:
                        try:
                            # 1.5 second aggressive heartbeat to prevent API timeout
                            item = await asyncio.wait_for(self.media_queue.get(), timeout=1.5)
                        except asyncio.TimeoutError:
                            try:
                                await session.send_realtime_input(audio=types.Blob(data=b'\x00'*256, mime_type="audio/pcm;rate=16000"))
                            except:
                                pass
                            continue

                        if item is None:
                            break
                        
                        media_type, blob_data, mime = item
                        try:
                            blob = types.Blob(data=blob_data, mime_type=mime)
                            if media_type == "audio":
                                await session.send_realtime_input(audio=blob)
                            elif media_type == "video":
                                await session.send_realtime_input(video=blob)
                        except Exception as e:
                            print(f"[SENDER ERROR] Failed to send {media_type} chunk: {e}", flush=True)
                            raise e

                async def receiver():
                    try:
                        async for response in session.receive():
                            # Primary path for audio
                            if response.data:
                                await send_audio(response.data)

                            if response.server_content and response.server_content.model_turn:
                                for part in response.server_content.model_turn.parts:
                                    if hasattr(part, 'inline_data') and part.inline_data:
                                        await send_audio(part.inline_data.data)
                                    
                                    if hasattr(part, 'thought') and part.thought:
                                        print(f"[DIAGNOSTIC] Model Thinking detected: {part.thought[:100]}...", flush=True)
                                    if hasattr(part, 'executable_code') and part.executable_code:
                                        print(f"[DIAGNOSTIC] Model Code Block detected!", flush=True)

                                    if part.text:
                                        raw = part.text.strip()
                                        if not raw:
                                            continue
                                        
                                        try:
                                            import json as _json
                                            payload = _json.loads(raw)
                                            if "indicator" in payload:
                                                await emit_event(f"System 1 evaluation: {payload.get('message', '')}")
                                                await send_json(payload)
                                                continue
                                        except (_json.JSONDecodeError, ValueError):
                                            pass
                                        
                                        await self.transcript_queue.put(raw)

                            if response.server_content and response.server_content.input_transcription:
                                clean_text = response.server_content.input_transcription.text.strip()
                                if clean_text:
                                    print(f"USER TRANSCRIPT: {clean_text}", flush=True)
                                    await self.transcript_queue.put(clean_text)
                    except Exception as e:
                        print(f"[RECEIVER ERROR] {e}", flush=True)
                        raise e

                async def analytics_processor():
                    while True:
                        text = await self.transcript_queue.get()
                        if text is None:
                            break
                        try:
                            result = await self.process_async_transcript(text, emit_event)
                            await send_json({"async_results": result})
                        except Exception as e:
                            print(f"[ANALYTICS ERROR] {e}", flush=True)
                
                # Supervisor Pattern implementation
                tasks = [
                    asyncio.create_task(sender()),
                    asyncio.create_task(receiver()),
                    asyncio.create_task(analytics_processor())
                ]
                
                done, pending = await asyncio.wait(
                    tasks,
                    return_when=asyncio.FIRST_EXCEPTION
                )
                
                # Cleanup: cancel remaining tasks if one fails
                for task in pending:
                    task.cancel()
                
                # Propagate exception to trigger UI alert
                for task in done:
                    if task.exception():
                        raise task.exception()
                
        except asyncio.CancelledError:
            print(f"\n[LIVE STREAM] Pipeline task cancelled.", flush=True)
            raise
        except Exception as e:
            print(f"\n!!! [LIVE API ERROR] {e} !!!\n", flush=True)
            await emit_event(f"CRITICAL: Live API connection severed: {e}")
            raise e

    async def process_audio_stream(self, audio_chunk: bytes):
        await self.media_queue.put(("audio", audio_chunk, "audio/pcm;rate=16000"))

    async def process_video_frame(self, base64_image: str):
        requires_video = self.thresholds.requires_video_audit
        requires_screen = getattr(self.thresholds, "requires_screen_audit", False)
        
        if not (requires_video or requires_screen):
            return
            
        if "," in base64_image:
            base64_image = base64_image.split(",")[1]
            
        import base64
        try:
            image_bytes = base64.b64decode(base64_image)
            
            await self.media_queue.put(("video", image_bytes, "image/jpeg"))
            
            if len(self.visual_buffer) >= 3:
                self.visual_buffer.pop(0)
            self.visual_buffer.append(types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"))
            
        except Exception as e:
            print(f"[VISION SYSTEM ERROR] Failed to decode camera metric payload: {e}")

    async def process_async_transcript(self, transcript: str, emit_event=None):
        self.transcript_buffer += transcript + " "
        total_word_count = len(self.transcript_buffer.split())
        self.monitor.update_words(total_word_count)
        
        if emit_event: 
            await emit_event(f"Calculating pacing telemetry for {total_word_count} ongoing words...")
            
        pacing_state = self.monitor.evaluate_thresholds()
        council_evaluations = None
        
        current_time = time.time()
        
        if current_time - self.last_council_time >= self.COUNCIL_COOLDOWN:
            if emit_event:
                await emit_event("Routing accumulated transcript buffer and visual context to Background Council...")
            
            try:
                with open("session_transcript.txt", "a", encoding="utf-8") as f:
                    f.write(f"[{time.strftime('%H:%M:%S')}] {self.transcript_buffer}\n")
            except:
                pass
            
            current_visual_context = list(self.visual_buffer)
            self.visual_buffer.clear()
            
            council_evaluations = await self.background_council.evaluate_transcript(
                self.transcript_buffer, 
                visual_context=current_visual_context
            )
            
            self.transcript_buffer = "" 
            self.last_council_time = current_time
            
            if emit_event:
                await emit_event("Council consensus achieved. Dispatching intelligence payload to UI.")
                
        return {
            "pacing": pacing_state,
            "council": council_evaluations 
        }

    async def terminate(self):
        await self.media_queue.put(None)
        if self.live_task:
            self.live_task.cancel()

    def get_thresholds(self) -> Dict:
        return self.thresholds.model_dump()