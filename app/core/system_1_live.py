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
        
        base += "\nDictionary Definitions:\n"
        for item in self.config.rag_dictionary_injected:
            base += f"- {item.rule}: {item.definition} (Trigger: {item.ui_trigger})\n"
            
        base += "\nFew-Shot Calibration (Mandatory Response Format):\n"
        for shot in self.config.few_shot_calibration:
            base += f"User Input: \"{shot.user_input}\"\n"
            base += f"Expected Output: {shot.expected_output.model_dump_json()}\n\n"
            
        base += "\nCRITICAL INSTRUCTION: You are listening to a live audio stream. You must constantly evaluate the speaker's tone, pacing, and delivery.\n"
        base += "You must map your findings to the following priority logic:\n"
        base += "RED: High Priority correction. You MUST verbally speak the correction to the user AND output the JSON payload.\n"
        base += "ORANGE: Low Priority correction. You MUST REMAIN COMPLETELY SILENT and output ONLY the JSON payload for the visual panel.\n"
        base += "GREEN: Good for now. You MUST REMAIN COMPLETELY SILENT and output ONLY the JSON payload for the visual panel.\n"
        base += "Never use markdown tags in the text output.\n"
            
        return base

    def get_session(self):
        config = types.LiveConnectConfig(
            system_instruction=types.Content(parts=[types.Part.from_text(text=self.system_instruction)]),
            temperature=self.config.model_parameters.temperature,
            response_modalities=["AUDIO"]
        )
        return self.client.aio.live.connect(model=self.model, config=config)