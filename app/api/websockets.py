import json
import asyncio
from starlette.websockets import WebSocketDisconnect
from app.core.orchestrator import SessionOrchestrator

def setup_websockets(app):
    async def stream_handler(ws):
        await ws.accept()
        template_name = ws.query_params.get("template", "Formal Debate")
        
        print(f"\n--- SESSION IGNITED: {template_name} ---", flush=True)
        
        async def emit_event(message: str):
            try:
                await ws.send_json({"system_event": message})
            except Exception:
                pass
        
        await emit_event(f"Mounting orchestrator for {template_name}...")
        
        try:
            orchestrator = SessionOrchestrator(template_name)
            await emit_event("System 1 (Live Audio) and System 2 (Council) initialized. Awaiting stream...")
        except Exception as e:
            print(f"FAILED TO LOAD ORCHESTRATOR: {e}", flush=True)
            await emit_event("CRITICAL ERROR: Failed to load orchestrator template.")
            await ws.close()
            return

        # Background Task: Audio Processing
        async def process_audio_task(chunk):
            try:
                result = await orchestrator.process_audio_stream(chunk)
                if result:
                    await emit_event("System 1 audio evaluation complete. Updating visual matrix.")
                    print(f"SYSTEM 1 OUTPUT: {result}", flush=True)
                    await ws.send_json(result)
            except Exception as e:
                print(f"[AUDIO TASK ERROR] {e}")

        async def process_text_task(raw_text_payload):
            try:
                parsed_data = json.loads(raw_text_payload)
                transcript = parsed_data.get("text", "")
                
                print(f"TRANSCRIPT RECEIVED: '{transcript}'", flush=True)
                
                result = await orchestrator.process_async_transcript(transcript, emit_event)
                if result:
                    print(f"SYSTEM 2 & PACING OUTPUT: {result}", flush=True)
                    await ws.send_json({"async_results": result})
            except Exception as e:
                print(f"[TEXT TASK ERROR] {e}")
                
        try:
            while True:
                message = await ws.receive()
                
                if message.get("type") == "websocket.disconnect":
                    print("\n--- SESSION CLOSED BY CLIENT ---", flush=True)
                    break
                    
                if "bytes" in message:
                    # Fire and forget: immediately frees the socket loop
                    asyncio.create_task(process_audio_task(message["bytes"]))
                        
                elif "text" in message:
                    # Fire and forget: immediately frees the socket loop
                    asyncio.create_task(process_text_task(message["text"]))
                        
        except WebSocketDisconnect:
            print("\n--- SESSION CLOSED BY CLIENT ---", flush=True)
        except Exception as e:
            print(f"\n!!! BACKEND CRASH DETECTED: {e} !!!\n", flush=True)
            await emit_event("Warning: System realignment required due to engine fault.")
    app.add_websocket_route("/stream", stream_handler)