import math
import time
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

WRIST = 0
THUMB_TIP, THUMB_IP, THUMB_MCP = 4, 3, 2
INDEX_TIP, INDEX_PIP, INDEX_MCP = 8, 6, 5
MIDDLE_TIP, MIDDLE_PIP, MIDDLE_MCP = 12, 10, 9
RING_TIP, RING_PIP, RING_MCP = 16, 14, 13
PINKY_TIP, PINKY_PIP, PINKY_MCP = 20, 18, 17

DOUBLE_TAP_WINDOW = 0.5
GESTURE_COOLDOWN = 0.15
MODEL_PATH = "hand_landmarker.task"


class HandState:
    def __init__(self, label):
        self.label = label
        self.shot_cycle = 0
        self.is_gesturing = False
        self.last_gesture_time = 0
        self.pending_tap = False
        self.last_fire_time = 0

    def register_gesture_frame(self, gesturing):
        now = time.time()

        if gesturing and not self.is_gesturing:
            if self.pending_tap and (now - self.last_gesture_time) < DOUBLE_TAP_WINDOW:
                self.pending_tap = False
                self.last_fire_time = now
                self.is_gesturing = True
                self.last_gesture_time = now
                return True
            else:
                self.pending_tap = True
                self.last_gesture_time = now

        if not gesturing and self.is_gesturing:
            self.is_gesturing = False

        if self.pending_tap and (now - self.last_gesture_time) > DOUBLE_TAP_WINDOW:
            self.pending_tap = False

        return False

    def next_effect_type(self):
        effect = ["particle", "particle", "static", "stuck"][self.shot_cycle]
        self.shot_cycle = (self.shot_cycle + 1) % 4
        return effect


def _dist(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def _is_extended(landmarks, tip_idx, pip_idx, mcp_idx, wrist_idx=WRIST):
    wrist = landmarks[wrist_idx]
    d_tip = _dist(wrist, landmarks[tip_idx])
    d_pip = _dist(wrist, landmarks[pip_idx])
    d_mcp = _dist(wrist, landmarks[mcp_idx])
    return d_tip > d_pip * 1.05 > d_mcp * 1.05


def is_web_shooter_gesture(landmarks):
    thumb_ext = _is_extended(landmarks, THUMB_TIP, THUMB_IP, THUMB_MCP)
    index_ext = _is_extended(landmarks, INDEX_TIP, INDEX_PIP, INDEX_MCP)
    pinky_ext = _is_extended(landmarks, PINKY_TIP, PINKY_PIP, PINKY_MCP)
    middle_ext = _is_extended(landmarks, MIDDLE_TIP, MIDDLE_PIP, MIDDLE_MCP)
    ring_ext = _is_extended(landmarks, RING_TIP, RING_PIP, RING_MCP)

    return thumb_ext and index_ext and pinky_ext and not middle_ext and not ring_ext


def get_shoot_direction(landmarks, frame_w, frame_h):
    wrist = landmarks[WRIST]
    index_tip = landmarks[INDEX_TIP]

    dx = index_tip.x - wrist.x
    dy = index_tip.y - wrist.y
    mag = math.hypot(dx, dy)
    if mag < 1e-6:
        dx, dy = 0, -1
    else:
        dx, dy = dx / mag, dy / mag

    hand_span_x = _dist(landmarks[THUMB_TIP], landmarks[PINKY_TIP])
    hand_span_y = _dist(landmarks[WRIST], landmarks[MIDDLE_MCP])

    toward_camera = hand_span_x < hand_span_y * 0.55

    return dx, dy, toward_camera


def get_shoot_origin(landmarks, frame_w, frame_h):
    tip = landmarks[INDEX_TIP]
    return int(tip.x * frame_w), int(tip.y * frame_h)


class HandTracker:
    def __init__(self, max_hands=2, detection_conf=0.8, tracking_conf=0.7, model_path=MODEL_PATH):
        base_options = mp_python.BaseOptions(model_asset_path=model_path)
        options = mp_vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=max_hands,
            min_hand_detection_confidence=detection_conf,
            min_tracking_confidence=tracking_conf,
            running_mode=mp_vision.RunningMode.VIDEO,
        )
        self.detector = mp_vision.HandLandmarker.create_from_options(options)
        self.states = {"Left": HandState("Left"), "Right": HandState("Right")}
        self.start_time = time.time()

    def process(self, frame_rgb):
        h, w = frame_rgb.shape[:2]
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        timestamp_ms = int((time.time() - self.start_time) * 1000)
        result = self.detector.detect_for_video(mp_image, timestamp_ms)

        out = []
        if not result.hand_landmarks:
            return out

        for landmarks, handedness in zip(result.hand_landmarks, result.handedness):
            label = handedness[0].category_name

            gesturing = is_web_shooter_gesture(landmarks)
            state = self.states[label]
            fire = state.register_gesture_frame(gesturing)

            dx, dy, toward_camera = get_shoot_direction(landmarks, w, h)
            origin = get_shoot_origin(landmarks, w, h)

            out.append({
                "label": label,
                "landmarks": landmarks,
                "gesturing": gesturing,
                "fire": fire,
                "direction": (dx, dy),
                "toward_camera": toward_camera,
                "origin": origin,
                "state": state,
            })

        return out

    def close(self):
        self.detector.close()