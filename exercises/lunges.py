# exercises/lunges.py
import cv2
import mediapipe as mp
import math
import time
from collections import defaultdict
from core.pose_detector import PoseDetector

class LungeTracker:
    # Constants based on scientific measurements for proper form
    STANDING_KNEE_THRESHOLD = 160  # Knee angle when standing
    FRONT_KNEE_THRESHOLD = 100     # Front knee should bend to 90° (allow a bit more)
    BACK_KNEE_THRESHOLD = 120      # Back knee should bend adequately
    FRONT_KNEE_ALIGNMENT = 0.10    # Front knee should not go beyond toes
    TORSO_VERTICAL_THRESHOLD = 20  # Torso should remain relatively vertical
    MIN_KNEE_DROP = 20             # Minimal knee angle change to start a rep

    def __init__(self):
        self.detector = PoseDetector()
        self.rep_count = 0
        self.in_lunge = False
        self.starting_knee_angle = None       # Baseline knee angle when standing
        self.lowest_front_knee_angle = None   # Lowest front knee angle during rep
        self.lowest_back_knee_angle = None    # Lowest back knee angle during rep
        self.improper_knee_alignment_flag = False  # Flag for improper knee alignment
        self.improper_torso_angle_flag = False     # Flag for improper torso angle
        self.current_side = None               # Track which leg is currently forward
        self.last_side = None                  # Track which leg was forward in last rep
        self.start_time = None                 # For timing the rep
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
            self.detector.LEFT_SHOULDER, self.detector.RIGHT_SHOULDER,
            self.detector.LEFT_HIP, self.detector.RIGHT_HIP,
            self.detector.LEFT_KNEE, self.detector.RIGHT_KNEE,
            self.detector.LEFT_ANKLE, self.detector.RIGHT_ANKLE,
            self.detector.LEFT_FOOT_INDEX, self.detector.RIGHT_FOOT_INDEX
        ]
        
        if not all(landmarks[idx].visibility > 0.5 for idx in required):
            feedback = "Waiting for user... (full body must be visible)"
            if current_time - self.last_wait_time >= 5:
                self.last_wait_time = current_time
                self.last_feedback = feedback
            return frame, self.last_feedback, self.rep_count, 0

        if self.last_feedback.startswith("Waiting for user"):
            self.last_feedback = "Begin exercise."
            
        # Detect which leg is forward based on feet position
        left_foot_y = landmarks[self.detector.LEFT_FOOT_INDEX].y
        right_foot_y = landmarks[self.detector.RIGHT_FOOT_INDEX].y
        
        front_side = 'left' if left_foot_y < right_foot_y else 'right'
        back_side = 'right' if front_side == 'left' else 'left'
        
        # Calculate knee angles
        left_knee_angle = self.detector.calculate_angle(
            landmarks[self.detector.LEFT_HIP],
            landmarks[self.detector.LEFT_KNEE],
            landmarks[self.detector.LEFT_ANKLE]
        )
        
        right_knee_angle = self.detector.calculate_angle(
            landmarks[self.detector.RIGHT_HIP],
            landmarks[self.detector.RIGHT_KNEE],
            landmarks[self.detector.RIGHT_ANKLE]
        )
        
        # Assign front and back knee angles
        front_knee_angle = left_knee_angle if front_side == 'left' else right_knee_angle
        back_knee_angle = right_knee_angle if front_side == 'left' else left_knee_angle
        
        # Calculate torso angle (spine from vertical)
        left_shoulder_hip = self.calculate_vertical_angle(
            [landmarks[self.detector.LEFT_SHOULDER].x, landmarks[self.detector.LEFT_SHOULDER].y],
            [landmarks[self.detector.LEFT_HIP].x, landmarks[self.detector.LEFT_HIP].y]
        )
        
        right_shoulder_hip = self.calculate_vertical_angle(
            [landmarks[self.detector.RIGHT_SHOULDER].x, landmarks[self.detector.RIGHT_SHOULDER].y],
            [landmarks[self.detector.RIGHT_HIP].x, landmarks[self.detector.RIGHT_HIP].y]
        )
        
        torso_angle = (left_shoulder_hip + right_shoulder_hip) / 2
        
        # Check knee alignment (front knee should not go beyond toes)
        front_knee = landmarks[self.detector.LEFT_KNEE] if front_side == 'left' else landmarks[self.detector.RIGHT_KNEE]
        front_ankle = landmarks[self.detector.LEFT_ANKLE] if front_side == 'left' else landmarks[self.detector.RIGHT_ANKLE]
        knee_over_toes = front_knee.x > front_ankle.x + self.FRONT_KNEE_ALIGNMENT
        
        # Update tracking if not in a lunge and both knees are straight
        if not self.in_lunge and left_knee_angle > self.STANDING_KNEE_THRESHOLD and right_knee_angle > self.STANDING_KNEE_THRESHOLD:
            self.starting_knee_angle = (left_knee_angle + right_knee_angle) / 2
            
        # Rep Attempt Initiation
        if not self.in_lunge and self.starting_knee_angle is not None:
            if ((self.starting_knee_angle - front_knee_angle > self.MIN_KNEE_DROP) or
                (self.starting_knee_angle - back_knee_angle > self.MIN_KNEE_DROP)):
                self.in_lunge = True
                self.current_side = front_side
                self.start_time = current_time
                self.lowest_front_knee_angle = front_knee_angle
                self.lowest_back_knee_angle = back_knee_angle
                self.improper_knee_alignment_flag = False
                self.improper_torso_angle_flag = False
                
        feedback = ""
        rep_time = 0
        
        # During the lunge
        if self.in_lunge:
            # Update lowest knee angles during the lunge
            if front_knee_angle < self.lowest_front_knee_angle:
                self.lowest_front_knee_angle = front_knee_angle
                
            if back_knee_angle < self.lowest_back_knee_angle:
                self.lowest_back_knee_angle = back_knee_angle
                
            # Check for improper knee alignment
            if knee_over_toes:
                self.improper_knee_alignment_flag = True
                
            # Check for improper torso angle
            if torso_angle > self.TORSO_VERTICAL_THRESHOLD:
                self.improper_torso_angle_flag = True
                
            # Rep Completion Check
            if left_knee_angle > self.STANDING_KNEE_THRESHOLD and right_knee_angle > self.STANDING_KNEE_THRESHOLD:
                rep_time = current_time - self.start_time
                
                issues = []
                
                # Check front knee bend depth
                if self.lowest_front_knee_angle > self.FRONT_KNEE_THRESHOLD:
                    issues.append("Bend your front knee deeper!")
                    
                # Check back knee bend
                if self.lowest_back_knee_angle > self.BACK_KNEE_THRESHOLD:
                    issues.append("Lower your back knee more!")
                    
                # Check knee alignment
                if self.improper_knee_alignment_flag:
                    issues.append("Keep front knee over ankle, not beyond toes!")
                    
                # Check torso angle
                if self.improper_torso_angle_flag:
                    issues.append("Keep your torso upright!")
                    
                if issues:
                    feedback = " ".join(issues)
                else:
                    self.rep_count += 1
                    rounded_time = round(rep_time * 2) / 2
                    self.rep_time_intervals[rounded_time] += 1
                    self.rep_times.append(rep_time)
                    
                    # Check if alternating legs properly
                    if self.last_side and self.current_side == self.last_side and self.rep_count > 1:
                        feedback = "Try to alternate legs for balance!"
                        
                # Reset for next rep
                self.in_lunge = False
                self.last_side = self.current_side
                self.current_side = None
                self.lowest_front_knee_angle = None
                self.lowest_back_knee_angle = None
                
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