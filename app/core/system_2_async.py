import json
import asyncio
from google import genai
from google.genai import types

class BackgroundCouncil:
    def __init__(self, council_config):
        self.council_config = council_config
        self.client = genai.Client()
        self.model = "gemini-2.5-flash-native-audio-latest"

    def _build_instruction(self, member):
        base = f"Role: {member.specialist_role}\nObjective: {member.primary_objective}\n"
        base += "Dictionary:\n"
        for item in member.rag_dictionary_injected:
            base += f"- {item.rule}: {item.definition} (Trigger: {item.ui_trigger})\n"
        return base

    async def evaluate_transcript(self, transcript: str):
        results = []
        tasks = []
        
        for member in self.council_config:
            instruction = self._build_instruction(member)
            tasks.append(self._call_model(instruction, transcript))
            
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in completed_tasks:
            if isinstance(result, Exception):
                results.append({"indicator": "green", "message": "error"})
            else:
                results.append(result)
                
        return results

    async def _call_model(self, instruction: str, transcript: str):
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=transcript,
            config=types.GenerateContentConfig(
                system_instruction=instruction,
                temperature=0.2,
                response_mime_type="application/json"
            )
        )
        return json.loads(response.text)