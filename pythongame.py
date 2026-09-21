import math
import json
import random
import sys
from array import array
from colorsys import hsv_to_rgb
from pathlib import Path

import pygame

WIDTH, HEIGHT = 960, 640
ROAD = pygame.Rect(190, 0, 580, HEIGHT)
LANES = [260, 405, 550, 695]
FPS = 60
SAVE_FILE = Path(__file__).with_name("highway_hooligans_highscore.txt")
PROFILE_FILE = Path(__file__).with_name("highway_hooligans_profile.json")

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("HIGHWAY HOOLIGANS // NIGHT RUN")
clock = pygame.time.Clock()
FONT = pygame.font.SysFont("consolas", 20, bold=True)
SMALL = pygame.font.SysFont("consolas", 15, bold=True)
TITLE = pygame.font.SysFont("impact", 76)
SUBTITLE = pygame.font.SysFont("consolas", 24, bold=True)
WHITE = (240, 245, 244)
INK = (10, 16, 25)
CYAN = (45, 224, 213)
YELLOW = (255, 208, 76)
PINK = (255, 72, 135)
RED = (242, 74, 83)
MAX_BOOST = 142.0
PLAYER_SPEED_MULTIPLIER = 1.2
NITRO_SPEED_BONUS = 2.1
MAX_ROAD_SPEED = 3.0
SPEED_CAP_DISTANCE = 4800
SHIFT_WARNING_DURATION = .75
SHIFT_WARNING_FLASH = SHIFT_WARNING_DURATION / 6
audio_channel = None
audio_tracks = {}
crash_sound = None

SKINS = (
    {"id": "neon", "name": "NEON CYAN", "price": 0, "min_score": 0, "colour": CYAN},
    {"id": "inferno", "name": "INFERNO", "price": 180, "min_score": 250, "colour": (255, 92, 48)},
    {"id": "violet", "name": "VIOLET VOLT", "price": 350, "min_score": 750, "colour": (168, 89, 227)},
    {"id": "rainbow", "name": "PRISM RUSH", "price": 1000, "min_score": 3000, "colour": PINK},
    {"id": "aurora", "name": "AURORA SHIFT", "price": 1500, "min_score": 6000, "colour": (75, 220, 180)},
    {"id": "gold", "name": "GOLD STANDARD", "price": 2200, "min_score": 10000, "colour": (255, 193, 48)},
)
DEATH_ANIMATIONS = (
    {"id": "standard", "name": "STREET CRASH", "price": 0, "min_score": 0, "colour": RED},
    {"id": "shockwave", "name": "SHOCKWAVE", "price": 260, "min_score": 500, "colour": CYAN},
    {"id": "fireworks", "name": "FIREWORKS", "price": 500, "min_score": 1200, "colour": PINK},
    {"id": "pixel", "name": "PIXEL BURST", "price": 850, "min_score": 2500, "colour": YELLOW},
    {"id": "blackhole", "name": "BLACK HOLE", "price": 1400, "min_score": 5000, "colour": (130, 90, 227)},
    {"id": "laser", "name": "LASER GRID", "price": 2000, "min_score": 9000, "colour": (255, 80, 120)},
)


def make_track(notes, beat_length):
    sample_rate = 22050
    samples = array("h")
    for note in notes:
        for sample_index in range(int(sample_rate * beat_length)):
            time = sample_index / sample_rate
            envelope = min(1.0, time * 18) * min(1.0, (beat_length - time) * 10)
            lead = math.sin(math.tau * note * time) * .18
            bass = math.sin(math.tau * (note / 2) * time) * .12
            samples.append(int((lead + bass) * envelope * 32767))
    return pygame.mixer.Sound(buffer=samples.tobytes())


def start_music():
    global audio_channel, audio_tracks, crash_sound
    try:
        pygame.mixer.init()
        normal_notes = (220, 262, 330, 294, 247, 294, 370, 330,
                        196, 247, 294, 330, 220, 262, 330, 392)
        nitro_notes = tuple(note * 2 for note in normal_notes)
        audio_tracks = {"normal": make_track(normal_notes, .28),
                        "nitro": make_track(nitro_notes, .14)}
        for track in audio_tracks.values():
            track.set_volume(.22)
        crash_samples = array("h")
        for sample_index in range(int(22050 * .55)):
            time = sample_index / 22050
            envelope = max(0, 1 - time * 1.9)
            noise = random.uniform(-1, 1) * .4
            boom = math.sin(math.tau * (90 - time * 70) * time) * .6
            crash_samples.append(int((noise + boom) * envelope * 32767))
        crash_sound = pygame.mixer.Sound(buffer=crash_samples.tobytes())
        crash_sound.set_volume(.4)
        audio_channel = pygame.mixer.Channel(0)
        audio_channel.play(audio_tracks["normal"], loops=-1)
    except pygame.error:
        audio_channel, audio_tracks, crash_sound = None, {}, None


def update_music(boosting):
    if audio_channel is None or not audio_tracks:
        return
    desired = "nitro" if boosting else "normal"
    if audio_channel.get_sound() is not audio_tracks[desired]:
        audio_channel.play(audio_tracks[desired], loops=-1, fade_ms=140)


def play_crash_sound():
    if crash_sound is not None:
        crash_sound.play()


def stop_music():
    if audio_channel is not None:
        audio_channel.stop()


def load_high_score():
    try:
        return int(SAVE_FILE.read_text(encoding="ascii").strip())
    except (OSError, ValueError):
        return 0


def save_high_score(score):
    try:
        SAVE_FILE.write_text(str(score), encoding="ascii")
    except OSError:
        pass


def load_profile():
    default = {"coins": 0, "owned_skins": ["neon"],
               "owned_deaths": ["standard"], "skin": "neon", "death": "standard"}
    try:
        profile = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
        for key, value in default.items():
            profile.setdefault(key, value)
        valid_skin_ids = {skin["id"] for skin in SKINS}
        valid_death_ids = {animation["id"] for animation in DEATH_ANIMATIONS}
        profile["owned_skins"] = [skin_id for skin_id in profile["owned_skins"]
                                   if skin_id in valid_skin_ids]
        profile["owned_deaths"] = [death_id for death_id in profile["owned_deaths"]
                                    if death_id in valid_death_ids]
        if profile["skin"] not in valid_skin_ids:
            profile["skin"] = "neon"
        if profile["death"] not in valid_death_ids:
            profile["death"] = "standard"
        return profile
    except (OSError, ValueError, TypeError):
        return default


