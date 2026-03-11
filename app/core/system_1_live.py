import json
from google import genai
from google.genai import types
from app.core.validators import ExpectedOutput

class LiveSessionManager:
    def __init__(self, config):
        self.config = config
        self.client = genai.Client()
        self.model = "gemini-2.5-flash"
        self.system_instruction = self._build_instruction()
        self.audio_buffer = bytearray()
        self.chunk_count = 0

    def _build_instruction(self):
        base = f"Role: {self.config.specialist_role}\nObjective: {self.config.primary_objective}\n"
        
        base += "\nDictionary Definitions:\n"
        for item in self.config.rag_dictionary_injected:
            base += f"- {item.rule}: {item.definition} (Trigger: {item.ui_trigger})\n"
            
        base += "\nFew-Shot Calibration (Mandatory Response Format):\n"
        for shot in self.config.few_shot_calibration:
            base += f"User Input: \"{shot.user_input}\"\n"
            base += f"Expected Output: {shot.expected_output.model_dump_json()}\n\n"
            
        return base

    async def evaluate_chunk(self, audio_chunk: bytes):
        self.audio_buffer.extend(audio_chunk)
        self.chunk_count += 1

        if self.chunk_count < 12:
            return None

        payload = bytes(self.audio_buffer)
        self.audio_buffer.clear()
        self.chunk_count = 0

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=[
                    types.Part.from_bytes(data=payload, mime_type="audio/webm")
                ],
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=self.config.model_parameters.temperature,
                    response_mime_type="application/json",
                    response_schema=ExpectedOutput,
                )
            )
            return json.loads(response.text)
        except Exception:
            return {"indicator": "yellow", "interruption": False, "message": "SYSTEM REALIGNING"}