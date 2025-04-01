# exercises/pushups.py
import time
from core.pose_detector import PoseDetector

class PushUpTracker:
    EXTENDED_ELBOW_THRESHOLD = 160  # When the arm is fully extended (baseline)
    MIN_DROP = 10                   # Minimal drop to initiate a rep

    def __init__(self, thresholds):
        # thresholds: {"max_elbow_angle": 90, "min_body_line": 160}
        self.detector = PoseDetector()
        self.thresholds = thresholds
        self.rep_count = 0
        self.in_rep = False
        self.baseline = None         # Baseline (extended) elbow angle
        self.min_elbow = None        # Minimum elbow angle reached during rep
        self.improper_flag = False   # True if body alignment gets too low
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
        # Check that necessary landmarks are visible on both sides:
        required = [
            self.detector.NOSE,
            self.detector.LEFT_SHOULDER, self.detector.LEFT_ELBOW, self.detector.LEFT_WRIST,
            self.detector.LEFT_HIP, self.detector.LEFT_ANKLE,
            self.detector.RIGHT_SHOULDER, self.detector.RIGHT_ELBOW, self.detector.RIGHT_WRIST,
            self.detector.RIGHT_HIP, self.detector.RIGHT_ANKLE
        ]
        if not all(landmarks[idx].visibility > 0.5 for idx in required):
            feedback = ""
            if current_time - self.last_wait_time >= 5:
                feedback = "Waiting for user to be fully in frame (complete body required)..."
                self.last_wait_time = current_time
            self.in_rep = False
            return frame, feedback, self.rep_count, 0

        # Helper function to compute arm (elbow) angle.
        def get_arm_angle(side):
            if side == "left":
                shoulder = landmarks[self.detector.LEFT_SHOULDER]
                elbow = landmarks[self.detector.LEFT_ELBOW]
                wrist = landmarks[self.detector.LEFT_WRIST]
            else:
                shoulder = landmarks[self.detector.RIGHT_SHOULDER]
                elbow = landmarks[self.detector.RIGHT_ELBOW]
                wrist = landmarks[self.detector.RIGHT_WRIST]
            return self.detector.calculate_angle(shoulder, elbow, wrist)
        
        # Helper function for body alignment (shoulder-hip-ankle).
        def get_body_line(side):
            if side == "left":
                shoulder = landmarks[self.detector.LEFT_SHOULDER]
                hip = landmarks[self.detector.LEFT_HIP]
                ankle = landmarks[self.detector.LEFT_ANKLE]
            else:
                shoulder = landmarks[self.detector.RIGHT_SHOULDER]
                hip = landmarks[self.detector.RIGHT_HIP]
                ankle = landmarks[self.detector.RIGHT_ANKLE]
            return self.detector.calculate_angle(shoulder, hip, ankle)
        
        left_elbow = get_arm_angle("left")
        right_elbow = get_arm_angle("right")
        current_elbow_angle = (left_elbow + right_elbow) / 2.0

        left_body = get_body_line("left")
        right_body = get_body_line("right")
        body_line = (left_body + right_body) / 2.0

        # Update baseline if fully extended.
        if current_elbow_angle > self.EXTENDED_ELBOW_THRESHOLD:
            self.baseline = current_elbow_angle

        # Begin a rep if not in rep and sufficient drop occurs.
        if not self.in_rep and self.baseline is not None:
            if (self.baseline - current_elbow_angle) >= self.MIN_DROP:
                self.in_rep = True
                self.start_time = current_time
                self.min_elbow = current_elbow_angle
                self.improper_flag = False

        if self.in_rep:
            if current_elbow_angle < self.min_elbow:
                self.min_elbow = current_elbow_angle
            if body_line < self.thresholds["min_body_line"]:
                self.improper_flag = True
            # Rep completion when the arm re-extends.
            if current_elbow_angle > self.EXTENDED_ELBOW_THRESHOLD:
                rep_time = current_time - self.start_time
                contraction = self.baseline - self.min_elbow
                desired_contraction = self.baseline - self.thresholds["max_elbow_angle"]
                feedback = ""
                if contraction < self.MIN_CONTRACTION_REQUIRED:
                    if self.min_elbow > self.WARN_CURL_THRESHOLD:
                        feedback = "Curl higher! Your curl isn't high enough."
                    elif self.min_elbow > self.PROPER_CURL_THRESHOLD:
                        feedback = "Almost there, try curling a bit more."
                    else:
                        feedback = "Adjust your form!"
                if self.improper_flag:
                    if feedback:
                        feedback += " Keep your elbows close to your body!"
                    else:
                        feedback = "Keep your elbows close to your body!"
                if feedback == "":
                    self.rep_count += 1
                self.in_rep = False
                return frame, feedback, self.rep_count, rep_time

        return frame, "", self.rep_count, 0
