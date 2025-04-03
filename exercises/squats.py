# exercises/squats.py
import cv2
import mediapipe as mp
import math
import time
import numpy as np
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
            side = "left"
        else:
            shoulder = landmarks[self.detector.RIGHT_SHOULDER]
            hip = landmarks[self.detector.RIGHT_HIP]
            knee = landmarks[self.detector.RIGHT_KNEE]
            ankle = landmarks[self.detector.RIGHT_ANKLE]
            foot = landmarks[self.detector.RIGHT_FOOT_INDEX]
            side = "right"

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
            self.current_rep_start_time = current_time
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
                self.current_rep_start_time = None
                
        # Store feedback if it's new
        if feedback:
            self.last_feedback = feedback
            if not feedback.startswith("Waiting"):
                self.feedback_history.append(feedback)
        
        # Draw additional visual cues on the frame
        self.draw_visual_feedback(frame, landmarks, current_knee_angle, current_back_angle, side)
        
        # Overlay information on the frame
        self.draw_info_overlay(frame)
        
        return frame, self.last_feedback, self.rep_count, rep_time
    
    def draw_visual_feedback(self, frame, landmarks, knee_angle, back_angle, side):
        """Draw visual feedback elements on the frame"""
        h, w, _ = frame.shape
        
        # Get key coordinates
        if side == "left":
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
            
        # Convert normalized coordinates to pixel coordinates
        shoulder_px = (int(shoulder.x * w), int(shoulder.y * h))
        hip_px = (int(hip.x * w), int(hip.y * h))
        knee_px = (int(knee.x * w), int(knee.y * h))
        ankle_px = (int(ankle.x * w), int(ankle.y * h))
        foot_px = (int(foot.x * w), int(foot.y * h))
        
        # Draw knee angle arc
        self.draw_angle_arc(frame, hip_px, knee_px, ankle_px, knee_angle)
        
        # Draw back angle arc
        self.draw_angle_arc(frame, shoulder_px, hip_px, knee_px, back_angle, color_mode="back")
        
        # Draw rep timing indicator if in a squat
        if self.in_squat and self.current_rep_start_time:
            current_duration = time.time() - self.current_rep_start_time
            # Draw a timer box at the top of the frame
            timer_width = int(min(current_duration * 50, w-40))  # Scale timer width by duration
            cv2.rectangle(frame, (20, 20), (20 + timer_width, 40), (0, 255, 0), -1)
            cv2.rectangle(frame, (20, 20), (w-20, 40), (255, 255, 255), 2)
            
            # Display current time
            cv2.putText(frame, f"{current_duration:.1f}s", 
                      (w-100, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Draw form indicators
        # Knee depth indicator
        depth_status = "GOOD" if knee_angle <= self.SQUAT_THRESHOLD else "TOO HIGH"
        depth_color = (0, 255, 0) if depth_status == "GOOD" else (0, 0, 255)
        
        cv2.putText(frame, f"Squat depth: {depth_status}", 
                  (20, h-90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, depth_color, 2)
                  
        # Back posture indicator
        back_status = "GOOD" if back_angle >= self.BACK_THRESHOLD else "TOO BENT"
        back_color = (0, 255, 0) if back_status == "GOOD" else (0, 0, 255)
        
        cv2.putText(frame, f"Back posture: {back_status}", 
                  (20, h-60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, back_color, 2)
                  
        # Feet position indicator
        feet_status = "GOOD" if foot.y >= ankle.y - self.FOOT_THRESHOLD else "HEELS RAISED"
        feet_color = (0, 255, 0) if feet_status == "GOOD" else (0, 165, 255)
        
        cv2.putText(frame, f"Feet position: {feet_status}", 
                  (20, h-30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, feet_color, 2)
    
    def draw_angle_arc(self, frame, point1, point2, point3, angle, color_mode="knee"):
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
        
        # Determine color based on angle and what we're measuring
        if color_mode == "knee":
            if angle <= self.SQUAT_THRESHOLD:
                color = (0, 255, 0)  # Green for good squat depth
            elif angle <= 120:
                color = (0, 165, 255)  # Orange for moderate depth
            else:
                color = (0, 0, 255)  # Red for insufficient depth
        else:  # back angle
            if angle >= self.BACK_THRESHOLD:
                color = (0, 255, 0)  # Green for good back posture
            else:
                color = (0, 0, 255)  # Red for poor back posture
            
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
        cv2.putText(frame, "SQUATS", (20, 40), font, 1, (255, 255, 255), 2)
        
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