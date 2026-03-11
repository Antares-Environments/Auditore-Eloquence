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
        # Absolute mathematical zero protection
        if elapsed_minutes <= 0.0001: 
            return 0.0
        return self.word_count / elapsed_minutes

    def evaluate_thresholds(self) -> Dict[str, str]:
        if not self.thresholds.get("track_wpm", False):
            # Silent compliance if the template disables tracking
            return {"indicator": "white", "message": "WPM UNTRACKED"}

        elapsed_seconds = time.time() - self.start_time
        current_wpm = self.calculate_wpm()
        
        # 5-second stabilization buffer to prevent instant mathematical spikes
        if elapsed_seconds < 5.0:
            return {"indicator": "white", "message": f"CALCULATING PACE... {int(current_wpm)} WPM"}

        upper = self.thresholds.get("wpm_upper_limit", 160)
        lower = self.thresholds.get("wpm_lower_limit", 110)
        trigger = self.thresholds.get("wpm_violation_trigger", "yellow")

        if current_wpm > upper:
            return {"indicator": trigger, "message": f"WPM VIOLATION: {int(current_wpm)} (TOO FAST)"}
        
        if current_wpm > 0 and current_wpm < lower:
            return {"indicator": trigger, "message": f"WPM VIOLATION: {int(current_wpm)} (TOO SLOW)"}

        return {"indicator": "green", "message": f"PACE OPTIMAL: {int(current_wpm)} WPM"}