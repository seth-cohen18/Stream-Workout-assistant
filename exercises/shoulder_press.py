# exercises/shoulder_press.py
import cv2
import mediapipe as mp
import math
import time
import numpy as np
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
        self.current_rep_start_time = None

    def track(self, frame):
        original_frame = frame.copy()
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
            self.current_rep_start_time = current_time
            self.highest_elbow_angle = current_elbow_angle
            self.improper_back_lean_flag = False
            self.improper_elbow_forward_flag = False
            
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
                self.current_rep_start_time = None
                
        # Store feedback if it's new
        if feedback:
            self.last_feedback = feedback
            if not feedback.startswith("Waiting"):
                self.feedback_history.append(feedback)
        
        # Draw additional visual cues on the frame
        self.draw_visual_feedback(frame, landmarks, current_elbow_angle, spine_vertical_angle, elbows_forward)
        
        # Overlay information on the frame
        self.draw_info_overlay(frame)
        
        return frame, self.last_feedback, self.rep_count, rep_time
    
    def draw_visual_feedback(self, frame, landmarks, elbow_angle, spine_angle, elbows_forward):
        """Draw visual feedback elements on the frame"""
        h, w, _ = frame.shape
        
        # Get key coordinates
        left_shoulder = landmarks[self.detector.LEFT_SHOULDER]
        left_elbow = landmarks[self.detector.LEFT_ELBOW]
        left_wrist = landmarks[self.detector.LEFT_WRIST]
        left_hip = landmarks[self.detector.LEFT_HIP]
        
        right_shoulder = landmarks[self.detector.RIGHT_SHOULDER]
        right_elbow = landmarks[self.detector.RIGHT_ELBOW]
        right_wrist = landmarks[self.detector.RIGHT_WRIST]
        right_hip = landmarks[self.detector.RIGHT_HIP]
        
        # Convert normalized coordinates to pixel coordinates
        left_shoulder_px = (int(left_shoulder.x * w), int(left_shoulder.y * h))
        left_elbow_px = (int(left_elbow.x * w), int(left_elbow.y * h))
        left_wrist_px = (int(left_wrist.x * w), int(left_wrist.y * h))
        left_hip_px = (int(left_hip.x * w), int(left_hip.y * h))
        
        right_shoulder_px = (int(right_shoulder.x * w), int(right_shoulder.y * h))
        right_elbow_px = (int(right_elbow.x * w), int(right_elbow.y * h))
        right_wrist_px = (int(right_wrist.x * w), int(right_wrist.y * h))
        right_hip_px = (int(right_hip.x * w), int(right_hip.y * h))
        
        # Draw spine angle indicators (vertical line)
        # Left side
        self.draw_vertical_reference(frame, left_shoulder_px, left_hip_px)
        
        # Right side
        self.draw_vertical_reference(frame, right_shoulder_px, right_hip_px)
        
        # Draw elbow angles
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
        
        self.draw_angle_arc(frame, left_shoulder_px, left_elbow_px, left_wrist_px, left_elbow_angle)
        self.draw_angle_arc(frame, right_shoulder_px, right_elbow_px, right_wrist_px, right_elbow_angle)
        
        # Draw rep timing indicator if in a press
        if self.in_press and self.current_rep_start_time:
            current_duration = time.time() - self.current_rep_start_time
            # Draw a timer box at the top of the frame
            timer_width = int(min(current_duration * 50, w-40))  # Scale timer width by duration
            cv2.rectangle(frame, (20, 20), (20 + timer_width, 40), (0, 255, 0), -1)
            cv2.rectangle(frame, (20, 20), (w-20, 40), (255, 255, 255), 2)
            
            # Display current time
            cv2.putText(frame, f"{current_duration:.1f}s", 
                      (w-100, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Draw form indicators
        # Extension indicator
        if self.in_press:
            extension_status = "GOOD" if self.highest_elbow_angle >= self.EXTENDED_ELBOW_THRESHOLD else "INCOMPLETE"
            extension_color = (0, 255, 0) if extension_status == "GOOD" else (0, 165, 255)
            cv2.putText(frame, f"Arm extension: {extension_status}", 
                      (20, h-90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, extension_color, 2)
        
        # Back posture indicator
        back_status = "GOOD" if spine_angle <= self.BACK_LEAN_THRESHOLD else "LEANING BACK"
        back_color = (0, 255, 0) if back_status == "GOOD" else (0, 0, 255)
        
        cv2.putText(frame, f"Back posture: {back_status}", 
                  (20, h-60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, back_color, 2)
                  
        # Elbow position indicator
        elbow_status = "GOOD" if not elbows_forward else "TOO FORWARD"
        elbow_color = (0, 255, 0) if elbow_status == "GOOD" else (0, 0, 255)
        
        cv2.putText(frame, f"Elbow position: {elbow_status}", 
                  (20, h-30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, elbow_color, 2)
    
    def draw_vertical_reference(self, frame, shoulder_px, hip_px):
        """Draw a vertical reference line to check spine alignment"""
        # Draw a vertical line from shoulder down
        vertical_x = shoulder_px[0]
        vertical_top = (vertical_x, shoulder_px[1])
        vertical_bottom = (vertical_x, hip_px[1])
        
        # Calculate angle with vertical
        shoulder_hip_vector = [hip_px[0] - shoulder_px[0], hip_px[1] - shoulder_px[1]]
        vertical_vector = [0, hip_px[1] - shoulder_px[1]]
        
        # Calculate dot product
        dot = shoulder_hip_vector[0] * vertical_vector[0] + shoulder_hip_vector[1] * vertical_vector[1]
        mag1 = math.sqrt(shoulder_hip_vector[0]**2 + shoulder_hip_vector[1]**2)
        mag2 = math.sqrt(vertical_vector[0]**2 + vertical_vector[1]**2)
        
        # Avoid division by zero
        if mag1 * mag2 == 0:
            angle = 0
        else:
            cos_angle = dot / (mag1 * mag2)
            cos_angle = max(min(cos_angle, 1.0), -1.0)
            angle = math.degrees(math.acos(cos_angle))
        
        # Determine color based on angle
        if angle <= self.BACK_LEAN_THRESHOLD:
            color = (0, 255, 0)  # Green for good alignment
        else:
            color = (0, 0, 255)  # Red for poor alignment
        
        # Draw vertical reference line (dashed)
        dash_length = 10
        gap_length = 5
        y_start = shoulder_px[1]
        y_end = hip_px[1]
        
        for y in range(y_start, y_end, dash_length + gap_length):
            y2 = min(y + dash_length, y_end)
            cv2.line(frame, (vertical_x, y), (vertical_x, y2), (255, 255, 255), 1)
        
        # Draw actual spine line
        cv2.line(frame, shoulder_px, hip_px, color, 2)
        
        # Add angle text
        mid_y = (shoulder_px[1] + hip_px[1]) // 2
        cv2.putText(frame, f"{int(angle)}°", (shoulder_px[0] + 10, mid_y), 
                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    
    def draw_angle_arc(self, frame, point1, point2, point3, angle):
        """Draw an arc showing the angle between three points"""
        # Calculate vectors
        vec1 = np.array([point1[0] - point2[0], point1[1] - point2[1]])
        vec2 = np.array([point3[0] - point2[0], point3[1] - point2[1]])
        
        # Avoid division by zero
        vec1_norm = vec1 / (np.linalg.norm(vec1) + 1e-6)
        vec2_norm = vec2 / (np.linalg.norm(vec2) + 1e-6)
        
        # Calculate the angle in radians
        cos_angle = np.clip(np.dot(vec1_norm, vec2_norm), -1.0, 1.0)
        angle_rad = np.arccos(cos_angle)
        
        # Determine the direction of the arc (clockwise or counterclockwise)
        cross_product = np.cross([vec1_norm[0], vec1_norm[1], 0], [vec2_norm[0], vec2_norm[1], 0])
        if cross_product[2] < 0:
            angle_rad = 2 * np.pi - angle_rad
        
        # Calculate the start angle
        start_angle = np.arctan2(vec1[1], vec1[0])
        
        # Set arc properties
        radius = min(int(np.linalg.norm(vec1) * 0.3), int(np.linalg.norm(vec2) * 0.3))
        radius = max(radius, 20)  # Minimum radius
        
        # Determine color based on angle and context (press vs starting position)
        if self.in_press and angle >= self.EXTENDED_ELBOW_THRESHOLD:
            color = (0, 255, 0)  # Green for good extension
        elif not self.in_press and angle <= self.STARTING_ELBOW_THRESHOLD:
            color = (0, 255, 0)  # Green for good starting position
        else:
            color = (0, 165, 255)  # Orange for intermediate positions
            
        # Draw the arc
        cv2.ellipse(frame, point2, (radius, radius), 
                  np.degrees(start_angle), 0, np.degrees(angle_rad), color, 3)
        
        # Add the angle text
        text_angle = start_angle + angle_rad / 2
        text_x = int(point2[0] + (radius + 20) * np.cos(text_angle))
        text_y = int(point2[1] + (radius + 20) * np.sin(text_angle))
        
        cv2.putText(frame, f"{int(angle)}°", (text_x, text_y), 
                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
    def draw_info_overlay(self, frame):
        """Draw general information overlay on the frame"""
        h, w, _ = frame.shape
        
        # Create a semi-transparent overlay for the top info bar
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 100), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        # Draw exercise info and rep count
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(frame, "SHOULDER PRESS", (20, 40), font, 1, (255, 255, 255), 2)
        
        rep_text = f"Reps: {self.rep_count}"
        cv2.putText(frame, rep_text, (w - 150, 40), font, 1, (255, 255, 255), 2)
        
        # Draw feedback message
        cv2.putText(frame, self.last_feedback, (20, 80), font, 0.7, (255, 255, 255), 2)
        
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