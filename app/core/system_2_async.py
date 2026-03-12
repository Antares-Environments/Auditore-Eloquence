import json
import asyncio
from google import genai
from google.genai import types
from app.core.validators import ExpectedOutput

class BackgroundCouncil:
    def __init__(self, council_config):
        self.council_config = council_config
        self.client = genai.Client()
        self.model = "gemini-2.5-flash"

    def _build_instruction(self, member):
        base = f"Role: {member.specialist_role}\nObjective: {member.primary_objective}\n"
        base += "Dictionary:\n"
        for item in member.rag_dictionary_injected:
            base += f"- {item.rule}: {item.definition} (Trigger: {item.ui_trigger})\n"
        return base

    async def evaluate_transcript(self, transcript: str):
        results = []
        for member in self.council_config:
            instruction = self._build_instruction(member)
            result = await self._call_model(instruction, transcript)
            results.append(result)
            await asyncio.sleep(1)
        return results

    async def _call_model(self, instruction: str, transcript: str):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model,
                    contents=transcript,
                    config=types.GenerateContentConfig(
                        system_instruction=instruction,
                        temperature=0.2,
                        response_mime_type="application/json",
                        response_schema=ExpectedOutput,
                    )
                )
                return json.loads(response.text)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                await asyncio.sleep(2 ** attempt)