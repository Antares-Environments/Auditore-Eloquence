import json
import asyncio
from starlette.websockets import WebSocketDisconnect
from app.core.orchestrator import SessionOrchestrator

async def stream_handler(ws):
    await ws.accept()
    template_name = ws.query_params.get("template", "Formal Debate")
    
    print(f"\n--- SESSION IGNITED: {template_name} ---", flush=True)
    
    async def emit_event(message: str):
        try:
            await ws.send_json({"system_event": message})
        except WebSocketDisconnect:
            pass
        except Exception as e:
            print(f"[EMIT EVENT ERROR] {e}", flush=True)
            
    async def send_json(data: dict):
        try:
            await ws.send_json(data)
        except WebSocketDisconnect:
            pass
        except Exception as e:
            print(f"[SEND JSON ERROR] {e}", flush=True)
            
    async def send_audio(audio_bytes: bytes):
        try:
            await ws.send_bytes(audio_bytes)
        except WebSocketDisconnect:
            pass
        except Exception as e:
            print(f"[SEND AUDIO ERROR] {e}", flush=True)

    await emit_event(f"Mounting orchestrator for {template_name}...")
    
    try:
        orchestrator = SessionOrchestrator(template_name)
        await emit_event("System 1 (Live Audio) and System 2 (Council) initialized.")
        await orchestrator.start_live_stream(emit_event, send_json, send_audio)
    except Exception as e:
        print(f"FAILED TO LOAD ORCHESTRATOR: {e}", flush=True)
        await emit_event(f"CRITICAL ERROR: Failed to load orchestrator template. {e}")
        await ws.close()
        return

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
            print(f"[TEXT TASK ERROR] {e}", flush=True)
            
    try:
        while True:
            message = await ws.receive()
            
            if message.get("type") == "websocket.disconnect":
                print("\n--- SESSION CLOSED BY CLIENT ---", flush=True)
                break
                
            if "bytes" in message:
                await orchestrator.process_audio_stream(message["bytes"])
                    
            elif "text" in message:
                try:
                    parsed_payload = json.loads(message["text"])
                    if "video_frame" in parsed_payload:
                        await orchestrator.process_video_frame(parsed_payload["video_frame"])
                    elif "client_event" in parsed_payload and parsed_payload["client_event"] == "barge_in":
                        print("\n[BARGE-IN] User interrupted the agent.", flush=True)
                        # The Gemini Live API handles audio interruption natively.
                        # We acknowledge the frontend signal and log it for diagnostics.
                    else:
                        asyncio.create_task(process_text_task(message["text"]))
                except json.JSONDecodeError:
                    # Fallback to assumed standard script handling if parsing fails
                    asyncio.create_task(process_text_task(message["text"]))
                    
    except WebSocketDisconnect:
        print("\n--- SESSION CLOSED BY CLIENT ---", flush=True)
    except RuntimeError as re:
        if "Cannot call 'receive' once a disconnect message has been received" in str(re) or "Unexpected ASGI message" in str(re):
             print("\n--- SOCKET TERMINATED ABRUPTLY ---", flush=True)
        else:
             print(f"\n!!! BACKEND RUNTIME FAULT DETECTED: {re} !!!\n", flush=True)
             raise re
    except Exception as e:
        print(f"\n!!! BACKEND FAULT DETECTED: {e} !!!\n", flush=True)
        try:
            await emit_event(f"Warning: System realignment required due to engine fault. {e}")
        except:
            pass # Socket already dead
        raise e
    finally:
        await orchestrator.terminate()

def setup_websockets(app):
    print("\n>>> MOUNTING WEBSOCKET ENGINE <<<", flush=True)
    app.add_websocket_route("/stream", stream_handler)
    print(">>> ENGINE MOUNTED SUCCESSFULLY <<<\n", flush=True)