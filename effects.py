import random
import math
import time
import cv2

WEB_COLOR = (235, 235, 235)
BULLET_COLOR = (40, 140, 255)
STATIC_DURATION = 1.2
PARTICLE_LIFE = 0.6
STUCK_MAX = 6


def _sticky_line(frame, p1, p2, color, thickness, segments=4, jitter=3):
    x1, y1 = p1
    x2, y2 = p2
    pts = [(int(x1), int(y1))]
    for i in range(1, segments):
        t = i / segments
        x = x1 + (x2 - x1) * t + random.randint(-jitter, jitter)
        y = y1 + (y2 - y1) * t + random.randint(-jitter, jitter)
        pts.append((int(x), int(y)))
    pts.append((int(x2), int(y2)))

    shadow = tuple(max(0, int(c * 0.35)) for c in color)
    highlight = tuple(min(255, int(c * 1.1) + 50) for c in color)

    for i in range(len(pts) - 1):
        cv2.line(frame, pts[i], pts[i + 1], shadow, thickness + 2, cv2.LINE_AA)
        cv2.line(frame, pts[i], pts[i + 1], color, thickness, cv2.LINE_AA)
        hp1 = (pts[i][0] - 1, pts[i][1] - 1)
        hp2 = (pts[i + 1][0] - 1, pts[i + 1][1] - 1)
        cv2.line(frame, hp1, hp2, highlight, max(1, thickness - 1), cv2.LINE_AA)

    for p in pts:
        r = max(1, thickness // 2 + 1)
        cv2.circle(frame, p, r, highlight, -1, cv2.LINE_AA)
        cv2.circle(frame, p, r, shadow, 1, cv2.LINE_AA)


def _jitter_line(frame, p1, p2, color, thickness, segments=4, jitter=3):
    x1, y1 = p1
    x2, y2 = p2
    pts = [(int(x1), int(y1))]
    for i in range(1, segments):
        t = i / segments
        x = x1 + (x2 - x1) * t + random.randint(-jitter, jitter)
        y = y1 + (y2 - y1) * t + random.randint(-jitter, jitter)
        pts.append((int(x), int(y)))
    pts.append((int(x2), int(y2)))
    for i in range(len(pts) - 1):
        cv2.line(frame, pts[i], pts[i + 1], color, thickness, cv2.LINE_AA)


class GrowingWebSplat:
    def __init__(self, origin, duration=0.9, max_radius=130, spokes=7, rings=3):
        self.origin = origin
        self.duration = duration
        self.max_radius = max_radius
        self.spawn_time = time.time()
        self.rings = rings
        self.angles = [(2 * math.pi / spokes) * i + random.uniform(-0.15, 0.15) for i in range(spokes)]
        self.jitter_seed = [[(random.randint(-3, 3), random.randint(-3, 3)) for _ in range(spokes)] for _ in range(rings)]

    def alive(self):
        return time.time() - self.spawn_time < self.duration

    def draw(self, frame):
        t = (time.time() - self.spawn_time) / self.duration
        radius = (t * t) * self.max_radius
        alpha = max(0.0, 1.0 - t * 0.6)
        color = tuple(int(c * alpha) for c in WEB_COLOR)
        thickness = 1 + int(t * 2)
        ox, oy = self.origin

        for a in self.angles:
            ex = ox + math.cos(a) * radius
            ey = oy + math.sin(a) * radius
            _sticky_line(frame, (int(ox), int(oy)), (int(ex), int(ey)), color, thickness, segments=3, jitter=2)

        for r in range(1, self.rings + 1):
            rr = radius * (r / self.rings)
            pts = []
            for i, a in enumerate(self.angles):
                jx, jy = self.jitter_seed[r - 1][i]
                px = ox + math.cos(a) * rr + jx
                py = oy + math.sin(a) * rr + jy
                pts.append((int(px), int(py)))
            for i in range(len(pts)):
                _sticky_line(frame, pts[i], pts[(i + 1) % len(pts)], color, thickness, segments=2, jitter=2)


class Particle:
    def __init__(self, origin, angle, speed):
        self.x, self.y = origin
        self.angle = angle
        self.speed = speed
        self.max_life = PARTICLE_LIFE
        self.life = self.max_life
        self.trail_len = random.randint(18, 32)

    def update(self, dt):
        self.x += math.cos(self.angle) * self.speed * dt
        self.y += math.sin(self.angle) * self.speed * dt
        self.life -= dt

    def alive(self):
        return self.life > 0

    def draw(self, frame):
        t = self.life / self.max_life
        color = tuple(int(c * (0.4 + 0.6 * t)) for c in WEB_COLOR)
        tail_x = self.x - math.cos(self.angle) * self.trail_len
        tail_y = self.y - math.sin(self.angle) * self.trail_len
        _jitter_line(frame, (int(tail_x), int(tail_y)), (int(self.x), int(self.y)), color, 2)


class ParticleBurst:
    def __init__(self, origin, direction, toward_camera, count=9, spread=0.5):
        self.web = GrowingWebSplat(origin) if toward_camera else None
        self.particles = []
        if not toward_camera:
            base_angle = math.atan2(direction[1], direction[0])
            for _ in range(count):
                a = base_angle + random.uniform(-spread, spread)
                speed = random.uniform(220, 420)
                self.particles.append(Particle(origin, a, speed))

    def update(self, dt):
        if self.web:
            return
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.alive()]

    def alive(self):
        if self.web:
            return self.web.alive()
        return len(self.particles) > 0

    def draw(self, frame):
        if self.web:
            self.web.draw(frame)
            return
        for p in self.particles:
            p.draw(frame)


