import time
import math
from collections import deque
import cv2

MIN_MOTION_AREA = 1200
FIRE_AREA_FLOOR = 7000
SPIKE_RATIO = 2.8
FIRE_COOLDOWN = 0.4
DIFF_THRESH = 35


class MotionTrigger:
    def __init__(self):
        self.prev_gray = None
        self.area_history = deque(maxlen=12)
        self.last_fire_time = 0

    def update(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (9, 9), 0)

        if self.prev_gray is None:
            self.prev_gray = gray
            return None

        diff = cv2.absdiff(gray, self.prev_gray)
        self.prev_gray = gray

        _, thresh = cv2.threshold(diff, DIFF_THRESH, 255, cv2.THRESH_BINARY)
        thresh = cv2.dilate(thresh, None, iterations=2)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)
        if area < MIN_MOTION_AREA:
            return None

        M = cv2.moments(largest)
        if M["m00"] == 0:
            return None

        cx = M["m10"] / M["m00"]
        cy = M["m01"] / M["m00"]

        baseline = sum(self.area_history) / len(self.area_history) if self.area_history else area
        self.area_history.append(area)

        now = time.time()
        fire = False
        spike_thresh = max(FIRE_AREA_FLOOR, baseline * SPIKE_RATIO)
        if area > spike_thresh and (now - self.last_fire_time) > FIRE_COOLDOWN:
            fire = True
            self.last_fire_time = now

        return {
            "origin": (int(cx), int(cy)),
            "fire": fire,
            "area": area,
        }