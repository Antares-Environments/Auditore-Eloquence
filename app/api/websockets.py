import json
import asyncio
from starlette.websockets import WebSocketDisconnect
from app.core.orchestrator import SessionOrchestrator

def setup_websockets(app):
    async def stream_handler(ws):
        await ws.accept()
        template_name = ws.query_params.get("template", "Formal Debate")
        
        # flush=True forces the terminal to print immediately without buffering
        print(f"\n--- SESSION IGNITED: {template_name} ---", flush=True)
        
        try:
            orchestrator = SessionOrchestrator(template_name)
        except Exception as e:
            print(f"FAILED TO LOAD ORCHESTRATOR: {e}", flush=True)
            await ws.close()
            return
            
        try:
            while True:
                message = await ws.receive()
                
                # Bare-metal interception of raw audio bytes
                if "bytes" in message:
                    audio_chunk = message["bytes"]
                    result = await orchestrator.process_audio_stream(audio_chunk)
                    if result:
                        print(f"SYSTEM 1 OUTPUT: {result}", flush=True)
                        await ws.send_json(result)
                        
                # Bare-metal interception of native JS speech transcripts
                elif "text" in message:
                    transcript_chunk = message["text"]
                    print(f"TRANSCRIPT RECEIVED: '{transcript_chunk}'", flush=True)
                    
                    result = await orchestrator.process_async_transcript(transcript_chunk)
                    if result:
                        print(f"SYSTEM 2 & PACING OUTPUT: {result}", flush=True)
                        await ws.send_json({"async_results": result})
                        
        except WebSocketDisconnect:
            print(f"\n--- SESSION CLOSED BY CLIENT ---", flush=True)
        except Exception as e:
            print(f"\n!!! BACKEND CRASH DETECTED: {e} !!!\n", flush=True)

    # The Green Plot: Bind the handler natively, bypassing FastHTML's text-only wrapper
    app.add_websocket_route("/stream", stream_handler)