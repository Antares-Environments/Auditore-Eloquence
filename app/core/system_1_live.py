# app/core/system_1_live.py
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
            
        base += "\nCRITICAL INSTRUCTION: You are listening to a live audio stream. Constantly evaluate the speaker's tone, pacing, and delivery.\n"
        base += "FAST RESPONSE MODE: Your ONLY action is to speak a calm, authoritative verbal correction the INSTANT you detect a RED (high priority) flaw.\n"
        base += "STRICT RULES:\n"
        base += "1. NEVER monologue. Keep corrections under 5 seconds.\n"
        base += "2. NEVER output 'thought' blocks or internal reasoning. Respond immediately with audio.\n"
        base += "3. For GREEN, YELLOW, or ORANGE observations: REMAIN COMPLETELY SILENT. Do not speak. Do not respond.\n"
        base += "4. Only speak when you MUST correct a RED priority violation.\n"
        base += "5. TRANSCRIPTION RULE: The speaker is speaking ENGLISH. Always transcribe audio input into English text.\n"
            
        return base

    def get_session(self):
        config = types.LiveConnectConfig(
            system_instruction=types.Content(parts=[types.Part.from_text(text=self.system_instruction)]),
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                language_code="en-US",
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Charon"
                    )
                )
            ),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            thinking_config=types.ThinkingConfig(thinking_budget=0)
        )
        return self.client.aio.live.connect(model=self.model, config=config)