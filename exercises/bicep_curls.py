# exercises/bicep_curls.py
import time
from core.pose_detector import PoseDetector

class BicepCurlTracker:
    EXTENDED_THRESHOLD = 160    # Fully extended angle.
    MIN_DROP = 5                # Minimal drop to start rep.
    MIN_CONTRACTION_REQUIRED = 15  # Required contraction amount.
    WARN_CURL_THRESHOLD = 35    # If min angle > 35°, prompt to curl higher.
    PROPER_CURL_THRESHOLD = 30  # If min angle > 30 and <=35, prompt "Almost there".
    BODY_ANGLE_LIMIT = 15       # Elbow-to-body must be less than 15°.

    def __init__(self):
        self.detector = PoseDetector()
        self.rep_count = 0
        self.in_rep = False
        self.baseline = None
        self.min_angle = None
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
        required = [
            self.detector.LEFT_SHOULDER, self.detector.LEFT_ELBOW,
            self.detector.LEFT_WRIST, self.detector.LEFT_HIP,
            self.detector.RIGHT_SHOULDER, self.detector.RIGHT_ELBOW,
            self.detector.RIGHT_WRIST, self.detector.RIGHT_HIP
        ]
        if not all(landmarks[idx].visibility > 0.5 for idx in required):
            feedback = ""
            if current_time - self.last_wait_time >= 5:
                feedback = "Waiting for user to be fully in frame (arms must be visible)..."
                self.last_wait_time = current_time
            self.in_rep = False
            return frame, feedback, self.rep_count, 0

        # Define helper to compute side’s angles.
        def compute_side(side):
            if side == "left":
                shoulder = landmarks[self.detector.LEFT_SHOULDER]
                elbow = landmarks[self.detector.LEFT_ELBOW]
                wrist = landmarks[self.detector.LEFT_WRIST]
                hip = landmarks[self.detector.LEFT_HIP]
            else:
                shoulder = landmarks[self.detector.RIGHT_SHOULDER]
                elbow = landmarks[self.detector.RIGHT_ELBOW]
                wrist = landmarks[self.detector.RIGHT_WRIST]
                hip = landmarks[self.detector.RIGHT_HIP]
            curl_angle = self.detector.calculate_angle(shoulder, elbow, wrist)
            body_angle = self.detector.calculate_angle(hip, shoulder, elbow)
            return curl_angle, body_angle

        left_visible = all(landmarks[idx].visibility > 0.5 for idx in 
                             [self.detector.LEFT_SHOULDER, self.detector.LEFT_ELBOW, self.detector.LEFT_WRIST, self.detector.LEFT_HIP])
        right_visible = all(landmarks[idx].visibility > 0.5 for idx in 
                              [self.detector.RIGHT_SHOULDER, self.detector.RIGHT_ELBOW, self.detector.RIGHT_WRIST, self.detector.RIGHT_HIP])
        if left_visible and right_visible:
            left_curl, left_body = compute_side("left")
            right_curl, right_body = compute_side("right")
            current_curl = (left_curl + right_curl) / 2.0
            body_angle = (left_body + right_body) / 2.0
        elif left_visible:
            current_curl, body_angle = compute_side("left")
        elif right_visible:
            current_curl, body_angle = compute_side("right")
        else:
            feedback = ""
            if current_time - self.last_wait_time >= 5:
                feedback = "Waiting for user to be fully in frame (arms must be visible)..."
                self.last_wait_time = current_time
            self.in_rep = False
            return frame, feedback, self.rep_count, 0

        if current_curl > self.EXTENDED_THRESHOLD:
            self.baseline = current_curl

        if not self.in_rep and self.baseline is not None:
            if (self.baseline - current_curl) >= self.MIN_DROP:
                self.in_rep = True
                self.start_time = current_time
                self.min_angle = current_curl
                self.improper_flag = False

        if self.in_rep:
            if current_curl < self.min_angle:
                self.min_angle = current_curl
            if body_angle >= self.BODY_ANGLE_LIMIT:
                self.improper_flag = True
            if current_curl > self.EXTENDED_THRESHOLD:
                rep_time = current_time - self.start_time
                contraction = self.baseline - self.min_angle
                feedback = ""
                if contraction < self.MIN_CONTRACTION_REQUIRED:
                    if self.min_angle > self.WARN_CURL_THRESHOLD:
                        feedback = "Curl higher! Your curl isn't high enough."
                    elif self.min_angle > self.PROPER_CURL_THRESHOLD:
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
