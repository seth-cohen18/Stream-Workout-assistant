# exercises/bicep_curls.py
import cv2
import mediapipe as mp
import math
import time
import numpy as np
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
            side = "left"
        else:
            shoulder = landmarks[self.detector.RIGHT_SHOULDER]
            elbow = landmarks[self.detector.RIGHT_ELBOW]
            wrist = landmarks[self.detector.RIGHT_WRIST]
            hip = landmarks[self.detector.RIGHT_HIP]
            side = "right"

        if self.last_feedback == "Waiting for user...":
            self.last_feedback = "Begin exercise."
            
        # Calculate the current elbow angle
        current_elbow_angle = self.detector.calculate_angle(shoulder, elbow, wrist)
        
        # Calculate elbow-to-body angle
        vec_SE = [elbow.x - shoulder.x, elbow.y - shoulder.y]
        vec_SH = [hip.x - shoulder.x, hip.y - shoulder.y]
        elbow_body_angle = self.calculate_vector_angle(vec_SE, vec_SH)
        
        # Update baseline if arm is fully extended
        if current_elbow_angle > self.EXTENDED_THRESHOLD:
            self.baseline = current_elbow_angle
            
        # Rep Attempt Initiation
        if not self.in_rep and self.baseline is not None and (self.baseline - current_elbow_angle) > self.MIN_DROP:
            self.in_rep = True
            self.start_time = current_time
            self.current_rep_start_time = current_time
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
                self.current_rep_start_time = None
                
        # Store feedback if it's new
        if feedback:
            self.last_feedback = feedback
            if not feedback.startswith("Waiting"):
                self.feedback_history.append(feedback)
        
        # Draw additional visual cues on the frame
        self.draw_visual_feedback(frame, landmarks, current_elbow_angle, side, elbow_body_angle)
        
        # Overlay information on the frame
        self.draw_info_overlay(frame)
        
        return frame, self.last_feedback, self.rep_count, rep_time
    
    def draw_visual_feedback(self, frame, landmarks, current_elbow_angle, side, elbow_body_angle):
        """Draw visual feedback elements on the frame"""
        h, w, _ = frame.shape
        
        # Draw elbow angle arc
        if side == "left":
            shoulder = landmarks[self.detector.LEFT_SHOULDER]
            elbow = landmarks[self.detector.LEFT_ELBOW]
            wrist = landmarks[self.detector.LEFT_WRIST]
        else:
            shoulder = landmarks[self.detector.RIGHT_SHOULDER]
            elbow = landmarks[self.detector.RIGHT_ELBOW]
            wrist = landmarks[self.detector.RIGHT_WRIST]
            
        # Convert normalized coordinates to pixel coordinates
        shoulder_px = (int(shoulder.x * w), int(shoulder.y * h))
        elbow_px = (int(elbow.x * w), int(elbow.y * h))
        wrist_px = (int(wrist.x * w), int(wrist.y * h))
        
        # Draw elbow angle arc
        self.draw_angle_arc(frame, shoulder_px, elbow_px, wrist_px, current_elbow_angle)
        
        # Draw rep timing indicator if in a rep
        if self.in_rep and self.current_rep_start_time:
            current_duration = time.time() - self.current_rep_start_time
            # Draw a timer box at the top of the frame
            timer_width = int(min(current_duration * 50, w-40))  # Scale timer width by duration
            cv2.rectangle(frame, (20, 20), (20 + timer_width, 40), (0, 255, 0), -1)
            cv2.rectangle(frame, (20, 20), (w-20, 40), (255, 255, 255), 2)
            
            # Display current time
            cv2.putText(frame, f"{current_duration:.1f}s", 
                      (w-100, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Draw form indicator for elbow body alignment
        alignment_status = "GOOD" if elbow_body_angle <= self.ELBOW_BODY_ANGLE_THRESHOLD else "BAD"
        alignment_color = (0, 255, 0) if alignment_status == "GOOD" else (0, 0, 255)
        
        cv2.putText(frame, f"Elbow alignment: {alignment_status}", 
                  (20, h-60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, alignment_color, 2)
                  
        # Draw depth indicator
        if self.in_rep:
            depth_status = "GOOD" if self.min_angle <= self.ELBOW_CONTRACT_THRESHOLD else "TOO SHALLOW"
            depth_color = (0, 255, 0) if depth_status == "GOOD" else (0, 165, 255)
            
            cv2.putText(frame, f"Curl depth: {depth_status}", 
                      (20, h-30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, depth_color, 2)
    
    def draw_angle_arc(self, frame, point1, point2, point3, angle):
        """Draw an arc showing the angle between three points"""
        # Calculate vectors
        vec1 = np.array([point1[0] - point2[0], point1[1] - point2[1]])
        vec2 = np.array([point3[0] - point2[0], point3[1] - point2[1]])
        
        # Normalize vectors
        vec1_norm = vec1 / np.linalg.norm(vec1)
        vec2_norm = vec2 / np.linalg.norm(vec2)
        
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
        
        # Determine color based on angle
        if angle <= self.ELBOW_CONTRACT_THRESHOLD:
            color = (0, 255, 0)  # Green for good curl
        elif angle <= 90:
            color = (0, 165, 255)  # Orange for moderate curl
        else:
            color = (0, 0, 255)  # Red for insufficient curl
            
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
        cv2.putText(frame, "BICEP CURLS", (20, 40), font, 1, (255, 255, 255), 2)
        
        rep_text = f"Reps: {self.rep_count}"
        cv2.putText(frame, rep_text, (w - 150, 40), font, 1, (255, 255, 255), 2)
        
        # Draw feedback message
        cv2.putText(frame, self.last_feedback, (20, 80), font, 0.7, (255, 255, 255), 2)
        
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