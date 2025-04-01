# exercises/squats.py
import time
from core.pose_detector import PoseDetector

class SquatTracker:
    EXTENDED_KNEE_THRESHOLD = 160
    
    def __init__(self, thresholds):
        # thresholds: {"max_knee_angle": 90, "min_back_angle": 35}
        self.detector = PoseDetector()
        self.thresholds = thresholds
        self.rep_count = 0
        self.in_rep = False
        self.baseline = None
        self.min_knee = None
        self.improper_flag = False
        self.start_time = None
        self.last_wait_time = 0

    def track(self, frame):
        results = self.detector.process_frame(frame)
        current_time = time.time()
        if not (results and results.pose_landmarks):
            feedback = ""
            if current_time - self.last_wait_time >= 5:
                feedback = "Waiting for user to be fully in frame..."
                self.last_wait_time = current_time
            self.in_rep = False
            return frame, feedback, self.rep_count, 0

        landmarks = results.pose_landmarks.landmark
        required = [self.detector.LEFT_SHOULDER, self.detector.LEFT_HIP,
                    self.detector.LEFT_KNEE, self.detector.LEFT_ANKLE]
        if not all(landmarks[idx].visibility > 0.5 for idx in required):
            feedback = ""
            if current_time - self.last_wait_time >= 5:
                feedback = "Waiting for user to be fully in frame (shoulder to feet)..."
                self.last_wait_time = current_time
            self.in_rep = False
            return frame, feedback, self.rep_count, 0

        shoulder = landmarks[self.detector.LEFT_SHOULDER]
        hip = landmarks[self.detector.LEFT_HIP]
        knee = landmarks[self.detector.LEFT_KNEE]
        ankle = landmarks[self.detector.LEFT_ANKLE]

        knee_angle = self.detector.calculate_angle(hip, knee, ankle)
        back_angle = self.detector.calculate_angle(shoulder, hip, knee)

        if knee_angle > self.EXTENDED_KNEE_THRESHOLD:
            self.baseline = knee_angle

        if not self.in_rep and self.baseline is not None:
            if (self.baseline - knee_angle) >= (self.baseline - self.thresholds["max_knee_angle"]):
                self.in_rep = True
                self.start_time = current_time
                self.min_knee = knee_angle
                self.improper_flag = False

        if self.in_rep:
            if knee_angle < self.min_knee:
                self.min_knee = knee_angle
            if back_angle < self.thresholds["min_back_angle"]:
                self.improper_flag = True
            if knee_angle > self.EXTENDED_KNEE_THRESHOLD:
                rep_time = current_time - self.start_time
                contraction = self.baseline - self.min_knee
                desired_contraction = self.baseline - self.thresholds["max_knee_angle"]
                feedback = ""
                if contraction < desired_contraction:
                    feedback = "Squat deeper! Lower your hips further."
                if self.improper_flag:
                    if feedback:
                        feedback += " Keep your back straighter!"
                    else:
                        feedback = "Keep your back straighter!"
                if feedback == "":
                    self.rep_count += 1
                self.in_rep = False
                return frame, feedback, self.rep_count, rep_time

        return frame, "", self.rep_count, 0
