import json
import asyncio
from app.core.orchestrator import SessionOrchestrator

def setup_websockets(app):
    @app.ws("/stream")
    async def stream_handler(ws):
        await ws.accept()
        orchestrator = SessionOrchestrator("Formal Debate")
        
        try:
            while True:
                message = await ws.receive()
                if "bytes" in message:
                    audio_chunk = message["bytes"]
                    result = await orchestrator.process_audio_stream(audio_chunk)
                    await ws.send_json(result)
                elif "text" in message:
                    transcript_chunk = message["text"]
                    result = await orchestrator.process_async_transcript(transcript_chunk)
                    await ws.send_json({"async_results": result})
        except Exception:
            pass