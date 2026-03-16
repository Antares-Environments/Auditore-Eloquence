import json
import asyncio
from google import genai
from google.genai import types
from app.core.validators import ExpectedOutput

class BackgroundCouncil:
    def __init__(self, council_config):
        self.council_config = council_config
        self.client = genai.Client()
        self.model = "gemini-3.1-flash-lite-preview"

    def _build_instruction(self, member):
        base = f"Role: {member.specialist_role}\nObjective: {member.primary_objective}\n"
        base += "Dictionary:\n"
        for item in member.rag_dictionary_injected:
            base += f"- {item.rule}: {item.definition} (Trigger: {item.ui_trigger})\n"
        return base

    async def evaluate_transcript(self, transcript: str):
        tasks = []
        # Free tier is ~15 RPM for 2.5 Flash. We use a short delay between fires if the council is large.
        delay = 0.0
        for member in self.council_config:
            instruction = self._build_instruction(member)
            tasks.append(self._delayed_call(instruction, transcript, delay))
            delay += 1.5
            
        # Execute all council members concurrently without crashing the orchestrator if one fails
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions to prevent downstream json parsing failures
        valid_results = [r for r in results if not isinstance(r, Exception)]
        return valid_results

    async def _delayed_call(self, instruction: str, transcript: str, delay: float):
        if delay > 0:
            await asyncio.sleep(delay)
        return await self._call_model(instruction, transcript)

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
                # 429 logic or other network faults
                print(f"[COUNCIL RETRY] Attempt {attempt+1}/{max_retries} failed for role '{instruction.split('Role: ')[1].split(chr(10))[0]}': {e}", flush=True)
                if attempt == max_retries - 1:
                    print(f"[COUNCIL FAILURE] Member evaluation failed after {max_retries} attempts.", flush=True)
                    raise e
                await asyncio.sleep(2 ** attempt + 1) # Exponential with jitter bases