def _build_web_geometry(origin, radius, spokes=8, rings=3):
    ox, oy = origin
    spoke_ends = []
    for i in range(spokes):
        a = (2 * math.pi / spokes) * i
        ex = ox + math.cos(a) * radius
        ey = oy + math.sin(a) * radius
        spoke_ends.append((ex, ey, a))

    ring_points = []
    for r in range(1, rings + 1):
        rr = radius * (r / rings)
        pts = []
        for i in range(spokes):
            a = spoke_ends[i][2]
            jx = ox + math.cos(a) * rr + random.randint(-2, 2)
            jy = oy + math.sin(a) * rr + random.randint(-2, 2)
            pts.append((int(jx), int(jy)))
        ring_points.append(pts)

    return spoke_ends, ring_points


class StaticWebPattern:
    def __init__(self, origin, radius=90):
        self.origin = origin
        self.radius = radius
        self.spawn_time = time.time()
        self.spoke_ends, self.ring_points = _build_web_geometry(origin, radius)

    def alive(self):
        return time.time() - self.spawn_time < STATIC_DURATION

    def draw(self, frame):
        t = (time.time() - self.spawn_time) / STATIC_DURATION
        alpha = max(0.0, 1.0 - t)
        color = tuple(int(c * alpha) for c in WEB_COLOR)
        ox, oy = int(self.origin[0]), int(self.origin[1])

        for ex, ey, _ in self.spoke_ends:
            _sticky_line(frame, (ox, oy), (int(ex), int(ey)), color, 1, segments=3, jitter=2)

        for pts in self.ring_points:
            for i in range(len(pts)):
                p1 = pts[i]
                p2 = pts[(i + 1) % len(pts)]
                _sticky_line(frame, p1, p2, color, 1, segments=2, jitter=2)


class StuckWeb:
    def __init__(self, origin, radius=70):
        self.origin = origin
        self.radius = radius
        self.spoke_ends, self.ring_points = _build_web_geometry(origin, radius)

    def draw(self, frame):
        ox, oy = int(self.origin[0]), int(self.origin[1])
        for ex, ey, _ in self.spoke_ends:
            _sticky_line(frame, (ox, oy), (int(ex), int(ey)), WEB_COLOR, 1, segments=3, jitter=2)

        for pts in self.ring_points:
            for i in range(len(pts)):
                p1 = pts[i]
                p2 = pts[(i + 1) % len(pts)]
                _sticky_line(frame, p1, p2, WEB_COLOR, 1, segments=2, jitter=2)


class BulletBurst:
    def __init__(self, origin, duration=0.35, max_radius=230):
        self.origin = origin
        self.duration = duration
        self.max_radius = max_radius
        self.spawn_time = time.time()

    def alive(self):
        return time.time() - self.spawn_time < self.duration

    def draw(self, frame):
        t = (time.time() - self.spawn_time) / self.duration
        radius = (t ** 0.5) * self.max_radius
        alpha = max(0.0, 1 - t)
        color = tuple(int(c * alpha) for c in BULLET_COLOR)
        thickness = max(1, int(6 * alpha))
        ox, oy = self.origin

        cv2.circle(frame, (int(ox), int(oy)), int(radius), color, thickness, cv2.LINE_AA)

        for ang_deg in range(0, 360, 45):
            a = math.radians(ang_deg)
            ix = ox + math.cos(a) * radius * 0.55
            iy = oy + math.sin(a) * radius * 0.55
            ex = ox + math.cos(a) * radius * 1.15
            ey = oy + math.sin(a) * radius * 1.15
            cv2.line(frame, (int(ix), int(iy)), (int(ex), int(ey)), color, max(1, thickness - 1), cv2.LINE_AA)


class Flash:
    def __init__(self, duration=0.12):
        self.start = time.time()
        self.duration = duration

    def alive(self):
        return time.time() - self.start < self.duration

    def draw(self, frame):
        t = (time.time() - self.start) / self.duration
        alpha = max(0.0, 1 - t) * 0.4
        overlay = frame.copy()
        overlay[:] = (255, 255, 255)
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)


class EffectManager:
    def __init__(self):
        self.bursts = []
        self.static_patterns = []
        self.stuck_webs = []
        self.flashes = []
        self.bullets = []
        self.last_update = time.time()

    def spawn(self, effect_type, origin, direction, toward_camera):
        if effect_type == "particle":
            self.bursts.append(ParticleBurst(origin, direction, toward_camera))
        elif effect_type == "static":
            self.static_patterns.append(StaticWebPattern(origin))
        elif effect_type == "stuck":
            self.stuck_webs.append(StuckWeb(origin))
            if len(self.stuck_webs) > STUCK_MAX:
                self.stuck_webs.pop(0)

    def spawn_bullet(self, origin):
        self.bullets.append(BulletBurst(origin))

    def spawn_flash(self):
        self.flashes.append(Flash())

    def update(self):
        now = time.time()
        dt = now - self.last_update
        self.last_update = now

        for b in self.bursts:
            b.update(dt)
        self.bursts = [b for b in self.bursts if b.alive()]
        self.static_patterns = [s for s in self.static_patterns if s.alive()]
        self.flashes = [f for f in self.flashes if f.alive()]
        self.bullets = [b for b in self.bullets if b.alive()]

    def draw(self, frame, show_web=True):
        if show_web:
            for w in self.stuck_webs:
                w.draw(frame)
            for s in self.static_patterns:
                s.draw(frame)
        for b in self.bursts:
            b.draw(frame)
        for bl in self.bullets:
            bl.draw(frame)
        for f in self.flashes:
            f.draw(frame)