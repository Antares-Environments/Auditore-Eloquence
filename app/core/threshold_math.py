# app/core/threshold_math.py
import time
from typing import Dict, Any
from collections import deque

class ThresholdMonitor:
    def __init__(self, thresholds: Dict[str, Any]):
        self.thresholds = thresholds
        self.start_time = time.time()
        self.word_history = deque()
        self.rolling_window_seconds = 60.0

    def update_words(self, current_total_words: int):
        current_time = time.time()
        self.word_history.append((current_time, current_total_words))
        self._prune_history(current_time)

    def _prune_history(self, current_time: float):
        # Remove word entries older than the 60-second rolling window
        while self.word_history and (current_time - self.word_history[0][0]) > self.rolling_window_seconds:
            self.word_history.popleft()

    def calculate_wpm(self) -> float:
        current_time = time.time()
        self._prune_history(current_time)

        if len(self.word_history) < 2:
            return 0.0

        # Calculate delta between the oldest and newest records in the current window
        oldest_time, oldest_count = self.word_history[0]
        newest_time, newest_count = self.word_history[-1]
        
        words_spoken_in_window = newest_count - oldest_count
        elapsed_seconds_in_window = newest_time - oldest_time
        
        # Absolute mathematical zero protection
        elapsed_seconds_in_window = max(1.0, elapsed_seconds_in_window) 
        
        return (words_spoken_in_window / elapsed_seconds_in_window) * 60.0

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