# exercises/squats.py
import cv2
import mediapipe as mp
import math
import time
from collections import defaultdict
from core.pose_detector import PoseDetector

class SquatTracker:
    # Constants based on scientific measurements for proper form
    SQUAT_THRESHOLD = 90      # Knee angle must be below this for a proper deep squat
    STAND_THRESHOLD = 160     # Knee angle above this indicates full standing
    BACK_THRESHOLD = 35       # Minimal allowed back angle (shoulder-hip-knee)
    FOOT_THRESHOLD = 0.02     # Foot should remain flat relative to the ankle
    HIP_DROP_THRESHOLD = 0.05 # Required hip drop for a proper squat
    MIN_HIP_DROP = 0.005      # Minimal hip drop to initiate a rep
    
    def __init__(self, thresholds=None):
        self.detector = PoseDetector()
        self.thresholds = thresholds or {"max_knee_angle": 90, "min_back_angle": 35}
        self.rep_count = 0
        self.in_squat = False
        self.standing_hip_y = None        # Baseline hip y-coordinate when standing
        self.lowest_hip_y = None          # Deepest hip y-coordinate during rep
        self.lowest_knee_angle = None     # Smallest knee angle during rep
        self.lowest_back_angle = None     # Smallest back angle during rep
        self.start_time = None            # For timing the rep
        self.last_wait_time = 0
        self.rep_times = []
        self.feedback_history = []
        self.last_feedback = "Waiting for user..."
        self.rep_time_intervals = defaultdict(int)

    def track(self, frame):
        results = self.detector.process_frame(frame)
        current_time = time.time()
        
        if not (results and results.pose_landmarks):
            feedback = ""
            if current_time - self.last_wait_time >= 5:
                feedback = "Waiting for user..."
                self.last_wait_time = current_time
                self.last_feedback = feedback
            return frame, self.last_feedback, self.rep_count, 0

        landmarks = results.pose_landmarks.landmark
        
        # Check visibility for both sides
        left_available = (
            landmarks[self.detector.LEFT_SHOULDER].visibility > 0.5 and
            landmarks[self.detector.LEFT_HIP].visibility > 0.5 and
            landmarks[self.detector.LEFT_KNEE].visibility > 0.5 and
            landmarks[self.detector.LEFT_ANKLE].visibility > 0.5 and
            landmarks[self.detector.LEFT_FOOT_INDEX].visibility > 0.5
        )
        
        right_available = (
            landmarks[self.detector.RIGHT_SHOULDER].visibility > 0.5 and
            landmarks[self.detector.RIGHT_HIP].visibility > 0.5 and
            landmarks[self.detector.RIGHT_KNEE].visibility > 0.5 and
            landmarks[self.detector.RIGHT_ANKLE].visibility > 0.5 and
            landmarks[self.detector.RIGHT_FOOT_INDEX].visibility > 0.5
        )
        
        if not (left_available or right_available):
            feedback = "Waiting for user..."
            if current_time - self.last_wait_time >= 5:
                self.last_wait_time = current_time
                self.last_feedback = feedback
            return frame, self.last_feedback, self.rep_count, 0

        # Prefer left side if available
        if left_available:
            shoulder = landmarks[self.detector.LEFT_SHOULDER]
            hip = landmarks[self.detector.LEFT_HIP]
            knee = landmarks[self.detector.LEFT_KNEE]
            ankle = landmarks[self.detector.LEFT_ANKLE]
            foot = landmarks[self.detector.LEFT_FOOT_INDEX]
        else:
            shoulder = landmarks[self.detector.RIGHT_SHOULDER]
            hip = landmarks[self.detector.RIGHT_HIP]
            knee = landmarks[self.detector.RIGHT_KNEE]
            ankle = landmarks[self.detector.RIGHT_ANKLE]
            foot = landmarks[self.detector.RIGHT_FOOT_INDEX]

        if self.last_feedback == "Waiting for user...":
            self.last_feedback = "Begin exercise."
            
        # Calculate angles
        current_knee_angle = self.detector.calculate_angle(hip, knee, ankle)
        current_back_angle = self.detector.calculate_angle(shoulder, hip, knee)
        
        # Update the standing baseline when fully upright
        if current_knee_angle > self.STAND_THRESHOLD:
            self.standing_hip_y = hip.y
            
        # Rep Attempt Initiation
        if not self.in_squat and self.standing_hip_y is not None and (hip.y - self.standing_hip_y) > self.MIN_HIP_DROP:
            self.in_squat = True
            self.start_time = current_time
            self.lowest_hip_y = hip.y
            self.lowest_knee_angle = current_knee_angle
            self.lowest_back_angle = current_back_angle
            
        feedback = ""
        rep_time = 0
        
        # During the squat
        if self.in_squat:
            # Update lowest points
            if hip.y > self.lowest_hip_y:
                self.lowest_hip_y = hip.y
                
            if current_knee_angle < self.lowest_knee_angle:
                self.lowest_knee_angle = current_knee_angle
                
            if current_back_angle < self.lowest_back_angle:
                self.lowest_back_angle = current_back_angle
                
            # Rep Completion Check
            if current_knee_angle > self.STAND_THRESHOLD:
                rep_time = current_time - self.start_time
                hip_drop = self.lowest_hip_y - self.standing_hip_y
                
                issues = []
                
                # Check squat depth
                if self.lowest_knee_angle >= self.SQUAT_THRESHOLD:
                    issues.append("Squat lower!")
                    
                # Check back posture
                if self.lowest_back_angle < self.BACK_THRESHOLD:
                    issues.append("Keep your back straighter!")
                    
                # Check feet position
                if foot.y < ankle.y - self.FOOT_THRESHOLD:
                    issues.append("Keep your feet flat!")
                    
                # Check hip drop
                if hip_drop < self.HIP_DROP_THRESHOLD:
                    issues.append("Lower your hips more!")
                    
                if issues:
                    feedback = " ".join(issues)
                else:
                    self.rep_count += 1
                    rounded_time = round(rep_time * 2) / 2
                    self.rep_time_intervals[rounded_time] += 1
                    self.rep_times.append(rep_time)
                    
                # Reset for next rep
                self.in_squat = False
                self.lowest_hip_y = None
                self.lowest_knee_angle = None
                self.lowest_back_angle = None
                self.standing_hip_y = hip.y  # Update standing position
                
        # Store feedback if it's new
        if feedback:
            self.last_feedback = feedback
            if not feedback.startswith("Waiting"):
                self.feedback_history.append(feedback)
                
        # Overlay information on the frame
        text_x, text_y = 50, 50
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1
        text_color = (255, 255, 255)
        thickness = 2

        cv2.putText(frame, self.last_feedback, (text_x, text_y), font, font_scale, (0, 0, 0), thickness * 4)
        cv2.putText(frame, self.last_feedback, (text_x, text_y), font, font_scale, text_color, thickness)
        rep_text = f"Reps: {self.rep_count}"
        cv2.putText(frame, rep_text, (text_x, text_y + 40), font, font_scale, (0, 0, 0), thickness * 4)
        cv2.putText(frame, rep_text, (text_x, text_y + 40), font, font_scale, text_color, thickness)

        return frame, self.last_feedback, self.rep_count, rep_time
        
    def get_session_summary(self):
        # Calculate average rep time
        avg_rep_time = 0
        if self.rep_times:
            avg_rep_time = sum(self.rep_times) / len(self.rep_times)
            
        return {
            "total_reps": self.rep_count,
            "rep_times": self.rep_times,
            "average_rep_time": avg_rep_time,
            "feedback": self.feedback_history,
            "rep_time_intervals": dict(self.rep_time_intervals)
        }