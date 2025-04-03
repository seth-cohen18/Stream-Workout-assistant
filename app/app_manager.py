# app/app_manager.py
import os
import time
import cv2
import numpy as np
import base64
import json
from datetime import datetime
from core.text_to_speech_manager import TextToSpeechManager
from exercises.squats import SquatTracker
from exercises.bicep_curls import BicepCurlTracker
from exercises.pushups import PushUpTracker
from exercises.shoulder_press import ShoulderPressTracker
from exercises.lunges import LungeTracker

# Map exercise names to their tracker classes
EXERCISE_TRACKERS = {
    "Squats": SquatTracker,
    "Bicep Curls": BicepCurlTracker,
    "Push-Ups": PushUpTracker,
    "Shoulder Press": ShoulderPressTracker,
    "Lunges": LungeTracker
}

class AppManager:
    def __init__(self):
        self.tts = TextToSpeechManager()
        self.current_tracker = None
        self.current_exercise = None
        self.session_results = {"rep_times": [], "rep_count": 0, "feedback_history": []}
        
        # Load user profile if exists, otherwise create new one
        self.profile_path = 'user_profile.json'
        if os.path.exists(self.profile_path):
            with open(self.profile_path, 'r') as f:
                self.profile = json.load(f)
        else:
            self.profile = {
                "Squats": {"latest_reps": 0, "progress": []},
                "Bicep Curls": {"latest_reps": 0, "progress": []},
                "Push-Ups": {"latest_reps": 0, "progress": []},
                "Shoulder Press": {"latest_reps": 0, "progress": []},
                "Lunges": {"latest_reps": 0, "progress": []}
            }
        
        self.video_frames = []  # For storing frames
        self.previous_feedback = ""
        self.last_spoken_time = 0
        self.recording = False
        self.video_writer = None

    def get_profile(self):
        return self.profile

    def start_session(self, exercise):
        if exercise in EXERCISE_TRACKERS:
            self.current_exercise = exercise
            self.current_tracker = EXERCISE_TRACKERS[exercise]()
            self.session_results = {"rep_times": [], "rep_count": 0, "feedback_history": []}
            self.video_frames = []
            self.previous_feedback = ""
            self.recording = True
            return True
        else:
            print(f"Invalid exercise selected: {exercise}")
            return False

    def process_frame(self, frame):
        if self.recording:
            self.video_frames.append(frame.copy())
        
        if self.current_tracker is not None:
            try:
                # Process the frame with the current exercise tracker
                processed_frame, feedback, rep_count, rep_time = self.current_tracker.track(frame)
                
                # Handle text-to-speech feedback
                current_time = time.time()
                if feedback and feedback != self.previous_feedback:
                    # Only speak feedback that has changed
                    if feedback == "Begin exercise." or not feedback.startswith("Waiting for user"):
                        # Add speech for new reps
                        if rep_count > self.session_results["rep_count"]:
                            new_reps = rep_count - self.session_results["rep_count"]
                            if new_reps == 1:
                                self.tts.speak(f"{rep_count}")
                            else:
                                self.tts.speak(f"Great! {rep_count} reps completed")
                                
                        # Speak form feedback
                        if not feedback.startswith("Waiting") and feedback != "Begin exercise.":
                            self.tts.speak(feedback)
                            
                    self.previous_feedback = feedback
                    self.last_spoken_time = current_time
                    
                    # Store feedback in session results
                    if feedback and not feedback.startswith("Waiting for user"):
                        self.session_results["feedback_history"].append(feedback)
                
                # Update rep count and times
                if rep_count > self.session_results["rep_count"] and rep_time > 0:
                    self.session_results["rep_count"] = rep_count
                    # Round to nearest 0.5 second for better time tracking
                    rounded_time = round(rep_time * 2) / 2
                    self.session_results["rep_times"].append(rounded_time)
                
                return processed_frame, rep_count, self.session_results
                
            except Exception as ex:
                print(f"Error in tracker.track: {ex}")
                import traceback
                traceback.print_exc()
                return frame, self.session_results.get("rep_count", 0), self.session_results
                
        return frame, 0, self.session_results

    def save_workout_video(self, filename=None):
        """Save the recorded workout video."""
        if not self.video_frames:
            return False, "No frames to save"
            
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            exercise = self.current_exercise.replace(" ", "_") if self.current_exercise else "workout"
            filename = f"{exercise}_{timestamp}.mp4"
        
        # Ensure uploads directory exists
        os.makedirs('uploads', exist_ok=True)
        
        # Complete filepath
        filepath = os.path.join('uploads', filename)
        
        try:
            # Get frame dimensions from the first frame
            h, w, _ = self.video_frames[0].shape
            
            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(filepath, fourcc, 25.0, (w, h))
            
            # Write frames to video
            for frame in self.video_frames:
                out.write(frame)
            
            out.release()
            return True, filepath
        except Exception as e:
            print(f"Error saving video: {e}")
            return False, str(e)

    def end_session(self, save_video=True):
        if not self.current_tracker:
            return False, {}
            
        # Get session summary
        if hasattr(self.current_tracker, 'get_session_summary'):
            summary = self.current_tracker.get_session_summary()
        else:
            summary = {
                "total_reps": self.session_results["rep_count"],
                "rep_times": self.session_results["rep_times"],
                "feedback": self.session_results["feedback_history"]
            }
        
        # Save video if requested
        video_saved = False
        video_path = ""
        if save_video:
            video_saved, video_path = self.save_workout_video()
            
        # Update profile with session data
        if self.current_exercise:
            self.profile[self.current_exercise]["latest_reps"] = summary["total_reps"]
            
            # Store workout data with timestamp
            workout_data = {
                "date": datetime.now().isoformat(),
                "reps": summary["total_reps"],
                "rep_times": summary["rep_times"],
                "video_path": video_path if video_saved else ""
            }
            
            self.profile[self.current_exercise]["progress"].append(workout_data)
            
            # Save updated profile to file
            with open(self.profile_path, 'w') as f:
                json.dump(self.profile, f, indent=2)
        
        # Reset recording state
        self.recording = False
        self.video_frames = []
        
        # Clean up
        self.current_tracker = None
        self.current_exercise = None
        
        # Include video info in summary
        summary["video_saved"] = video_saved
        summary["video_path"] = video_path
        
        return True, summary