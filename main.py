import time
import random
import numpy as np
import cv2
from hand_tracker import HandTracker
from effects import EffectManager
from sound import play_thwip, play_gunshot, play_hit
from object_tracker import MotionTrigger
from enemies import EnemyManager

WINDOW_NAME = "skillweb"
FRAME_W, FRAME_H = 1280, 720
HOLD_TIME = 0.6

BTN_W, BTN_H = 118, 42
BTN_MARGIN = 24
LEFT_ZONE = (BTN_MARGIN, BTN_MARGIN, BTN_MARGIN + BTN_W, BTN_MARGIN + BTN_H)
RIGHT_ZONE = (FRAME_W - BTN_MARGIN - BTN_W, BTN_MARGIN, FRAME_W - BTN_MARGIN, BTN_MARGIN + BTN_H)

SHAKE_DURATION = 0.18
SHAKE_MAGNITUDE = 22
CROSSHAIR_COLOR = (40, 140, 255)


def draw_crosshair(frame, pos):
    cx, cy = pos
    cv2.circle(frame, (cx, cy), 34, CROSSHAIR_COLOR, 2, cv2.LINE_AA)
    cv2.circle(frame, (cx, cy), 3, CROSSHAIR_COLOR, -1, cv2.LINE_AA)
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        x1 = cx + dx * 46
        y1 = cy + dy * 46
        x2 = cx + dx * 60
        y2 = cy + dy * 60
        cv2.line(frame, (x1, y1), (x2, y2), CROSSHAIR_COLOR, 2, cv2.LINE_AA)


def apply_shake(frame, elapsed):
    decay = max(0.0, 1 - elapsed / SHAKE_DURATION)
    offset_x = random.randint(-SHAKE_MAGNITUDE, SHAKE_MAGNITUDE) * decay
    offset_y = random.randint(-SHAKE_MAGNITUDE, SHAKE_MAGNITUDE) * decay
    m = np.float32([[1, 0, offset_x], [0, 1, offset_y]])
    return cv2.warpAffine(frame, m, (FRAME_W, FRAME_H))


def _in_zone(point, zone):
    x, y = point
    x1, y1, x2, y2 = zone
    return x1 <= x <= x2 and y1 <= y <= y2


INACTIVE_BORDER = (110, 110, 110)
INACTIVE_TEXT = (160, 160, 160)


def _pill_border(frame, pt1, pt2, color, thickness):
    x1, y1 = pt1
    x2, y2 = pt2
    r = (y2 - y1) // 2
    cv2.line(frame, (x1 + r, y1), (x2 - r, y1), color, thickness, cv2.LINE_AA)
    cv2.line(frame, (x1 + r, y2), (x2 - r, y2), color, thickness, cv2.LINE_AA)
    cv2.ellipse(frame, (x1 + r, y1 + r), (r, r), 90, 0, 180, color, thickness, cv2.LINE_AA)
    cv2.ellipse(frame, (x2 - r, y1 + r), (r, r), 270, 0, 180, color, thickness, cv2.LINE_AA)


def _pill_fill(frame, pt1, pt2, color):
    x1, y1 = pt1
    x2, y2 = pt2
    r = (y2 - y1) // 2
    cv2.rectangle(frame, (x1 + r, y1), (x2 - r, y2), color, -1)
    cv2.circle(frame, (x1 + r, y1 + r), r, color, -1)
    cv2.circle(frame, (x2 - r, y1 + r), r, color, -1)


def draw_mode_buttons(frame, current_mode, hover_zone, hover_progress):
    _draw_single_button(frame, LEFT_ZONE, "WEB", (255, 255, 255), (0, 0, 0), current_mode == "web", hover_zone == "web", hover_progress)
    _draw_single_button(frame, RIGHT_ZONE, "GUN", (0, 0, 0), (255, 255, 255), current_mode == "gun", hover_zone == "gun", hover_progress)


