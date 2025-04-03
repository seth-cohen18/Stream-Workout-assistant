# core/pose_detector.py
import cv2
import mediapipe as mp
import math
import numpy as np

class PoseDetector:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            model_complexity=1  # Use 1 for balance of speed and accuracy
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # Define pose landmarks for easier access
        self.LEFT_SHOULDER = self.mp_pose.PoseLandmark.LEFT_SHOULDER.value
        self.LEFT_HIP = self.mp_pose.PoseLandmark.LEFT_HIP.value
        self.LEFT_KNEE = self.mp_pose.PoseLandmark.LEFT_KNEE.value
        self.LEFT_ANKLE = self.mp_pose.PoseLandmark.LEFT_ANKLE.value
        self.LEFT_ELBOW = self.mp_pose.PoseLandmark.LEFT_ELBOW.value
        self.LEFT_WRIST = self.mp_pose.PoseLandmark.LEFT_WRIST.value
        self.LEFT_FOOT_INDEX = self.mp_pose.PoseLandmark.LEFT_FOOT_INDEX.value
        
        self.RIGHT_SHOULDER = self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value
        self.RIGHT_HIP = self.mp_pose.PoseLandmark.RIGHT_HIP.value
        self.RIGHT_KNEE = self.mp_pose.PoseLandmark.RIGHT_KNEE.value
        self.RIGHT_ANKLE = self.mp_pose.PoseLandmark.RIGHT_ANKLE.value
        self.RIGHT_ELBOW = self.mp_pose.PoseLandmark.RIGHT_ELBOW.value
        self.RIGHT_WRIST = self.mp_pose.PoseLandmark.RIGHT_WRIST.value
        self.RIGHT_FOOT_INDEX = self.mp_pose.PoseLandmark.RIGHT_FOOT_INDEX.value
        
        self.NOSE = self.mp_pose.PoseLandmark.NOSE.value

    def process_frame(self, frame):
        """Process a frame and detect pose landmarks."""
        if frame is None or frame.size == 0:
            return None
        
        # Convert the BGR image to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # To improve performance, mark the image as not writeable
        rgb_frame.flags.writeable = False
        
        # Process the frame and detect the pose
        results = self.pose.process(rgb_frame)
        
        # Make the image writeable again for drawing
        rgb_frame.flags.writeable = True
        
        # Draw the pose landmarks on the frame if landmarks detected
        if results.pose_landmarks:
            self.mp_drawing.draw_landmarks(
                frame, 
                results.pose_landmarks, 
                self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style()
            )
            
        return results

    @staticmethod
    def calculate_angle(a, b, c):
        """
        Calculate the angle between three points a, b, c.
        The angle is calculated in degrees between the lines ab and bc.
        """
        a_x, a_y = a.x, a.y
        b_x, b_y = b.x, b.y
        c_x, c_y = c.x, c.y
        
        radians = math.atan2(c_y - b_y, c_x - b_x) - math.atan2(a_y - b_y, a_x - b_x)
        angle = abs(radians * 180.0 / math.pi)
        
        if angle > 180:
            angle = 360 - angle
            
        return angle

    @staticmethod
    def check_alignment(a, b, c):
        """
        Check if the points a, b, c are roughly in a straight line.
        Returns True if the angle is greater than 160 degrees (nearly straight).
        """
        angle = PoseDetector.calculate_angle(a, b, c)
        return angle > 160