# app/app_manager.py
import os
import time
import cv2
import numpy as np
import base64
import matplotlib.pyplot as plt
from datetime import datetime
from core.text_to_speech_manager import TextToSpeechManager
from exercises.squats import SquatTracker
from exercises.bicep_curls import BicepCurlTracker
from exercises.pushups import PushUpTracker

# Map exercise names to their tracker constructors.
EXERCISE_TRACKERS = {
    "Squats": lambda: SquatTracker({"max_knee_angle": 90, "min_back_angle": 35}),
    "Bicep Curls": lambda: BicepCurlTracker(),
    "Push-Ups": lambda: PushUpTracker({"max_elbow_angle": 90, "min_body_line": 160})
}

class AppManager:
    def __init__(self):
        self.tts = TextToSpeechManager()
        self.current_tracker = None
        self.current_exercise = None
        self.session_results = {"rep_times": [], "rep_count": 0, "feedback_history": []}
        self.profile = {
            "Squats": {"latest_reps": 0, "progress": []},
            "Bicep Curls": {"latest_reps": 0, "progress": []},
            "Push-Ups": {"latest_reps": 0, "progress": []}
        }
        self.video_data = []  # For storing frames.

    def get_profile(self):
        return self.profile

    def start_session(self, exercise):
        if exercise in EXERCISE_TRACKERS:
            self.current_exercise = exercise
            self.current_tracker = EXERCISE_TRACKERS[exercise]()
            self.session_results = {"rep_times": [], "rep_count": 0, "feedback_history": []}
            self.video_data = []
            # When session starts and user is in frame, say "Begin exercise" once.
            self.tts.speak("Begin exercise.")
        else:
            print("Invalid exercise selected.")

    def process_frame(self, frame):
        self.video_data.append(frame.copy())
        if self.current_tracker is not None:
            try:
                result = self.current_tracker.track(frame)
                if result is None:
                    return frame, 0, self.session_results
                processed_frame, feedback, rep_count, rep_time = result
            except Exception as ex:
                print("Error in tracker.track:", ex)
                return frame, 0, self.session_results
            if feedback and not feedback.lower().startswith("waiting for user"):
                self.session_results["feedback_history"].append(feedback)
            if rep_count > self.session_results["rep_count"] and rep_time > 0:
                self.session_results["rep_count"] = rep_count
                self.session_results["rep_times"].append(rep_time)
            return processed_frame, rep_count, self.session_results
        return frame, 0, self.session_results

    def end_session(self):
        # Instead of a terminal prompt, now show a JS prompt (sent from the front end).
        # Here we simulate by using input (the front end should handle this in a production version).
        choice = input(f"Session finished. Save session video? (y/n): ").strip().lower()
        saved = True
        if choice != "y":
            saved = False
            print("Video discarded.")
        else:
            print("Video saved (simulation).")
        summary = {
            "total_reps": self.session_results["rep_count"],
            "rep_times": self.session_results["rep_times"],
            "feedback": self.session_results["feedback_history"]
        }
        if self.current_exercise:
            self.profile[self.current_exercise]["latest_reps"] = self.session_results["rep_count"]
            self.profile[self.current_exercise]["progress"].append({
                "date": datetime.now().isoformat(),
                "reps": self.session_results["rep_count"],
                "rep_times": self.session_results["rep_times"]
            })
        return saved, summary