def save_profile(profile):
    try:
        PROFILE_FILE.write_text(json.dumps(profile), encoding="utf-8")
    except OSError:
        pass


def selected_skin(profile):
    return next((skin for skin in SKINS if skin["id"] == profile["skin"]), SKINS[0])


def award_run_coins(profile, score):
    earned = max(1, score // 10)
    profile["coins"] += earned
    save_profile(profile)
    return earned


def draw_text(message, font, colour, position, anchor="center"):
    image = font.render(message, True, colour)
    screen.blit(image, image.get_rect(**{anchor: position}))


def draw_panel(rect, colour=(18, 28, 42), border=CYAN):
    pygame.draw.rect(screen, colour, rect, border_radius=8)
    pygame.draw.rect(screen, border, rect, 2, border_radius=8)


def draw_scanlines(alpha=18):
    scanlines = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for y in range(0, HEIGHT, 6):
        pygame.draw.line(scanlines, (130, 240, 235, alpha), (0, y), (WIDTH, y), 1)
    screen.blit(scanlines, (0, 0))


def draw_corner_frame(rect, colour):
    length = 24
    corners = ((rect.left, rect.top, 1, 1), (rect.right, rect.top, -1, 1),
               (rect.left, rect.bottom, 1, -1), (rect.right, rect.bottom, -1, -1))
    for x, y, horizontal, vertical in corners:
        pygame.draw.line(screen, colour, (x, y), (x + horizontal * length, y), 3)
        pygame.draw.line(screen, colour, (x, y), (x, y + vertical * length), 3)


def draw_light_beams(colour=CYAN, intensity=24):
    beams = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for x in (80, WIDTH - 80, WIDTH // 2 - 250, WIDTH // 2 + 250):
        points = [(x - 18, 0), (x + 18, 0), (x + 90, HEIGHT), (x - 90, HEIGHT)]
        pygame.draw.polygon(beams, (*colour, intensity), points)
    screen.blit(beams, (0, 0))


def draw_checkered_strip(rect, tile=18):
    for row, y in enumerate(range(rect.top, rect.bottom, tile)):
        for column, x in enumerate(range(rect.left, rect.right, tile)):
            colour = (235, 240, 225) if (row + column) % 2 == 0 else (15, 26, 38)
            pygame.draw.rect(screen, colour, (x, y, tile, tile))


def draw_city_sign(rect, label, colour, flip=False):
    glow = pygame.Surface((rect.w + 24, rect.h + 24), pygame.SRCALPHA)
    pygame.draw.rect(glow, (*colour, 24), (12, 12, rect.w, rect.h), border_radius=5)
    screen.blit(glow, (rect.x - 12, rect.y - 12))
    pygame.draw.rect(screen, (8, 20, 32), rect, border_radius=4)
    pygame.draw.rect(screen, colour, rect, 2, border_radius=4)
    pygame.draw.line(screen, tuple(min(255, channel + 50) for channel in colour),
                     (rect.left + 5, rect.top + 5), (rect.right - 5, rect.top + 5), 2)
    draw_text(label, SMALL, colour, rect.center)
    if flip:
        pygame.draw.line(screen, colour, (rect.left - 8, rect.bottom + 7),
                         (rect.right + 8, rect.bottom + 7), 2)


def make_car(x, y, colour, kind="traffic", lane=None, can_shift=None, skin_id=None):
    if kind == "player":
        width, height = 48, 82
    elif kind == "truck":
        width, height = 62, 116
    else:
        width, height = 46, 78
    lane = lane if lane is not None else LANES.index(x)
    return {"rect": pygame.Rect(x - width // 2, y, width, height), "colour": colour,
            "skin_id": skin_id,
            "kind": kind, "lane": lane, "target_lane": lane,
            "target_x": float(x),
            "lane_change_timer": random.uniform(.8, 2.2),
            "warning_timer": 0.0,
            "announced": False,
            "last_y": y,
            "can_shift": (kind != "player" and random.random() < .45)
            if can_shift is None else can_shift,
            "speed": random.uniform(.92, 1.18) if kind != "truck" else random.uniform(.74, .92),
            "near": False}


def new_game(profile):
    skin = selected_skin(profile)
    return {"player": make_car(LANES[1], HEIGHT - 125, skin["colour"], "player", 1,
                                skin_id=skin["id"]),
            "traffic": [], "pickups": [], "particles": [], "score": 0,
            "combo": 1, "lives": 3, "distance": 0.0, "spawn_timer": .4,
            "pickup_timer": 6.0, "boost": 100.0, "shield": 0.0,
            "road_speed": 1.0,
            "invincible": 0.0, "shake": 0.0, "flash": 0.0, "last_milestone": 0,
            "explosion_started": None, "boosting": False,
            "death_animation": profile["death"]}


def add_particle(state, position, colour, amount=8, force=1.0):
    for _ in range(amount):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(35, 150) * force
        state["particles"].append({"x": position[0], "y": position[1],
            "vx": math.cos(angle) * speed, "vy": math.sin(angle) * speed,
            "life": random.uniform(.25, .65), "size": random.randint(2, 5), "colour": colour})


def draw_background(state, offset):
    screen.fill((8, 17, 29))
    for y in range(0, HEIGHT, 32):
        pygame.draw.line(screen, (10, 30 + (y % 64) // 4, 43), (0, y), (WIDTH, y), 1)
    for x in range(25, WIDTH, 70):
        height = 35 + (x * 17) % 95
        pygame.draw.rect(screen, (11, 31, 43), (x, 170 - height, 42, height))
        for window_y in range(180 - height, 170, 18):
            pygame.draw.rect(screen, (30, 88, 94), (x + 9, window_y, 5, 4))
    horizon = pygame.Surface((WIDTH, 150), pygame.SRCALPHA)
    horizon.fill((20, 130, 139, 18))
    screen.blit(horizon, (0, 105))
    pygame.draw.rect(screen, (31, 38, 48), ROAD)
    pygame.draw.rect(screen, (20, 24, 34), ROAD.inflate(-10, 0))
    pygame.draw.line(screen, (70, 80, 91), (ROAD.left + 8, 0), (ROAD.left + 8, HEIGHT), 2)
    pygame.draw.line(screen, (70, 80, 91), (ROAD.right - 8, 0), (ROAD.right - 8, HEIGHT), 2)
    city_offset = int(state["distance"] * (90 if state["boosting"] else 48)) % 180
    side_maps = ((12, 166), (782, 948))
    for map_left, map_right in side_maps:
        map_surface = pygame.Rect(map_left, 0, map_right - map_left, HEIGHT)
        pygame.draw.rect(screen, (6, 19, 31), map_surface)
        for road_y in range(-180 + city_offset, HEIGHT + 180, 90):
            pygame.draw.rect(screen, (18, 46, 57), (map_left, road_y, map_surface.w, 13))
            pygame.draw.line(screen, (43, 99, 105), (map_left, road_y + 6),
                             (map_right, road_y + 6), 1)
        for road_x in range(map_left + 18, map_right, 48):
            pygame.draw.rect(screen, (18, 46, 57), (road_x, 0, 11, HEIGHT))
        for block_index, block_y in enumerate(range(-135 + city_offset, HEIGHT + 180, 180)):
            for block_column, block_x in enumerate(range(map_left + 4, map_right - 30, 52)):
                block = pygame.Rect(block_x, block_y, 38, 62)
                pygame.draw.rect(screen, (10, 31, 43), block, border_radius=2)
                pygame.draw.rect(screen, (23, 66, 75), block, 1, border_radius=2)
                for light_index in range(4):
                    if (block_index * 3 + block_column + light_index) % 4:
                        light_seed = (block_index * 29 + block_column * 47
                                      + light_index * 71 + map_left)
                        hue = (light_seed * 0.137) % 1.0
                        red, green, blue = hsv_to_rgb(hue, .82, 1.0)
                        light = (int(red * 255), int(green * 255), int(blue * 255))
                        light_x = block.left + 7 + (light_index % 2) * 16
                        light_y = block.top + 10 + (light_index // 2) * 22
                        pygame.draw.rect(screen, light, (light_x, light_y, 7, 5), border_radius=1)
    city_signs = ((72, "NEON DISTRICT", CYAN), (112, "04", PINK),
                  (HEIGHT - 128, "NIGHT", (130, 90, 227)),
                  (HEIGHT - 78, "RIDE", CYAN))
    for index, (base_y, label, colour) in enumerate(city_signs):
        side = ROAD.left - 170 if index % 2 == 0 else ROAD.right + 20
        sign_width = 148 if label == "NEON DISTRICT" else 74
        draw_city_sign(pygame.Rect(side, base_y, sign_width, 32), label, colour, index % 2 == 1)
        pole_x = side + (12 if index % 2 == 0 else 62)
        pygame.draw.line(screen, (45, 65, 76), (pole_x, base_y + 32),
                         (pole_x, base_y + 95), 2)
    for x in (ROAD.left - 35, ROAD.right + 35):
        pygame.draw.line(screen, (27, 53, 66), (x, 0), (x, HEIGHT), 2)
        for y in range(-20, HEIGHT, 72):
            pygame.draw.circle(screen, (45, 224, 213), (x, y + 20), 2)
    for x in (ROAD.left, ROAD.right):
        pygame.draw.line(screen, (255, 208, 76, 55), (x - 5, 0), (x - 5, HEIGHT), 6)
        pygame.draw.line(screen, YELLOW, (x, 0), (x, HEIGHT), 4)
    dash_speed = 220 if state["boosting"] else 120
    dash_length = 62 if state["boosting"] else 48
    dash_y = int((state["distance"] * dash_speed + offset) % 100) - 100
    for x in (335, 480, 625):
        for y in range(dash_y, HEIGHT, 100):
            pygame.draw.rect(screen, (150, 164, 170) if state["boosting"] else (110, 121, 132),
                             (x - 2, y, 4, dash_length))
    if state["boosting"]:
        streak_offset = int(state["distance"] * 260) % 70
        for x in (ROAD.left + 22, ROAD.right - 22):
            for y in range(streak_offset - 70, HEIGHT, 70):
                pygame.draw.line(screen, (70, 155, 160), (x, y), (x, y + 28), 2)


def draw_skin_body(car):
    rect = car["rect"]
    skin_id = car.get("skin_id")
    if skin_id == "neon":
        for y in range(rect.top + 2, rect.bottom - 1):
            pulse = (math.sin(pygame.time.get_ticks() / 260 + y / 18) + 1) / 2
            colour = (int(24 + pulse * 35), int(170 + pulse * 54), int(174 + pulse * 55))
            pygame.draw.line(screen, colour, (rect.left + 2, y), (rect.right - 2, y))
    elif skin_id == "inferno":
        for y in range(rect.top + 2, rect.bottom - 1):
            heat = (math.sin(pygame.time.get_ticks() / 420 + y / 13) + 1) / 2
            colour = (255, int(52 + heat * 100), int(28 + heat * 28))
            pygame.draw.line(screen, colour, (rect.left + 2, y), (rect.right - 2, y))
    elif skin_id == "violet":
        for y in range(rect.top + 2, rect.bottom - 1):
            shimmer = (math.sin(pygame.time.get_ticks() / 330 + y / 16) + 1) / 2
            colour = (int(108 + shimmer * 95), int(42 + shimmer * 55), int(175 + shimmer * 65))
            pygame.draw.line(screen, colour, (rect.left + 2, y), (rect.right - 2, y))
    elif skin_id == "rainbow":
        for y in range(rect.top + 2, rect.bottom - 1):
            hue = (y / 180 + pygame.time.get_ticks() / 3600) % 1.0
            colour = tuple(int(channel * 255) for channel in hsv_to_rgb(hue, .8, 1.0))
            pygame.draw.line(screen, colour, (rect.left + 2, y), (rect.right - 2, y))
    elif skin_id == "aurora":
        for y in range(rect.top + 2, rect.bottom - 1):
            wave = (math.sin(pygame.time.get_ticks() / 500 + y / 15) + 1) / 2
            colour = (int(38 + wave * 62), int(145 + wave * 80), int(175 + wave * 55))
            pygame.draw.line(screen, colour, (rect.left + 2, y), (rect.right - 2, y))
    elif skin_id == "gold":
        for y in range(rect.top + 2, rect.bottom - 1):
            shine = (math.sin(pygame.time.get_ticks() / 280 + y / 12) + 1) / 2
            colour = (255, int(146 + shine * 88), int(22 + shine * 70))
            pygame.draw.line(screen, colour, (rect.left + 2, y), (rect.right - 2, y))
    else:
        pygame.draw.rect(screen, car["colour"], rect,
                         border_radius=6 if car["kind"] == "truck" else 10)


def draw_car(car, glow=False):
    rect, colour = car["rect"], car["colour"]
    shifting = car["target_lane"] != car["lane"]
    if glow:
        pygame.draw.rect(screen, (25, 110, 125), rect.inflate(22, 22), 2, border_radius=15)
        pygame.draw.rect(screen, (70, 220, 213), rect.inflate(13, 13), 2, border_radius=12)
    if car["kind"] == "player":
        draw_skin_body(car)
    else:
        pygame.draw.rect(screen, colour, rect, border_radius=6 if car["kind"] == "truck" else 10)
    pygame.draw.rect(screen, (255, 255, 255), rect, 2,
                     border_radius=6 if car["kind"] == "truck" else 10)
    pygame.draw.line(screen, tuple(min(255, channel + 55) for channel in colour),
                     (rect.left + 8, rect.top + 4), (rect.right - 8, rect.top + 4), 3)
    if car["kind"] == "truck":
        cargo = pygame.Rect(rect.x + 4, rect.y + 3, rect.w - 8, rect.h - 35)
        pygame.draw.rect(screen, (224, 229, 218), cargo, border_radius=4)
        pygame.draw.line(screen, colour, (cargo.centerx, cargo.top + 6), (cargo.centerx, cargo.bottom - 5), 3)
        cab = pygame.Rect(rect.x + 4, rect.bottom - 35, rect.w - 8, 31)
        pygame.draw.rect(screen, colour, cab, border_radius=5)
        pygame.draw.rect(screen, (16, 26, 39), (cab.x + 8, cab.y + 6, cab.w - 16, 13), border_radius=4)
    else:
        pygame.draw.rect(screen, (16, 26, 39), (rect.x + 7, rect.y + 11, rect.w - 14, 25), border_radius=6)
        pygame.draw.rect(screen, (100, 218, 226), (rect.x + 10, rect.y + 14, rect.w - 20, 8), border_radius=3)
        pygame.draw.line(screen, (220, 255, 249), (rect.left + 11, rect.y + 15),
                 (rect.right - 11, rect.y + 15), 2)
    pygame.draw.rect(screen, (255, 233, 123), (rect.x + 7, rect.bottom - 16, 9, 5), border_radius=2)
    pygame.draw.rect(screen, (255, 82, 92), (rect.right - 16, rect.bottom - 16, 9, 5), border_radius=2)
    for wheel_y in (rect.y + 18, rect.bottom - 24):
        pygame.draw.rect(screen, INK, (rect.left - 4, wheel_y, 7, 15), border_radius=3)
        pygame.draw.rect(screen, INK, (rect.right - 3, wheel_y, 7, 15), border_radius=3)
    warning = car["warning_timer"] > 0
    warning_elapsed = SHIFT_WARNING_DURATION - car["warning_timer"]
    warning_blink = int(warning_elapsed / SHIFT_WARNING_FLASH) % 2 == 0
    if (shifting or warning) and (not warning or warning_blink):
        indicator_colour = YELLOW
        side = 1 if car["target_lane"] > car["lane"] else -1
        indicator_x = rect.right + 10 if side > 0 else rect.left - 10
        points = [(indicator_x, rect.centery - 8),
                  (indicator_x + side * 9, rect.centery),
                  (indicator_x, rect.centery + 8)]
        pygame.draw.polygon(screen, indicator_colour, points)


def draw_skin_preview(item, centre):
    rect = pygame.Rect(centre[0] - 12, centre[1] - 11, 24, 22)
    preview_car = {"rect": rect, "colour": item["colour"], "kind": "player",
                   "skin_id": item["id"]}
    draw_skin_body(preview_car)
    pygame.draw.rect(screen, WHITE, rect, 1, border_radius=4)


def draw_death_preview(item, centre):
    pulse = 8 + int((pygame.time.get_ticks() / 120) % 8)
    colour = item["colour"]
    if item["id"] == "standard":
        pygame.draw.circle(screen, YELLOW, centre, pulse, 2)
        pygame.draw.circle(screen, RED, centre, max(3, pulse - 5), 2)
    elif item["id"] == "shockwave":
        pygame.draw.circle(screen, colour, centre, pulse, 3)
        pygame.draw.circle(screen, WHITE, centre, max(3, pulse - 6), 1)
    elif item["id"] == "fireworks":
        for angle in range(0, 360, 60):
            direction = pygame.Vector2(1, 0).rotate(angle)
            pygame.draw.line(screen, colour, centre + direction * 5,
                             centre + direction * pulse, 2)
    elif item["id"] == "pixel":
        pygame.draw.rect(screen, colour, (centre[0] - pulse // 2, centre[1] - pulse // 2,
                                          pulse, pulse), 3)
    elif item["id"] == "blackhole":
        pygame.draw.circle(screen, (12, 8, 28), centre, max(4, pulse - 4))
        pygame.draw.circle(screen, colour, centre, pulse, 2)
    elif item["id"] == "laser":
        pygame.draw.line(screen, colour, (centre[0] - pulse, centre[1] - pulse),
                         (centre[0] + pulse, centre[1] + pulse), 2)
        pygame.draw.line(screen, WHITE, (centre[0] - pulse, centre[1] + pulse),
                         (centre[0] + pulse, centre[1] - pulse), 1)


def draw_nitro_effect(player):
    rect = player["rect"]
    pulse = 2 + int((pygame.time.get_ticks() / 55) % 4)
    for x in (rect.left + 12, rect.right - 12):
        pygame.draw.line(screen, (255, 208, 76), (x, rect.bottom + 3),
                         (x, rect.bottom + 23 + pulse), 4)
        pygame.draw.line(screen, (255, 245, 165), (x, rect.bottom + 4),
                         (x, rect.bottom + 14 + pulse), 2)


def draw_pickup(pickup):
    x, y = pickup["x"], pickup["y"]
    pulse = math.sin(pygame.time.get_ticks() / 150) * 3
    colour = YELLOW if pickup["type"] == "boost" else CYAN
    pygame.draw.circle(screen, colour, (int(x), int(y)), int(17 + pulse), 3)
    draw_text("N" if pickup["type"] == "boost" else "S", SMALL, colour, (x, y))


def draw_particles(state):
    for particle in state["particles"]:
        pygame.draw.circle(screen, particle["colour"], (int(particle["x"]), int(particle["y"])), particle["size"])


def update_particles(state, dt):
    for particle in state["particles"][:]:
        particle["life"] -= dt
        particle["x"] += particle["vx"] * dt
        particle["y"] += particle["vy"] * dt
        if particle["life"] <= 0:
            state["particles"].remove(particle)


def switch_player_lane(player, direction):
    player["target_lane"] = max(0, min(len(LANES) - 1, player["target_lane"] + direction))


def lane_is_clear(traffic, lane, y, gap=150, ignore=None):
    for car in traffic:
        if car is ignore:
            continue
        if (car["lane"] == lane or car["target_lane"] == lane) and abs(car["rect"].centery - y) < gap:
            return False
    return True


def safe_spawn_lanes(traffic, player_lane, player_y, gap=220):
    clear_lanes = [lane for lane in range(len(LANES))
                   if lane_is_clear(traffic, lane, -100, gap=150)]
    safe_lanes = []
    for lane in clear_lanes:
        if abs(lane - player_lane) == 1:
            opposite_lane = player_lane * 2 - lane
            if (0 <= opposite_lane < len(LANES)
                    and not lane_is_clear(traffic, opposite_lane, player_y, gap)):
                continue
        safe_lanes.append(lane)
    return safe_lanes


def powerup_lanes(traffic, player_y):
    lanes = []
    for lane in range(len(LANES)):
        blocked = any(
            (car["lane"] == lane or car["target_lane"] == lane)
            and car["rect"].bottom > -50
            and car["rect"].top < player_y + 90
            for car in traffic
        )
        if not blocked:
            lanes.append(lane)
    return lanes


def keep_powerup_clear(pickup, traffic):
    pickup_position = pygame.Vector2(pickup["x"], pickup["y"])
    overlapping = [car for car in traffic
                   if car["rect"].inflate(8, 8).collidepoint(pickup_position)]
    if not overlapping:
        return
    clear_lanes = [lane for lane in range(len(LANES))
                   if lane_is_clear(traffic, lane, pickup["y"], gap=90)]
    if clear_lanes:
        pickup["x"] = LANES[min(clear_lanes, key=lambda lane: abs(LANES[lane] - pickup["x"]))]
        return
    pickup["y"] = min(car["rect"].top for car in overlapping) - 45


def traffic_step_y(car, traffic, proposed_y):
    """Obstacle cars must always move downward. Never allow upward motion."""
    return proposed_y


def has_traffic_overlap(car, traffic):
    for other in traffic:
        if other is car:
            continue
        if car["rect"].colliderect(other["rect"]):
            return True
    return False


def update_game(state, dt):
    keys = pygame.key.get_pressed()
    player = state["player"]
    player_target_x = LANES[player["target_lane"]]
    space_held = bool(keys[pygame.K_SPACE])
    boosting = space_held and state["boost"] >= 34 * dt
    state["boosting"] = boosting
    update_music(boosting)
    if state["distance"] >= SPEED_CAP_DISTANCE:
        state["road_speed"] = MAX_ROAD_SPEED
    else:
        target_speed = 1.0 + min(MAX_ROAD_SPEED - 1.0,
                                 state["distance"] / (SPEED_CAP_DISTANCE / 2))
        state["road_speed"] += (target_speed - state["road_speed"]) * min(1.0, dt * .65)
    speed = state["road_speed"] * PLAYER_SPEED_MULTIPLIER + (NITRO_SPEED_BONUS if boosting else 0)
    lane_shift_speed = speed
    player_delta = player_target_x - player["rect"].centerx
    player["rect"].centerx += ((1 if player_delta > 0 else -1)
                               * min(abs(player_delta), int(620 * lane_shift_speed * dt))
                               if player_delta else 0)
    if player["rect"].centerx == player_target_x:
        player["lane"] = player["target_lane"]
    state["distance"] += speed * dt * 55
    if boosting:
        state["boost"] = max(0, state["boost"] - 34 * dt)
    elif not space_held:
        state["boost"] = min(MAX_BOOST, state["boost"] + 6 * dt)
    state["shield"] = max(0, state["shield"] - dt)
    state["invincible"] = max(0, state["invincible"] - dt)
    state["shake"] = max(0, state["shake"] - dt * 3)
    state["flash"] = max(0, state["flash"] - dt)
    state["spawn_timer"] -= dt
    state["pickup_timer"] -= dt
    shift_warning_duration = min(SHIFT_WARNING_DURATION, 180 / (250 * speed))
    if state["spawn_timer"] <= 0:
        player_lane = state["player"]["target_lane"]
        can_shift = random.random() < .25
        kind = "truck" if random.random() < .28 else "traffic"
        colour = random.choice([(242, 74, 83), (255, 126, 52), (168, 89, 227), (73, 190, 112)])
        height = 116 if kind == "truck" else 78
        if can_shift:
            source_lanes = [lane for lane in (player_lane - 1, player_lane + 1)
                            if 0 <= lane < len(LANES)]
            clear_sources = [lane for lane in source_lanes
                             if lane in safe_spawn_lanes(state["traffic"], player_lane,
                                                         state["player"]["rect"].centery)]
            if clear_sources:
                lane_index = random.choice(clear_sources)
            else:
                can_shift = False
                clear_lanes = safe_spawn_lanes(state["traffic"], player_lane,
                                               state["player"]["rect"].centery)
                lane_index = random.choice(clear_lanes or range(len(LANES)))
        else:
            clear_lanes = safe_spawn_lanes(state["traffic"], player_lane,
                                           state["player"]["rect"].centery)
            lane_index = random.choice(clear_lanes or range(len(LANES)))
        car = make_car(LANES[lane_index], -height - 10, colour, kind, lane_index, can_shift)
        if can_shift:
            car["target_lane"] = player_lane
            if not lane_is_clear(state["traffic"], player_lane, car["rect"].centery, gap=140, ignore=car):
                car["can_shift"] = False
                car["target_lane"] = lane_index
        state["traffic"].append(car)
        state["spawn_timer"] = max(.28, .9 - min(.55, state["distance"] / 2200) + random.uniform(-.06, .10))
    if state["pickup_timer"] <= 0:
        available_lanes = powerup_lanes(state["traffic"], state["player"]["rect"].centery)
        if not available_lanes:
            available_lanes = sorted(
                range(len(LANES)),
                key=lambda lane: sum(
                    car["lane"] == lane or car["target_lane"] == lane
                    for car in state["traffic"]
                )
            )[:1]
        state["pickups"].append({"x": LANES[random.choice(available_lanes)], "y": -35,
                                 "type": random.choice(("boost", "shield"))})
        state["pickup_timer"] = random.uniform(7, 11)
    for car in state["traffic"][:]:
        if has_traffic_overlap(car, state["traffic"]):
            state["traffic"].remove(car)
            continue
        if not car["announced"] and car["rect"].bottom >= 0:
            car["announced"] = True
            if car["can_shift"]:
                adjacent = [lane for lane in (car["lane"] - 1, car["lane"] + 1)
                            if 0 <= lane < len(LANES)]
                if car["target_lane"] in adjacent:
                    target_clear = lane_is_clear(state["traffic"], car["target_lane"],
                                                 car["rect"].centery, gap=140, ignore=car)
                    if target_clear:
                        car["warning_timer"] = shift_warning_duration
                    else:
                        car["can_shift"] = False
                        car["target_lane"] = car["lane"]
                else:
                    car["can_shift"] = False
                    car["target_lane"] = car["lane"]
        if car["warning_timer"] > 0:
            car["warning_timer"] = max(0, car["warning_timer"] - dt)
            car["lane_change_timer"] = random.uniform(1.6, 3.4)
        target_x = LANES[car["target_lane"]]
        if car["warning_timer"] <= 0 and car["rect"].centerx != target_x:
            if car["can_shift"] and lane_is_clear(state["traffic"], car["target_lane"],
                                                 car["rect"].centery, gap=140, ignore=car):
                direction = 1 if target_x > car["rect"].centerx else -1
                lane_motion = (155 + car["speed"] * 20) * state["road_speed"]
                car["rect"].centerx += direction * min(abs(target_x - car["rect"].centerx), max(1, int(lane_motion * dt)))
                if car["rect"].centerx == target_x:
                    car["lane"] = car["target_lane"]
            else:
                car["target_lane"] = car["lane"]
                car["can_shift"] = False
        traffic_speed = 250 * speed
        car["rect"].y = float(car["rect"].y) + traffic_speed * dt
        car["last_y"] = car["rect"].y
        if has_traffic_overlap(car, state["traffic"]):
            state["traffic"].remove(car)
            continue
        if car["rect"].top > HEIGHT:
            state["traffic"].remove(car)
            state["score"] += 10 * state["combo"]
            state["combo"] = min(9, state["combo"] + 1)
            continue
        if not car["near"] and player["rect"].colliderect(car["rect"].inflate(28, 8)):
            car["near"] = True
            if not player["rect"].colliderect(car["rect"]):
                state["score"] += 25 * state["combo"]
                state["combo"] = min(9, state["combo"] + 1)
                add_particle(state, player["rect"].center, YELLOW, 10)
        if state["invincible"] <= 0 and player["rect"].colliderect(car["rect"]):
            state["traffic"].remove(car)
            if state["shield"] > 0:
                state["score"] += 35 * state["combo"]
                add_particle(state, player["rect"].center, CYAN, 26, 1.3)
                continue
            play_crash_sound()
            state["invincible"] = 1.2
            state["shake"], state["flash"] = .5, .3
            add_particle(state, player["rect"].center, RED, 22, 1.4)
            state["lives"] -= 1
            state["combo"] = 1
    for pickup in state["pickups"][:]:
        pickup["y"] += int(250 * speed * dt)
        keep_powerup_clear(pickup, state["traffic"])
        if player["rect"].collidepoint(pickup["x"], pickup["y"]):
            state["pickups"].remove(pickup)
            if pickup["type"] == "boost":
                state["boost"] = min(MAX_BOOST, state["boost"] + 42)
                add_particle(state, (pickup["x"], pickup["y"]), YELLOW, 14)
            else:
                state["shield"] = 5.0
                add_particle(state, (pickup["x"], pickup["y"]), CYAN, 14)
        elif pickup["y"] > HEIGHT + 30:
            state["pickups"].remove(pickup)
    if int(state["distance"]) // 100 > state["last_milestone"]:
        state["last_milestone"] = int(state["distance"]) // 100
        state["score"] += 50
    update_particles(state, dt)


def draw_hud(state, high_score):
    pygame.draw.rect(screen, (7, 13, 22), (0, 0, WIDTH, 72))
    pygame.draw.rect(screen, (12, 27, 39), (14, 10, 225, 52), border_radius=6)
    pygame.draw.rect(screen, (12, 27, 39), (WIDTH - 272, 10, 258, 52), border_radius=6)
    pygame.draw.line(screen, (34, 93, 101), (14, 62), (239, 62), 1)
    pygame.draw.line(screen, (34, 93, 101), (WIDTH - 272, 62), (WIDTH - 14, 62), 1)
    pygame.draw.line(screen, CYAN, (0, 71), (WIDTH, 71), 2)
    draw_text(f"SCORE  {state['score']:06d}", FONT, WHITE, (24, 20), "topleft")
    draw_text(f"BEST  {high_score:06d}", SMALL, (137, 155, 168), (25, 48), "topleft")
    draw_text(f"LIVES  {state['lives']}/3", SMALL, PINK, (175, 48), "topleft")
    draw_text(f"DISTANCE  {int(state['distance']):04d}m", SMALL, WHITE, (WIDTH // 2, 20))
    pygame.draw.rect(screen, (30, 42, 52), (WIDTH - 250, 47, 120, 9), border_radius=4)
    base_boost = min(100, state["boost"])
    pygame.draw.rect(screen, YELLOW, (WIDTH - 250, 47, int(120 * base_boost / 100), 9), border_radius=4)
    if state["boost"] > 100:
        extra_width = int(45 * (state["boost"] - 100) / (MAX_BOOST - 100))
        pygame.draw.rect(screen, (255, 242, 157), (WIDTH - 130, 47, extra_width, 9), border_radius=4)
    draw_text("NITRO", SMALL, YELLOW, (WIDTH - 258, 52), "midright")
    if state["boosting"]:
        draw_text("BOOST ACTIVE", SMALL, YELLOW, (WIDTH - 24, 20), "topright")
    elif state["distance"] >= SPEED_CAP_DISTANCE:
        draw_text("MAX VELOCITY", SMALL, CYAN, (WIDTH - 24, 20), "topright")


def draw_game(state, high_score):
    offset = random.uniform(-state["shake"] * 8, state["shake"] * 8)
    draw_background(state, offset)
    for car in state["traffic"]:
        draw_car(car)
    for pickup in state["pickups"]:
        draw_pickup(pickup)
    if state["invincible"] <= 0 or int(state["invincible"] * 12) % 2:
        if state["boosting"]:
            draw_nitro_effect(state["player"])
        draw_car(state["player"], state["shield"] > 0)
    draw_particles(state)
    draw_hud(state, high_score)
    if state["combo"] > 1:
        draw_text(f"x{state['combo']} COMBO", SUBTITLE, YELLOW, (WIDTH // 2, 103))
    if state["shield"] > 0:
        draw_text(f"SHIELD {state['shield']:0.1f}s", SMALL, CYAN, (WIDTH // 2, HEIGHT - 22))


def draw_explosion(state):
    if state["explosion_started"] is None:
        return
    elapsed = (pygame.time.get_ticks() - state["explosion_started"]) / 1000
    if elapsed >= 1.8:
        return
    centre = state["player"]["rect"].center
    animation = state["death_animation"]
    radius = int(25 + elapsed * 230)
    if animation == "shockwave":
        pygame.draw.circle(screen, CYAN, centre, radius, 8)
        pygame.draw.circle(screen, WHITE, centre, max(8, radius - 35), 2)
        for angle in range(0, 360, 45):
            direction = pygame.Vector2(1, 0).rotate(angle)
            pygame.draw.line(screen, CYAN, centre + direction * radius,
                             centre + direction * (radius + 30), 3)
    elif animation == "fireworks":
        for angle in range(0, 360, 30):
            direction = pygame.Vector2(1, 0).rotate(angle)
            pygame.draw.line(screen, PINK, centre + direction * radius,
                             centre + direction * (radius + 34), 4)
        pygame.draw.circle(screen, YELLOW, centre, max(8, int(42 - elapsed * 14)), 5)
    elif animation == "pixel":
        for angle in range(0, 360, 30):
            direction = pygame.Vector2(1, 0).rotate(angle)
            point = centre + direction * radius
            pygame.draw.rect(screen, YELLOW, (int(point.x - 7), int(point.y - 7), 14, 14))
        pygame.draw.rect(screen, WHITE, (centre[0] - 15, centre[1] - 15, 30, 30), 4)
    elif animation == "blackhole":
        pygame.draw.circle(screen, (12, 8, 28), centre, max(10, radius - 28))
        pygame.draw.circle(screen, (130, 90, 227), centre, radius, 5)
        pygame.draw.circle(screen, PINK, centre, max(8, radius - 48), 3)
    elif animation == "laser":
        pulse = int((elapsed * 10) % 2)
        for index in range(-3, 4):
            y = centre[1] + index * 18 + pulse * 5
            pygame.draw.line(screen, (255, 80, 120), (centre[0] - radius, y),
                             (centre[0] + radius, y), 3)
        pygame.draw.line(screen, WHITE, (centre[0] - radius, centre[1] - radius),
                         (centre[0] + radius, centre[1] + radius), 3)
    else:
        pygame.draw.circle(screen, YELLOW, centre, radius, 5)
        pygame.draw.circle(screen, RED, centre, max(8, radius - 20), 4)
        if elapsed < .7:
            pygame.draw.circle(screen, (255, 240, 180), centre, int(35 + elapsed * 80))


def menu_screen(high_score, profile):
    pulse = (math.sin(pygame.time.get_ticks() / 280) + 1) / 2
    screen.fill((5, 11, 22))
    draw_light_beams((45, 224, 213), 18)
    pygame.draw.rect(screen, (12, 44, 55), (0, 0, WIDTH, HEIGHT), 8)
    draw_checkered_strip(pygame.Rect(0, 18, WIDTH, 18), 18)
    draw_checkered_strip(pygame.Rect(0, HEIGHT - 18, WIDTH, 18), 18)
    for y in range(0, HEIGHT, 40):
        pygame.draw.line(screen, (9, 28, 42), (0, y), (WIDTH, y), 1)
    for x in range(-HEIGHT, WIDTH, 80):
        pygame.draw.line(screen, (11, 32, 43), (x, HEIGHT), (x + HEIGHT // 2, 0), 2)
    pygame.draw.circle(screen, (17, 72, 79), (WIDTH // 2, 230), int(170 + pulse * 12), 2)
    pygame.draw.circle(screen, (17, 72, 79), (WIDTH // 2, 230), int(205 + pulse * 18), 1)
    draw_text("HIGHWAY", TITLE, (9, 45, 58), (WIDTH // 2 + 5, 195))
    draw_text("HIGHWAY", TITLE, WHITE, (WIDTH // 2, 190))
    draw_text("HOOLIGANS", TITLE, PINK, (WIDTH // 2, 260))
    draw_text("NIGHT RUN // TOKYO AFTER DARK", SUBTITLE, CYAN, (WIDTH // 2, 325))
    draw_text("NEON DISTRICT 04  /  CITY CIRCUIT", SMALL, (255, 208, 76), (WIDTH // 2, 350))
    panel = pygame.Rect(WIDTH // 2 - 280, 370, 560, 124)
    draw_panel(panel, (13, 28, 39), YELLOW)
    draw_corner_frame(panel.inflate(18, 18), (255, 96, 138))
    draw_text("PRESS ENTER TO START", FONT, (255, 208, 76), (WIDTH // 2, 398))
    draw_text("MOVE", SMALL, (137, 155, 168), (WIDTH // 2 - 224, 435))
    draw_text("A / D  or  ARROWS", SMALL, WHITE, (WIDTH // 2 - 116, 435))
    draw_text("BOOST", SMALL, (137, 155, 168), (WIDTH // 2 + 55, 435))
    draw_text("SPACE", SMALL, YELLOW, (WIDTH // 2 + 126, 435))
    draw_text("ESC  PAUSE", SMALL, CYAN, (WIDTH // 2, 466))
    draw_text("S  SHOP", SMALL, CYAN, (WIDTH // 2 + 150, 466))
    draw_text(f"ALL-TIME BEST  {high_score:06d}", SMALL, (137, 155, 168), (WIDTH // 2, 535))
    draw_text("COINS  {0:04d}".format(profile["coins"]), SMALL, YELLOW,
              (WIDTH // 2, 557))
    draw_text("// SYSTEM READY //", SMALL, (70, 220, 198), (WIDTH // 2, 578))
    draw_text("LIGHTS ON  //  ENGINE HOT  //  ROAD OPEN", SMALL, (137, 155, 168),
              (WIDTH // 2, 603))
    draw_scanlines(10)


def shop_items(profile, high_score):
    return [("CAR SKINS", skin, "skin", skin["id"] in profile["owned_skins"],
             high_score >= skin["min_score"])
            for skin in SKINS] + [("DEATH ANIMATIONS", animation, "death",
                                   animation["id"] in profile["owned_deaths"],
                                   high_score >= animation["min_score"])
                                  for animation in DEATH_ANIMATIONS]


def shop_screen(profile, high_score, selected):
    screen.fill((5, 11, 22))
    draw_light_beams(PINK, 16)
    draw_text("NIGHT MARKET", TITLE, WHITE, (WIDTH // 2, 72))
    draw_text("BUY THE LOOK. OWN THE EXIT.", SMALL, CYAN, (WIDTH // 2, 126))
    draw_text(f"WALLET  {profile['coins']:04d} COINS", FONT, YELLOW, (WIDTH - 28, 28), "topright")
    items = shop_items(profile, high_score)
    row_height = 34
    for index, (category, item, item_type, owned, unlocked) in enumerate(items):
        section_offset = 18 if item_type == "death" else 0
        y = 155 + index * row_height + section_offset
        is_selected = index == selected
        colour = YELLOW if is_selected else (56, 91, 104)
        panel = pygame.Rect(170, y, 620, 29)
        draw_panel(panel, (13, 28, 39) if is_selected else (9, 20, 31), colour)
        if index == 0 or item_type != items[index - 1][2]:
            draw_text(category, SMALL, PINK if item_type == "death" else CYAN, (182, y - 14), "topleft")
        pygame.draw.rect(screen, item["colour"], (190, y + 7, 14, 14), border_radius=3)
        draw_text(item["name"], SMALL, WHITE, (220, y + 14), "midleft")
        requirement = "NO SCORE GATE" if item["min_score"] == 0 else f"REQ SCORE {item['min_score']}"
        requirement_colour = (96, 125, 135) if unlocked else PINK
        draw_text(requirement, SMALL, requirement_colour, (500, y + 14), "midleft")
        if not unlocked:
            status, status_colour = "LOCKED", PINK
        elif profile[item_type] == item["id"]:
            status, status_colour = "EQUIPPED", CYAN
        elif owned:
            status, status_colour = "EQUIP", WHITE
        else:
            status, status_colour = f"{item['price']} COINS", YELLOW
        draw_text(status, SMALL, status_colour, (760, y + 14), "midright")
        preview_center = (825, y + 14)
        if item_type == "skin":
            draw_skin_preview(item, preview_center)
        else:
            draw_death_preview(item, preview_center)
    draw_text("UP / DOWN  SELECT     ENTER  BUY / EQUIP     M  MENU", SMALL,
              (137, 155, 168), (WIDTH // 2, HEIGHT - 28))
    draw_scanlines(10)


def use_shop_selection(profile, high_score, selected):
    _, item, item_type, owned, unlocked = shop_items(profile, high_score)[selected]
    owned_key = "owned_skins" if item_type == "skin" else "owned_deaths"
    if not unlocked:
        return
    if owned:
        profile[item_type] = item["id"]
        save_profile(profile)
    elif profile["coins"] >= item["price"]:
        profile["coins"] -= item["price"]
        profile[owned_key].append(item["id"])
        profile[item_type] = item["id"]
        save_profile(profile)


def overlay(title, subtitle, colour):
    overlay_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay_surface.fill((5, 10, 17, 220))
    screen.blit(overlay_surface, (0, 0))
    draw_light_beams(colour, 16)
    draw_checkered_strip(pygame.Rect(0, 104, WIDTH, 14), 14)
    draw_checkered_strip(pygame.Rect(0, HEIGHT - 28, WIDTH, 14), 14)
    panel = pygame.Rect(WIDTH // 2 - 250, 205, 500, 190)
    draw_panel(panel, (12, 24, 37), colour)
    draw_corner_frame(panel.inflate(22, 22), YELLOW if colour == PINK else PINK)
    draw_text("// NIGHT SHIFT HOLD //", SMALL, (115, 180, 188), (WIDTH // 2, 224))
    draw_text(title, TITLE, colour, (WIDTH // 2, 260))
    draw_text(subtitle, SMALL, WHITE, (WIDTH // 2, 345))
    draw_text("CITY LIGHTS STANDING BY  /  DRIFT LOCKED", SMALL, YELLOW, (WIDTH // 2, 375))
    draw_scanlines(14)


def main():
    start_music()
    profile = load_profile()
    state, mode, high_score = new_game(profile), "menu", load_high_score()
    shop_selected = 0
    while True:
        dt = min(clock.tick(FPS) / 1000, .05)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and mode in ("menu", "gameover"):
                    state, mode = new_game(profile), "playing"
                elif mode == "menu" and event.key == pygame.K_s:
                    shop_selected = 0
                    mode = "shop"
                elif mode == "shop" and event.key in (pygame.K_UP, pygame.K_w):
                    shop_selected = (shop_selected - 1) % len(shop_items(profile, high_score))
                elif mode == "shop" and event.key in (pygame.K_DOWN, pygame.K_s):
                    shop_selected = (shop_selected + 1) % len(shop_items(profile, high_score))
                elif mode == "shop" and event.key == pygame.K_RETURN:
                    use_shop_selection(profile, high_score, shop_selected)
                elif mode == "shop" and event.key in (pygame.K_m, pygame.K_ESCAPE):
                    mode = "menu"
                elif mode == "playing" and event.key in (pygame.K_LEFT, pygame.K_a):
                    switch_player_lane(state["player"], -1)
                elif mode == "playing" and event.key in (pygame.K_RIGHT, pygame.K_d):
                    switch_player_lane(state["player"], 1)
                elif mode in ("paused", "gameover") and event.key == pygame.K_m:
                    mode = "menu"
                elif event.key == pygame.K_ESCAPE and mode in ("playing", "paused"):
                    mode = "paused" if mode == "playing" else "playing"
        if mode == "playing":
            update_game(state, dt)
            if state["lives"] <= 0:
                high_score = max(high_score, state["score"])
                save_high_score(high_score)
                state["coins_earned"] = award_run_coins(profile, state["score"])
                state["explosion_started"] = pygame.time.get_ticks()
                stop_music()
                mode = "gameover"
        if mode in ("playing", "paused", "gameover"):
            draw_game(state, high_score)
            if mode == "paused":
                overlay("PAUSED", "ESC  RESUME     M  MAIN MENU", CYAN)
            elif mode == "gameover":
                overlay("RUN OVER", f"SCORE {state['score']:06d}   BEST {high_score:06d}   //   ENTER RETRY   M MENU", PINK)
                draw_text(f"+{state['coins_earned']} COINS   /   WALLET {profile['coins']}", SMALL,
                          YELLOW, (WIDTH // 2, 405))
                draw_explosion(state)
        elif mode == "shop":
            shop_screen(profile, high_score, shop_selected)
        else:
            menu_screen(high_score, profile)
        pygame.display.flip()


if __name__ == "__main__":
    main()