# core/pose_detector.py
import cv2
import mediapipe as mp
import math

class PoseDetector:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(min_detection_confidence=0.5,
                                      min_tracking_confidence=0.5)
        self.mp_drawing = mp.solutions.drawing_utils
        self.LEFT_SHOULDER = self.mp_pose.PoseLandmark.LEFT_SHOULDER.value
        self.LEFT_HIP = self.mp_pose.PoseLandmark.LEFT_HIP.value
        self.LEFT_KNEE = self.mp_pose.PoseLandmark.LEFT_KNEE.value
        self.LEFT_ANKLE = self.mp_pose.PoseLandmark.LEFT_ANKLE.value
        self.LEFT_ELBOW = self.mp_pose.PoseLandmark.LEFT_ELBOW.value
        self.LEFT_WRIST = self.mp_pose.PoseLandmark.LEFT_WRIST.value
        self.RIGHT_SHOULDER = self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value
        self.RIGHT_HIP = self.mp_pose.PoseLandmark.RIGHT_HIP.value
        self.RIGHT_KNEE = self.mp_pose.PoseLandmark.RIGHT_KNEE.value
        self.RIGHT_ANKLE = self.mp_pose.PoseLandmark.RIGHT_ANKLE.value
        self.RIGHT_ELBOW = self.mp_pose.PoseLandmark.RIGHT_ELBOW.value
        self.RIGHT_WRIST = self.mp_pose.PoseLandmark.RIGHT_WRIST.value
        self.NOSE = self.mp_pose.PoseLandmark.NOSE.value

    def process_frame(self, frame):
        if frame is None or frame.size == 0:
            return None
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb_frame)
        if results.pose_landmarks:
            self.mp_drawing.draw_landmarks(frame, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)
        return results

    @staticmethod
    def calculate_angle(a, b, c):
        radians = math.atan2(c.y - b.y, c.x - b.x) - math.atan2(a.y - b.y, a.x - b.x)
        angle = abs(radians * 180.0 / math.pi)
        if angle > 180:
            angle = 360 - angle
        return angle

    @staticmethod
    def check_alignment(a, b, c):
        angle = PoseDetector.calculate_angle(a, b, c)
        return angle > 160
