import json
import asyncio
from app.core.orchestrator import SessionOrchestrator

def setup_websockets(app):
    @app.ws("/stream")
    async def stream_handler(ws):
        template_name = ws.query_params.get("template")
        
        if not template_name:
            template_name = "Formal Debate" 

        await ws.accept()
        print(f"\n--- SESSION IGNITED: {template_name} ---")
        
        try:
            orchestrator = SessionOrchestrator(template_name)
        except Exception as e:
            print(f"FAILED TO LOAD ORCHESTRATOR: {e}")
            return
            
        try:
            while True:
                message = await ws.receive()
                
                if "bytes" in message:
                    audio_chunk = message["bytes"]
                    # Silently accumulates until the 12th chunk, then processes
                    result = await orchestrator.process_audio_stream(audio_chunk)
                    if result:
                        print(f"SYSTEM 1 OUTPUT: {result}")
                        await ws.send_json(result)
                        
                elif "text" in message:
                    transcript_chunk = message["text"]
                    print(f"TRANSCRIPT RECEIVED: '{transcript_chunk}'")
                    
                    result = await orchestrator.process_async_transcript(transcript_chunk)
                    if result:
                        print(f"SYSTEM 2 & PACING OUTPUT: {result}")
                        await ws.send_json({"async_results": result})
                        
        except Exception as e:
            # THIS IS WHERE THE SILENT CRASH WAS HIDING
            print(f"\n!!! BACKEND CRASH DETECTED: {e} !!!\n")