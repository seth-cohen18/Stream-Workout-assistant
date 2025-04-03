# exercises/bicep_curls.py
import cv2
import mediapipe as mp
import math
import time
from collections import defaultdict
from core.pose_detector import PoseDetector

class BicepCurlTracker:
    # Constants based on scientific measurements for proper form
    EXTENDED_THRESHOLD = 160    # Fully extended angle
    ELBOW_CONTRACT_THRESHOLD = 45  # For a proper curl, the lowest elbow angle must drop below this
    MIN_DROP = 10               # Minimal drop to start rep
    ELBOW_BODY_ANGLE_THRESHOLD = 15  # Elbow-to-body must be less than 15°

    def __init__(self):
        self.detector = PoseDetector()
        self.rep_count = 0
        self.in_rep = False
        self.baseline = None
        self.min_angle = None
        self.improper_flag = False
        self.start_time = None
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

        # Check visibility for both arms
        left_available = (
            landmarks[self.detector.LEFT_SHOULDER].visibility > 0.5 and
            landmarks[self.detector.LEFT_ELBOW].visibility > 0.5 and
            landmarks[self.detector.LEFT_WRIST].visibility > 0.5 and
            landmarks[self.detector.LEFT_HIP].visibility > 0.5
        )
        
        right_available = (
            landmarks[self.detector.RIGHT_SHOULDER].visibility > 0.5 and
            landmarks[self.detector.RIGHT_ELBOW].visibility > 0.5 and
            landmarks[self.detector.RIGHT_WRIST].visibility > 0.5 and
            landmarks[self.detector.RIGHT_HIP].visibility > 0.5
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
            elbow = landmarks[self.detector.LEFT_ELBOW]
            wrist = landmarks[self.detector.LEFT_WRIST]
            hip = landmarks[self.detector.LEFT_HIP]
        else:
            shoulder = landmarks[self.detector.RIGHT_SHOULDER]
            elbow = landmarks[self.detector.RIGHT_ELBOW]
            wrist = landmarks[self.detector.RIGHT_WRIST]
            hip = landmarks[self.detector.RIGHT_HIP]

        if self.last_feedback == "Waiting for user...":
            self.last_feedback = "Begin exercise."
            
        # Calculate the current elbow angle
        current_elbow_angle = self.detector.calculate_angle(shoulder, elbow, wrist)
        
        # Update baseline if arm is fully extended
        if current_elbow_angle > self.EXTENDED_THRESHOLD:
            self.baseline = current_elbow_angle
            
        # Rep Attempt Initiation
        if not self.in_rep and self.baseline is not None and (self.baseline - current_elbow_angle) > self.MIN_DROP:
            self.in_rep = True
            self.start_time = current_time
            self.min_angle = current_elbow_angle
            self.improper_flag = False  # Reset improper flag at rep start
            
        feedback = ""
        rep_time = 0
        
        # During the rep
        if self.in_rep:
            # Update lowest elbow angle
            if current_elbow_angle < self.min_angle:
                self.min_angle = current_elbow_angle
                
            # Check elbow-to-body alignment
            vec_SE = [elbow.x - shoulder.x, elbow.y - shoulder.y]
            vec_SH = [hip.x - shoulder.x, hip.y - shoulder.y]
            elbow_body_angle = self.calculate_vector_angle(vec_SE, vec_SH)
            
            if elbow_body_angle > self.ELBOW_BODY_ANGLE_THRESHOLD:
                self.improper_flag = True
                
            # Rep Completion Check
            if current_elbow_angle > self.EXTENDED_THRESHOLD:
                rep_time = current_time - self.start_time
                issues = []
                
                # Check curl depth
                if self.min_angle > self.ELBOW_CONTRACT_THRESHOLD:
                    issues.append("Curl further!")
                    
                # Check elbow position
                if self.improper_flag:
                    issues.append("Keep your elbows close to your body!")
                    
                if issues:
                    feedback = " ".join(issues)
                else:
                    self.rep_count += 1
                    rounded_time = round(rep_time * 2) / 2
                    self.rep_time_intervals[rounded_time] += 1
                    self.rep_times.append(rep_time)
                    
                # Reset for next rep
                self.in_rep = False
                self.min_angle = None
                self.baseline = current_elbow_angle
                
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
        
    def calculate_vector_angle(self, v1, v2):
        """Calculate the angle (in degrees) between two 2D vectors v1 and v2."""
        dot = v1[0]*v2[0] + v1[1]*v2[1]
        mag1 = math.sqrt(v1[0]**2 + v1[1]**2)
        mag2 = math.sqrt(v2[0]**2 + v2[1]**2)
        if mag1 == 0 or mag2 == 0:
            return 0
        cos_val = dot / (mag1 * mag2)
        cos_val = max(min(cos_val, 1.0), -1.0)
        return math.degrees(math.acos(cos_val))
        
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