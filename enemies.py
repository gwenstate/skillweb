import random
import math
import time
import cv2

ENEMY_COLOR = (50, 50, 235)
ENEMY_RADIUS = 65
SPAWN_MARGIN_X = 160
SPAWN_MARGIN_TOP = 100
SPAWN_MARGIN_BOTTOM = 100


class Enemy:
    def __init__(self, x, y, radius=ENEMY_RADIUS):
        self.x = x
        self.y = y
        self.radius = radius
        self.spawn_time = time.time()

    def draw(self, frame):
        pulse = 1 + 0.06 * math.sin((time.time() - self.spawn_time) * 4)
        r = int(self.radius * pulse)

        cv2.circle(frame, (self.x, self.y), r, ENEMY_COLOR, 3, cv2.LINE_AA)
        cv2.circle(frame, (self.x, self.y), int(r * 0.55), ENEMY_COLOR, 2, cv2.LINE_AA)
        cv2.circle(frame, (self.x, self.y), 4, ENEMY_COLOR, -1, cv2.LINE_AA)

        for ang_deg in (45, 135, 225, 315):
            a = math.radians(ang_deg)
            ix = self.x + math.cos(a) * r * 0.7
            iy = self.y + math.sin(a) * r * 0.7
            ex = self.x + math.cos(a) * r * 1.25
            ey = self.y + math.sin(a) * r * 1.25
            cv2.line(frame, (int(ix), int(iy)), (int(ex), int(ey)), ENEMY_COLOR, 2, cv2.LINE_AA)

    def hit_test(self, point):
        return math.hypot(point[0] - self.x, point[1] - self.y) <= self.radius


class KillEffect:
    def __init__(self, x, y, duration=0.35):
        self.x = x
        self.y = y
        self.duration = duration
        self.spawn_time = time.time()
        self.angles = [random.uniform(0, 2 * math.pi) for _ in range(10)]
        self.speeds = [random.uniform(140, 260) for _ in range(10)]

    def alive(self):
        return time.time() - self.spawn_time < self.duration

    def draw(self, frame):
        t = (time.time() - self.spawn_time) / self.duration
        alpha = max(0.0, 1 - t)
        color = tuple(int(c * alpha) for c in ENEMY_COLOR)

        for a, s in zip(self.angles, self.speeds):
            dist = s * t
            x1 = self.x + math.cos(a) * dist * 0.5
            y1 = self.y + math.sin(a) * dist * 0.5
            x2 = self.x + math.cos(a) * dist
            y2 = self.y + math.sin(a) * dist
            cv2.line(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2, cv2.LINE_AA)

        ring_r = int(20 + t * 60)
        cv2.circle(frame, (self.x, self.y), ring_r, color, 2, cv2.LINE_AA)


NUM_ENEMIES = 3
MIN_SEPARATION = 150


class EnemyManager:
    def __init__(self, frame_w, frame_h, count=NUM_ENEMIES):
        self.frame_w = frame_w
        self.frame_h = frame_h
        self.count = count
        self.enemies = []
        self.score = 0
        self.combo = 0
        self.best_combo = 0
        self.effects = []
        for _ in range(count):
            self.enemies.append(self._make_enemy())

    def _make_enemy(self):
        x, y = 0, 0
        for _ in range(20):
            x = random.randint(SPAWN_MARGIN_X, self.frame_w - SPAWN_MARGIN_X)
            y = random.randint(SPAWN_MARGIN_TOP, self.frame_h - SPAWN_MARGIN_BOTTOM)
            if all(math.hypot(x - e.x, y - e.y) > MIN_SEPARATION for e in self.enemies):
                break
        return Enemy(x, y)

    def try_hit(self, point):
        hit_enemy = None
        for e in self.enemies:
            if e.hit_test(point):
                hit_enemy = e
                break

        if hit_enemy:
            self.score += 1
            self.combo += 1
            self.best_combo = max(self.best_combo, self.combo)
            self.effects.append(KillEffect(hit_enemy.x, hit_enemy.y))
            self.enemies.remove(hit_enemy)
            self.enemies.append(self._make_enemy())
            return True

        self.combo = 0
        return False

    def update(self):
        self.effects = [e for e in self.effects if e.alive()]

    def draw(self, frame):
        for e in self.enemies:
            e.draw(frame)
        for e in self.effects:
            e.draw(frame)

        score_text = "SCORE: {}".format(self.score)
        combo_text = "COMBO: {}".format(self.combo) if self.combo > 1 else ""

        cv2.putText(frame, score_text, (frame.shape[1] // 2 - 70, 45),
                    cv2.FONT_HERSHEY_DUPLEX, 0.75, (255, 255, 255), 1, cv2.LINE_AA)
        if combo_text:
            cv2.putText(frame, combo_text, (frame.shape[1] // 2 - 55, 75),
                        cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)