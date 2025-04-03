# exercises/lunges.py
import cv2
import mediapipe as mp
import math
import time
import numpy as np
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
                self.current_rep_start_time = current_time
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
                self.current_rep_start_time = None
                
        # Store feedback if it's new
        if feedback:
            self.last_feedback = feedback
            if not feedback.startswith("Waiting"):
                self.feedback_history.append(feedback)
        
        # Draw additional visual cues on the frame
        self.draw_visual_feedback(frame, landmarks, front_side, front_knee_angle, back_knee_angle, torso_angle, knee_over_toes)
        
        # Overlay information on the frame
        self.draw_info_overlay(frame)
                
        return frame, self.last_feedback, self.rep_count, rep_time
    
    def draw_visual_feedback(self, frame, landmarks, front_side, front_knee_angle, back_knee_angle, torso_angle, knee_over_toes):
        """Draw visual feedback elements on the frame"""
        h, w, _ = frame.shape
        
        # Define sides
        if front_side == 'left':
            front_hip = landmarks[self.detector.LEFT_HIP]
            front_knee = landmarks[self.detector.LEFT_KNEE]
            front_ankle = landmarks[self.detector.LEFT_ANKLE]
            front_foot = landmarks[self.detector.LEFT_FOOT_INDEX]
            
            back_hip = landmarks[self.detector.RIGHT_HIP]
            back_knee = landmarks[self.detector.RIGHT_KNEE]
            back_ankle = landmarks[self.detector.RIGHT_ANKLE]
            back_foot = landmarks[self.detector.RIGHT_FOOT_INDEX]
        else:
            front_hip = landmarks[self.detector.RIGHT_HIP]
            front_knee = landmarks[self.detector.RIGHT_KNEE]
            front_ankle = landmarks[self.detector.RIGHT_ANKLE]
            front_foot = landmarks[self.detector.RIGHT_FOOT_INDEX]
            
            back_hip = landmarks[self.detector.LEFT_HIP]
            back_knee = landmarks[self.detector.LEFT_KNEE]
            back_ankle = landmarks[self.detector.LEFT_ANKLE]
            back_foot = landmarks[self.detector.LEFT_FOOT_INDEX]
            
        # Convert normalized coordinates to pixel coordinates
        front_hip_px = (int(front_hip.x * w), int(front_hip.y * h))
        front_knee_px = (int(front_knee.x * w), int(front_knee.y * h))
        front_ankle_px = (int(front_ankle.x * w), int(front_ankle.y * h))
        front_foot_px = (int(front_foot.x * w), int(front_foot.y * h))
        
        back_hip_px = (int(back_hip.x * w), int(back_hip.y * h))
        back_knee_px = (int(back_knee.x * w), int(back_knee.y * h))
        back_ankle_px = (int(back_ankle.x * w), int(back_ankle.y * h))
        back_foot_px = (int(back_foot.x * w), int(back_foot.y * h))
        
        # Draw knee angle arcs
        self.draw_angle_arc(frame, front_hip_px, front_knee_px, front_ankle_px, front_knee_angle, "front_knee")
        self.draw_angle_arc(frame, back_hip_px, back_knee_px, back_ankle_px, back_knee_angle, "back_knee")
        
        # Draw knee alignment indicator for front leg
        if knee_over_toes:
            # Draw an arrow indicating improper alignment
            knee_x, knee_y = front_knee_px
            ankle_x, ankle_y = front_ankle_px
            
            # Draw red vertical line from ankle
            cv2.line(frame, (ankle_x, ankle_y), (ankle_x, knee_y), (0, 0, 255), 2)
            
            # Draw current knee position and its relation to the vertical line
            cv2.circle(frame, (knee_x, knee_y), 5, (0, 0, 255), -1)
            cv2.line(frame, (ankle_x, knee_y), (knee_x, knee_y), (0, 0, 255), 2)
            
            # Add warning text
            cv2.putText(frame, "Knee over toes!", 
                      (ankle_x - 80, knee_y - 15), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Draw torso vertical reference
        self.draw_torso_reference(frame, landmarks, torso_angle)
        
        # Draw rep timing indicator if in a lunge
        if self.in_lunge and self.current_rep_start_time:
            current_duration = time.time() - self.current_rep_start_time
            # Draw a timer box at the top of the frame
            timer_width = int(min(current_duration * 50, w-40))  # Scale timer width by duration
            cv2.rectangle(frame, (20, 20), (20 + timer_width, 40), (0, 255, 0), -1)
            cv2.rectangle(frame, (20, 20), (w-20, 40), (255, 255, 255), 2)
            
            # Display current time
            cv2.putText(frame, f"{current_duration:.1f}s", 
                      (w-100, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Draw form indicators
        # Front knee depth
        front_status = "GOOD" if front_knee_angle <= self.FRONT_KNEE_THRESHOLD else "TOO HIGH"
        front_color = (0, 255, 0) if front_status == "GOOD" else (0, 0, 255)
        
        cv2.putText(frame, f"Front knee: {front_status}", 
                  (20, h-120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, front_color, 2)
                  
        # Back knee depth
        back_status = "GOOD" if back_knee_angle <= self.BACK_KNEE_THRESHOLD else "TOO HIGH"
        back_color = (0, 255, 0) if back_status == "GOOD" else (0, 0, 255)
        
        cv2.putText(frame, f"Back knee: {back_status}", 
                  (20, h-90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, back_color, 2)
                  
        # Knee alignment
        alignment_status = "GOOD" if not knee_over_toes else "IMPROPER"
        alignment_color = (0, 255, 0) if alignment_status == "GOOD" else (0, 0, 255)
        
        cv2.putText(frame, f"Knee alignment: {alignment_status}", 
                  (20, h-60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, alignment_color, 2)
                  
        # Torso posture
        torso_status = "GOOD" if torso_angle <= self.TORSO_VERTICAL_THRESHOLD else "LEANING"
        torso_color = (0, 255, 0) if torso_status == "GOOD" else (0, 0, 255)
        
        cv2.putText(frame, f"Torso posture: {torso_status}", 
                  (20, h-30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, torso_color, 2)
    
    def draw_angle_arc(self, frame, point1, point2, point3, angle, angle_type="front_knee"):
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
        if angle_type == "front_knee":
            if angle <= self.FRONT_KNEE_THRESHOLD:
                color = (0, 255, 0)  # Green for good depth
            else:
                color = (0, 0, 255)  # Red for insufficient depth
        else:  # back knee
            if angle <= self.BACK_KNEE_THRESHOLD:
                color = (0, 255, 0)  # Green for good bend
            else:
                color = (0, 0, 255)  # Red for insufficient bend
            
        # Draw the arc
        cv2.ellipse(frame, point2, (radius, radius), 
                  np.degrees(start_angle), 0, np.degrees(angle_rad), color, 3)
        
        # Add the angle text
        text_angle = start_angle + angle_rad / 2
        text_x = int(point2[0] + (radius + 20) * np.cos(text_angle))
        text_y = int(point2[1] + (radius + 20) * np.sin(text_angle))
        
        cv2.putText(frame, f"{int(angle)}°", (text_x, text_y), 
                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    
    def draw_torso_reference(self, frame, landmarks, torso_angle):
        """Draw a vertical reference to check torso alignment"""
        h, w, _ = frame.shape
        
        # Average shoulders and hips to get torso midpoints
        mid_shoulder_x = (landmarks[self.detector.LEFT_SHOULDER].x + landmarks[self.detector.RIGHT_SHOULDER].x) / 2
        mid_shoulder_y = (landmarks[self.detector.LEFT_SHOULDER].y + landmarks[self.detector.RIGHT_SHOULDER].y) / 2
        
        mid_hip_x = (landmarks[self.detector.LEFT_HIP].x + landmarks[self.detector.RIGHT_HIP].x) / 2
        mid_hip_y = (landmarks[self.detector.LEFT_HIP].y + landmarks[self.detector.RIGHT_HIP].y) / 2
        
        # Convert to pixel coordinates
        mid_shoulder_px = (int(mid_shoulder_x * w), int(mid_shoulder_y * h))
        mid_hip_px = (int(mid_hip_x * w), int(mid_hip_y * h))
        
        # Draw a vertical reference line
        vertical_x = mid_shoulder_px[0]
        vertical_bottom = (vertical_x, mid_hip_px[1])
        
        # Draw dashed vertical reference line
        dash_length = 10
        gap_length = 5
        y_start = mid_shoulder_px[1]
        y_end = mid_hip_px[1]
        
        for y in range(y_start, y_end, dash_length + gap_length):
            y2 = min(y + dash_length, y_end)
            cv2.line(frame, (vertical_x, y), (vertical_x, y2), (255, 255, 255), 1)
        
        # Draw actual torso line
        torso_color = (0, 255, 0) if torso_angle <= self.TORSO_VERTICAL_THRESHOLD else (0, 0, 255)
        cv2.line(frame, mid_shoulder_px, mid_hip_px, torso_color, 2)
        
        # Draw angle text
        cv2.putText(frame, f"{int(torso_angle)}°", 
                  (mid_shoulder_px[0] + 15, mid_shoulder_px[1] + 30), 
                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, torso_color, 2)
        
    def draw_info_overlay(self, frame):
        """Draw general information overlay on the frame"""
        h, w, _ = frame.shape
        
        # Create a semi-transparent overlay for the top info bar
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 100), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        # Draw exercise info and rep count
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(frame, "LUNGES", (20, 40), font, 1, (255, 255, 255), 2)
        
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