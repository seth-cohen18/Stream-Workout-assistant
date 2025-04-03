# exercises/pushups.py
import cv2
import mediapipe as mp
import math
import time
import numpy as np
from collections import defaultdict
from core.pose_detector import PoseDetector

class PushUpTracker:
    # Constants based on scientific measurements for proper form
    EXTENDED_ELBOW_THRESHOLD = 160  # Fully extended elbow angle
    PROPER_ELBOW_THRESHOLD = 90     # Elbow should bend to at least 90° or less
    MIN_ELBOW_DROP = 15             # Minimal elbow angle drop to start rep
    MIN_BODY_LINE = 160             # Body should remain straight (>160°)
    
    def __init__(self, thresholds=None):
        self.detector = PoseDetector()
        self.thresholds = thresholds or {"max_elbow_angle": 90, "min_body_line": 160}
        self.rep_count = 0
        self.in_pushup = False
        self.baseline_elbow = None          # Baseline elbow angle when arms extended
        self.lowest_elbow_angle = None      # Lowest elbow angle during rep
        self.improper_body_line_flag = False  # Flag for improper body alignment
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
            self.detector.NOSE,
            self.detector.LEFT_SHOULDER, self.detector.LEFT_ELBOW, self.detector.LEFT_WRIST,
            self.detector.LEFT_HIP, self.detector.LEFT_ANKLE,
            self.detector.RIGHT_SHOULDER, self.detector.RIGHT_ELBOW, self.detector.RIGHT_WRIST,
            self.detector.RIGHT_HIP, self.detector.RIGHT_ANKLE
        ]
        
        if not all(landmarks[idx].visibility > 0.5 for idx in required):
            feedback = "Waiting for user... (full body required)"
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
        
        # Check body alignment (should be straight line from head to heels)
        left_body_line = self.detector.calculate_angle(
            landmarks[self.detector.LEFT_SHOULDER],
            landmarks[self.detector.LEFT_HIP],
            landmarks[self.detector.LEFT_ANKLE]
        )
        
        right_body_line = self.detector.calculate_angle(
            landmarks[self.detector.RIGHT_SHOULDER],
            landmarks[self.detector.RIGHT_HIP],
            landmarks[self.detector.RIGHT_ANKLE]
        )
        
        body_line_angle = (left_body_line + right_body_line) / 2
        
        # Update baseline when arms fully extended
        if current_elbow_angle > self.EXTENDED_ELBOW_THRESHOLD:
            self.baseline_elbow = current_elbow_angle
            
        # Rep Attempt Initiation
        if not self.in_pushup and self.baseline_elbow is not None and (self.baseline_elbow - current_elbow_angle) > self.MIN_ELBOW_DROP:
            self.in_pushup = True
            self.start_time = current_time
            self.current_rep_start_time = current_time
            self.lowest_elbow_angle = current_elbow_angle
            self.improper_body_line_flag = False
            
        feedback = ""
        rep_time = 0
        
        # During the push-up
        if self.in_pushup:
            # Update lowest elbow angle
            if current_elbow_angle < self.lowest_elbow_angle:
                self.lowest_elbow_angle = current_elbow_angle
                
            # Check for improper body alignment
            if body_line_angle < self.MIN_BODY_LINE:
                self.improper_body_line_flag = True
                
            # Rep Completion Check
            if current_elbow_angle > self.EXTENDED_ELBOW_THRESHOLD:
                rep_time = current_time - self.start_time
                
                issues = []
                
                # Check depth
                if self.lowest_elbow_angle > self.PROPER_ELBOW_THRESHOLD:
                    issues.append("Lower chest closer to ground!")
                    
                # Check body alignment
                if self.improper_body_line_flag:
                    issues.append("Keep body in straight line!")
                    
                if issues:
                    feedback = " ".join(issues)
                else:
                    self.rep_count += 1
                    rounded_time = round(rep_time * 2) / 2
                    self.rep_time_intervals[rounded_time] += 1
                    self.rep_times.append(rep_time)
                    
                # Reset for next rep
                self.in_pushup = False
                self.lowest_elbow_angle = None
                self.current_rep_start_time = None
                
        # Store feedback if it's new
        if feedback:
            self.last_feedback = feedback
            if not feedback.startswith("Waiting"):
                self.feedback_history.append(feedback)
        
        # Draw additional visual cues on the frame
        self.draw_visual_feedback(frame, landmarks, current_elbow_angle, body_line_angle)
        
        # Overlay information on the frame
        self.draw_info_overlay(frame)
        
        return frame, self.last_feedback, self.rep_count, rep_time
        
    def draw_visual_feedback(self, frame, landmarks, elbow_angle, body_line_angle):
        """Draw visual feedback elements on the frame"""
        h, w, _ = frame.shape
        
        # Get key coordinates
        left_shoulder = landmarks[self.detector.LEFT_SHOULDER]
        left_elbow = landmarks[self.detector.LEFT_ELBOW]
        left_wrist = landmarks[self.detector.LEFT_WRIST]
        left_hip = landmarks[self.detector.LEFT_HIP]
        left_ankle = landmarks[self.detector.LEFT_ANKLE]
        
        right_shoulder = landmarks[self.detector.RIGHT_SHOULDER]
        right_elbow = landmarks[self.detector.RIGHT_ELBOW]
        right_wrist = landmarks[self.detector.RIGHT_WRIST]
        right_hip = landmarks[self.detector.RIGHT_HIP]
        right_ankle = landmarks[self.detector.RIGHT_ANKLE]
        
        # Convert normalized coordinates to pixel coordinates for drawing
        left_shoulder_px = (int(left_shoulder.x * w), int(left_shoulder.y * h))
        left_elbow_px = (int(left_elbow.x * w), int(left_elbow.y * h))
        left_wrist_px = (int(left_wrist.x * w), int(left_wrist.y * h))
        left_hip_px = (int(left_hip.x * w), int(left_hip.y * h))
        left_ankle_px = (int(left_ankle.x * w), int(left_ankle.y * h))
        
        right_shoulder_px = (int(right_shoulder.x * w), int(right_shoulder.y * h))
        right_elbow_px = (int(right_elbow.x * w), int(right_elbow.y * h))
        right_wrist_px = (int(right_wrist.x * w), int(right_wrist.y * h))
        right_hip_px = (int(right_hip.x * w), int(right_hip.y * h))
        right_ankle_px = (int(right_ankle.x * w), int(right_ankle.y * h))
        
        # Draw elbow angle arcs
        left_elbow_angle = self.detector.calculate_angle(left_shoulder, left_elbow, left_wrist)
        right_elbow_angle = self.detector.calculate_angle(right_shoulder, right_elbow, right_wrist)
        
        self.draw_angle_arc(frame, left_shoulder_px, left_elbow_px, left_wrist_px, left_elbow_angle, "elbow")
        self.draw_angle_arc(frame, right_shoulder_px, right_elbow_px, right_wrist_px, right_elbow_angle, "elbow")
        
        # Draw body line angles
        left_body_angle = self.detector.calculate_angle(left_shoulder, left_hip, left_ankle)
        right_body_angle = self.detector.calculate_angle(right_shoulder, right_hip, right_ankle)
        
        self.draw_angle_arc(frame, left_shoulder_px, left_hip_px, left_ankle_px, left_body_angle, "body")
        self.draw_angle_arc(frame, right_shoulder_px, right_hip_px, right_ankle_px, right_body_angle, "body")
        
        # Draw rep timing indicator if in a push-up
        if self.in_pushup and self.current_rep_start_time:
            current_duration = time.time() - self.current_rep_start_time
            # Draw a timer box at the top of the frame
            timer_width = int(min(current_duration * 50, w-40))  # Scale timer width by duration
            cv2.rectangle(frame, (20, 20), (20 + timer_width, 40), (0, 255, 0), -1)
            cv2.rectangle(frame, (20, 20), (w-20, 40), (255, 255, 255), 2)
            
            # Display current time
            cv2.putText(frame, f"{current_duration:.1f}s", 
                      (w-100, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Draw form indicators
        # Elbow depth indicator
        depth_status = "GOOD" if elbow_angle <= self.PROPER_ELBOW_THRESHOLD else "TOO HIGH"
        depth_color = (0, 255, 0) if depth_status == "GOOD" else (0, 0, 255)
        
        cv2.putText(frame, f"Push-up depth: {depth_status}", 
                  (20, h-60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, depth_color, 2)
                  
        # Body alignment indicator
        alignment_status = "GOOD" if body_line_angle >= self.MIN_BODY_LINE else "IMPROPER"
        alignment_color = (0, 255, 0) if alignment_status == "GOOD" else (0, 0, 255)
        
        cv2.putText(frame, f"Body alignment: {alignment_status}", 
                  (20, h-30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, alignment_color, 2)
    
    def draw_angle_arc(self, frame, point1, point2, point3, angle, angle_type="elbow"):
        """Draw an arc showing the angle between three points"""
        # Calculate vectors
        vec1 = np.array([point1[0] - point2[0], point1[1] - point2[1]])
        vec2 = np.array([point3[0] - point2[0], point3[1] - point2[1]])
        
        # Normalize vectors
        vec1_norm = vec1 / (np.linalg.norm(vec1) + 1e-6)  # Add small epsilon to avoid division by zero
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
        
        # Determine color based on angle and what we're measuring
        if angle_type == "elbow":
            if angle <= self.PROPER_ELBOW_THRESHOLD:
                color = (0, 255, 0)  # Green for good depth
            elif angle <= 120:
                color = (0, 165, 255)  # Orange for moderate depth
            else:
                color = (0, 0, 255)  # Red for insufficient depth
        else:  # body line
            if angle >= self.MIN_BODY_LINE:
                color = (0, 255, 0)  # Green for good body alignment
            else:
                color = (0, 0, 255)  # Red for poor body alignment
            
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
        cv2.putText(frame, "PUSH-UPS", (20, 40), font, 1, (255, 255, 255), 2)
        
        rep_text = f"Reps: {self.rep_count}"
        cv2.putText(frame, rep_text, (w - 150, 40), font, 1, (255, 255, 255), 2)
        
        # Draw feedback message
        cv2.putText(frame, self.last_feedback, (20, 80), font, 0.7, (255, 255, 255), 2)
        
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