def _draw_single_button(frame, zone, label, fill_color, text_color, active, hovering, hover_progress):
    x1, y1, x2, y2 = zone

    if active:
        overlay = frame.copy()
        _pill_fill(overlay, (x1, y1), (x2, y2), fill_color)
        cv2.addWeighted(overlay, 0.92, frame, 0.08, 0, frame)
        if fill_color == (0, 0, 0):
            _pill_border(frame, (x1, y1), (x2, y2), (255, 255, 255), 1)
        label_color = text_color
        font_scale = 0.55
    else:
        overlay = frame.copy()
        _pill_fill(overlay, (x1, y1), (x2, y2), (15, 15, 15))
        cv2.addWeighted(overlay, 0.45, frame, 0.55, 0, frame)
        _pill_border(frame, (x1, y1), (x2, y2), INACTIVE_BORDER, 1)
        label_color = INACTIVE_TEXT
        font_scale = 0.52

    text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_DUPLEX, font_scale, 1)[0]
    tx = x1 + (x2 - x1 - text_size[0]) // 2
    ty = y1 + (y2 - y1 + text_size[1]) // 2
    cv2.putText(frame, label, (tx, ty), cv2.FONT_HERSHEY_DUPLEX, font_scale, label_color, 1, cv2.LINE_AA)

    if hovering:
        accent = (255, 255, 255) if not active else (140, 140, 140)
        r = (y2 - y1) // 2
        inner_x1, inner_y1 = x1 + r, y2 - 6
        inner_x2 = inner_x1 + int((x2 - x1 - 2 * r) * hover_progress)
        cv2.line(frame, (inner_x1, inner_y1), (max(inner_x2, inner_x1 + 2), inner_y1), accent, 3, cv2.LINE_AA)


def main():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, FRAME_W, FRAME_H)

    tracker = HandTracker(detection_conf=0.8, tracking_conf=0.7)
    fx = EffectManager()
    motion = MotionTrigger()
    enemies = EnemyManager(FRAME_W, FRAME_H)

    current_mode = "web"
    hover_zone = None
    hover_start = 0
    shake_start = 0
    gun_aim_pos = (FRAME_W // 2, FRAME_H // 2)
    last_fire_point = None
    last_fire_time = 0
    enemy_enabled = True

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        frame = cv2.flip(frame, 1)
        raw_frame = frame.copy()
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        hands = tracker.process(rgb)

        detected_zone = None
        for hand in hands:
            if _in_zone(hand["origin"], LEFT_ZONE):
                detected_zone = "web"
            elif _in_zone(hand["origin"], RIGHT_ZONE):
                detected_zone = "gun"

        now = time.time()
        hover_progress = 0.0
        if detected_zone is not None:
            if hover_zone != detected_zone:
                hover_zone = detected_zone
                hover_start = now
            hover_progress = min(1.0, (now - hover_start) / HOLD_TIME)
            if hover_progress >= 1.0:
                current_mode = detected_zone
                hover_zone = None
        else:
            hover_zone = None

        if current_mode == "web":
            for hand in hands:
                if hand["fire"]:
                    effect_type = hand["state"].next_effect_type()
                    fx.spawn(effect_type, hand["origin"], hand["direction"], hand["toward_camera"])
                    fx.spawn_flash()
                    play_thwip()
        else:
            result = motion.update(raw_frame)
            if result:
                ox, oy = result["origin"]
                gun_aim_pos = (ox, oy)
                cv2.circle(frame, (ox, oy), 5, (40, 140, 255), -1)
                if result["fire"]:
                    fx.spawn_bullet(result["origin"])
                    fx.spawn_flash()
                    play_gunshot()
                    shake_start = time.time()
                    if enemy_enabled:
                        hit = enemies.try_hit(result["origin"])
                        if hit:
                            play_hit()
                    last_fire_point = result["origin"]
                    last_fire_time = time.time()

        fx.update()
        fx.draw(frame, show_web=(current_mode == "web"))

        if current_mode == "gun":
            if enemy_enabled:
                enemies.update()
                enemies.draw(frame)
            hint = "E: enemy ON" if enemy_enabled else "E: enemy OFF"
            hint_color = (50, 50, 235) if enemy_enabled else (140, 140, 140)
            cv2.putText(frame, hint, (20, FRAME_H - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, hint_color, 1, cv2.LINE_AA)

            draw_crosshair(frame, gun_aim_pos)
            if last_fire_point is not None and time.time() - last_fire_time < 0.4:
                fx_, fy_ = last_fire_point
                cv2.line(frame, (fx_ - 14, fy_ - 14), (fx_ + 14, fy_ + 14), (0, 230, 255), 3, cv2.LINE_AA)
                cv2.line(frame, (fx_ - 14, fy_ + 14), (fx_ + 14, fy_ - 14), (0, 230, 255), 3, cv2.LINE_AA)
            elapsed = time.time() - shake_start
            if elapsed < SHAKE_DURATION:
                frame = apply_shake(frame, elapsed)

        draw_mode_buttons(frame, current_mode, hover_zone, hover_progress)

        cv2.imshow(WINDOW_NAME, frame)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), ord('Q')):
            break
        if key in (ord('e'), ord('E')):
            enemy_enabled = not enemy_enabled

    tracker.close()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()