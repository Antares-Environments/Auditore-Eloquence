import time
from typing import Dict, Any

class ThresholdMonitor:
    def __init__(self, thresholds: Dict[str, Any]):
        self.thresholds = thresholds
        self.start_time = time.time()
        self.word_count = 0

    def update_words(self, new_words: int):
        self.word_count += new_words

    def calculate_wpm(self) -> float:
        elapsed_minutes = (time.time() - self.start_time) / 60.0
        if elapsed_minutes <= 0.01:
            return 0.0
        return self.word_count / elapsed_minutes

    def evaluate_thresholds(self) -> Dict[str, str]:
        if not self.thresholds.get("track_wpm", False):
            return {"indicator": "white", "message": ""}

        current_wpm = self.calculate_wpm()
        
        upper = self.thresholds.get("wpm_upper_limit", 160)
        lower = self.thresholds.get("wpm_lower_limit", 110)
        trigger = self.thresholds.get("wpm_violation_trigger", "yellow")

        if current_wpm > upper:
            return {"indicator": trigger, "message": str(int(current_wpm))}
        
        if current_wpm > 0 and current_wpm < lower:
            return {"indicator": trigger, "message": str(int(current_wpm))}

        return {"indicator": "green", "message": str(int(current_wpm))}