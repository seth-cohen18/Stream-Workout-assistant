# exercises/shoulder_press.py
import cv2
import mediapipe as mp
import math
import time
from collections import defaultdict
from core.pose_detector import PoseDetector

class ShoulderPressTracker:
    # Constants based on scientific measurements for proper form
    EXTENDED_ELBOW_THRESHOLD = 160  # Fully extended elbow angle (top position)
    STARTING_ELBOW_THRESHOLD = 90   # Elbow angle at starting position (90° or less)
    MIN_ELBOW_RAISE = 15            # Minimal elbow angle increase to start rep
    BACK_LEAN_THRESHOLD = 15        # Max back lean angle from vertical
    ELBOW_FORWARD_THRESHOLD = 0.05  # Elbow should not move too far forward

    def __init__(self):
        self.detector = PoseDetector()
        self.rep_count = 0
        self.in_press = False
        self.baseline_elbow = None           # Baseline elbow angle at starting position
        self.highest_elbow_angle = None      # Highest elbow angle during rep
        self.improper_back_lean_flag = False # Flag for excessive back lean
        self.improper_elbow_forward_flag = False # Flag for improper elbow position
        self.start_time = None               # For timing the rep
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
        
        # Check visibility of required landmarks
        required = [
            self.detector.LEFT_SHOULDER, self.detector.LEFT_ELBOW, self.detector.LEFT_WRIST,
            self.detector.RIGHT_SHOULDER, self.detector.RIGHT_ELBOW, self.detector.RIGHT_WRIST,
            self.detector.LEFT_HIP, self.detector.RIGHT_HIP
        ]
        
        if not all(landmarks[idx].visibility > 0.5 for idx in required):
            feedback = "Waiting for user... (arms and upper body must be visible)"
            if current_time - self.last_wait_time >= 5:
                self.last_wait_time = current_time
                self.last_feedback = feedback
            return frame, self.last_feedback, self.rep_count, 0

        if self.last_feedback.startswith("Waiting for user"):
            self.last_feedback = "Begin exercise."
            
        # Calculate elbow angles (average of both sides)
        left_elbow_angle = self.detector.calculate_angle(
            landmarks[self.detector.LEFT_SHOULDER],
            landmarks[self.detector.LEFT_ELBOW],
            landmarks[self.detector.LEFT_WRIST]
        )
        
        right_elbow_angle = self.detector.calculate_angle(
            landmarks[self.detector.RIGHT_SHOULDER],
            landmarks[self.detector.RIGHT_ELBOW],
            landmarks[self.detector.RIGHT_WRIST]
        )
        
        current_elbow_angle = (left_elbow_angle + right_elbow_angle) / 2
        
        # Check back alignment (should be straight)
        left_spine_vertical = self.calculate_vertical_angle(
            [landmarks[self.detector.LEFT_SHOULDER].x, landmarks[self.detector.LEFT_SHOULDER].y],
            [landmarks[self.detector.LEFT_HIP].x, landmarks[self.detector.LEFT_HIP].y]
        )
        
        right_spine_vertical = self.calculate_vertical_angle(
            [landmarks[self.detector.RIGHT_SHOULDER].x, landmarks[self.detector.RIGHT_SHOULDER].y],
            [landmarks[self.detector.RIGHT_HIP].x, landmarks[self.detector.RIGHT_HIP].y]
        )
        
        spine_vertical_angle = (left_spine_vertical + right_spine_vertical) / 2
        
        # Check elbow position (should not move too far forward)
        left_elbow_forward = landmarks[self.detector.LEFT_ELBOW].z < landmarks[self.detector.LEFT_SHOULDER].z - self.ELBOW_FORWARD_THRESHOLD
        right_elbow_forward = landmarks[self.detector.RIGHT_ELBOW].z < landmarks[self.detector.RIGHT_SHOULDER].z - self.ELBOW_FORWARD_THRESHOLD
        elbows_forward = left_elbow_forward or right_elbow_forward
        
        # Update baseline when arms at starting position
        if current_elbow_angle <= self.STARTING_ELBOW_THRESHOLD and not self.in_press and self.highest_elbow_angle is None:
            self.baseline_elbow = current_elbow_angle
            
        # Rep Attempt Initiation
        if not self.in_press and self.baseline_elbow is not None and (current_elbow_angle - self.baseline_elbow) > self.MIN_ELBOW_RAISE:
            self.in_press = True
            self.start_time = current_time
            self.highest_elbow_angle = current_elbow_angle
            self.improper_back_lean_flag = False
            self.improper_elbow_forward_flag = False
            # exercises/shoulder_press.py (continued)
        feedback = ""
        rep_time = 0
        
        # During the shoulder press
        if self.in_press:
            # Update highest elbow angle during the press
            if current_elbow_angle > self.highest_elbow_angle:
                self.highest_elbow_angle = current_elbow_angle
                
            # Check for improper back lean
            if spine_vertical_angle > self.BACK_LEAN_THRESHOLD:
                self.improper_back_lean_flag = True
                
            # Check for improper elbow position
            if elbows_forward:
                self.improper_elbow_forward_flag = True
                
            # Rep Completion Check
            if current_elbow_angle <= self.STARTING_ELBOW_THRESHOLD:
                rep_time = current_time - self.start_time
                
                issues = []
                
                # Check full extension
                if self.highest_elbow_angle < self.EXTENDED_ELBOW_THRESHOLD:
                    issues.append("Extend arms fully overhead!")
                    
                # Check back posture
                if self.improper_back_lean_flag:
                    issues.append("Keep back straight, don't lean back!")
                    
                # Check elbow position
                if self.improper_elbow_forward_flag:
                    issues.append("Keep elbows out to sides, not forward!")
                    
                if issues:
                    feedback = " ".join(issues)
                else:
                    self.rep_count += 1
                    rounded_time = round(rep_time * 2) / 2
                    self.rep_time_intervals[rounded_time] += 1
                    self.rep_times.append(rep_time)
                    
                # Reset for next rep
                self.in_press = False
                self.highest_elbow_angle = None
                self.baseline_elbow = current_elbow_angle
                
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
        
    def calculate_vertical_angle(self, a, b):
        """Calculate the angle between a vector and the vertical axis."""
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        
        # Angle with vertical (y-axis)
        radians = math.atan2(dx, dy)
        return abs(radians * 180.0 / math.pi)
        
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