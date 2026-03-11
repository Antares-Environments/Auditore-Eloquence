import json
import asyncio
from app.core.orchestrator import SessionOrchestrator

def setup_websockets(app):
    @app.ws("/stream")
    async def stream_handler(ws):
        # Extract the template name from the connection URL
        template_name = ws.query_params.get("template")
        
        # Fallback security in case a direct connection bypasses the UI
        if not template_name:
            template_name = "Formal Debate" 

        await ws.accept()
        
        # Initialize the engine strictly with the selected architecture
        orchestrator = SessionOrchestrator(template_name)
        
        try:
            while True:
                message = await ws.receive()
                if "bytes" in message:
                    audio_chunk = message["bytes"]
                    result = await orchestrator.process_audio_stream(audio_chunk)
                    if result: # Only send if the orchestrator generated a response
                        await ws.send_json(result)
                elif "text" in message:
                    transcript_chunk = message["text"]
                    result = await orchestrator.process_async_transcript(transcript_chunk)
                    if result:
                        await ws.send_json({"async_results": result})
        except Exception:
            # Silently handle disconnections when the user clicks "Terminate Session"
            pass