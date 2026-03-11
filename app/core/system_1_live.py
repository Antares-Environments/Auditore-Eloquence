import os
import json
from google import genai
from google.genai import types

class LiveSessionManager:
    def __init__(self, config):
        self.config = config
        self.client = genai.Client()
        self.model = "gemini-2.5-flash-native-audio-latest"
        self.system_instruction = self._build_instruction()

    def _build_instruction(self):
        base = f"Role: {self.config.specialist_role}\nObjective: {self.config.primary_objective}\n"
        base += "Dictionary:\n"
        for item in self.config.rag_dictionary_injected:
            base += f"- {item.rule}: {item.definition} (Trigger: {item.ui_trigger})\n"
        return base

    async def evaluate_chunk(self, audio_chunk: bytes):
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=[
                    types.Part.from_bytes(data=audio_chunk, mime_type="audio/wav")
                ],
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=self.config.model_parameters.temperature,
                    response_mime_type="application/json"
                )
            )
            return json.loads(response.text)
        except Exception:
            return {"indicator": "green", "message": "error"}