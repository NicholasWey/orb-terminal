#!/usr/bin/env python3
"""Animated ASCII orb splash screen for Nick's terminal."""

import sys
import time
import math
import signal
import os
import random
import datetime

# ── Dynamic colors from Caelestia terminal palette ────────────────────────────
def _load_colors():
    try:
        conf = {}
        with open(os.path.expanduser('~/.local/share/kitty-dynamic-colors.conf')) as _f:
            for _line in _f:
                _line = _line.strip()
                if not _line or _line.startswith('#'):
                    continue
                _parts = _line.split()
                if len(_parts) == 2:
                    conf[_parts[0]] = _parts[1]
        def _h(k):
            h = conf[k].lstrip('#')
            return (int(h[0:2],16), int(h[2:4],16), int(h[4:6],16))
        return {
            'dark':     _h('color0'),     # deepest shadow
            'shadow':   _h('color1'),     # shadow accent
            'mid':      _h('color2'),     # mid-lit surface
            'bright':   _h('color6'),     # bright zone
            'specular': _h('color7'),     # near-specular
            'text':     _h('foreground'),
        }
    except Exception:
        return {
            'dark':     (20,  20,  20),
            'shadow':   (120, 60,  60),
            'mid':      (80,  140, 200),
            'bright':   (200, 180, 220),
            'specular': (230, 225, 240),
            'text':     (200, 200, 200),
        }

_COLORS = _load_colors()

# Rotating greeting list
GREETINGS = [
    "The best code you'll write today hasn't happened yet.",
    "Build something.",
    "Make the machine do the hard part.",
    "Ready. What are we building?",
    "Connection established.",
    "All systems nominal. Probably.",
    "It works on my machine.",
    "Git status: clean. Let's ruin that.",
    "Something is about to exist that didn't before.",
    "The docs lied. You'll figure it out.",
    "Caffeine levels: nominal.",
]

_greeting_rng = random.Random()
GREETING = _greeting_rng.choice(GREETINGS)
del _greeting_rng

# Seed from current time — unique personality every run
_rng = random.Random(int(time.time()))
_u = _rng.uniform

# Randomised light-source motion parameters
_L = (
    _u(0.5, 0.9), _u(0.2, 0.4), _u(0.75, 0.95),  # lx: f1, f2, a1
    _u(0.9, 1.3), _u(0.0, 6.28), _u(0.10, 0.20),  # lx: f3, p1, a2
    _u(0.4, 0.7), _u(0.15, 0.25), _u(0.0, 6.28),  # ly: f4, f5, p2
    _u(0.35, 0.55), _u(0.6, 1.0), _u(0.08, 0.14), # ly: a3, f6, a4
    _u(0.3, 0.55),                                  # lz: f7
)

# Randomised noise-field parameters
_N = (
    _u(0.6, 1.0), _u(0.9, 1.5), _u(0.8, 1.4), _u(0.5, 1.0),  # nx1, ny1, tf1, tf2
    _u(1.1, 1.9), _u(0.4, 0.9), _u(0.6, 1.2), _u(0.9, 1.6),  # nx2, ny2, tf3, tf4
    _u(0.3, 0.6), _u(0.5, 1.1), _u(0.3, 0.7),                 # nx3, ny3, tf5
)

# --splash: show full-screen splash then exit (auto-exits after 3s or keypress)
# --panel: persistent panel mode (launched as a WT native side pane)
SPLASH_FORCE = '--splash' in sys.argv
PANEL_MODE = '--panel' in sys.argv

ORB_CHARS = ' .:-=+*#@'
FPS = 20

def orb_size_for_terminal():
    """Return (W, H, RADIUS) scaled to fit terminal, never exceeding original 45x19."""
    try:
        sz = os.get_terminal_size()
        TEXT_COLS = 32  # chars needed beside orb for text
        available_w = sz.columns - TEXT_COLS
        available_h = sz.lines - 2
        # Scale down to fit small terminals; cap at 1.0 (original size)
        scale = min(available_h / 19.0, available_w / 45.0, 1.0)
        scale = max(0.4, scale)
        w = max(10, int(45 * scale))
        h = max(5,  int(19 * scale))
        r = min(w * 0.42, h * 2.1 * 0.42)
        return w, h, r
    except Exception:
        return 45, 19, 14.0

if PANEL_MODE:
    try:
        _sz = os.get_terminal_size()
        W, H = max(10, _sz.columns), max(5, _sz.lines)
        RADIUS = min(W * 0.42, H * 2.1 * 0.42)
    except Exception:
        W, H, RADIUS = 40, 34, 16.0
else:
    W, H, RADIUS = orb_size_for_terminal()


def noise2d(x, y, t):
    return (
        math.sin(x * _N[0] + t * _N[2]) * math.cos(y * _N[1] - t * _N[3])
        + math.sin(x * _N[4] - t * _N[6]) * math.cos(y * _N[5] + t * _N[7]) * 0.5
        + math.sin(x * _N[8] + y * _N[9] + t * _N[10]) * 0.25
    ) / 1.75


def orb_sample(x, y, cx, cy, t, radius=None, light_angle=None, light_override=None):
    r = radius if radius is not None else RADIUS
    dx = x - cx
    dy = (y - cy) * 2.1
    dist = math.sqrt(dx * dx + dy * dy)
    if dist >= r:
        return 0.0
    nx = dx / r
    ny = dy / r
    nz = math.sqrt(max(0.0, 1.0 - nx * nx - ny * ny))
    if light_override is not None:
        lx, ly, lz = light_override
    elif light_angle is not None:
        lx = math.cos(light_angle) * 0.9
        ly = math.sin(light_angle) * 0.45
        lz = 0.4
    else:
        lx = math.sin(t * _L[0]) * math.cos(t * _L[1]) * _L[2] + math.sin(t * _L[3] + _L[4]) * _L[5]
        ly = math.cos(t * _L[6]) * math.sin(t * _L[7] + _L[8]) * _L[9] + math.cos(t * _L[10]) * _L[11]
        lz = 0.5 + math.sin(t * _L[12]) * 0.2
    diffuse = max(0.0, nx * lx + ny * ly + nz * lz)
    n = noise2d(nx * 3 + t * 0.3, ny * 3 - t * 0.2, t) * 0.3
    edge = (1.0 - dist / r) ** 0.4
    return max(0.0, min(1.0, diffuse * 0.75 + n * edge + edge * 0.1))


def orb_color(v):
    dr, dg, db = _COLORS['dark']
    sr, sg, sb = _COLORS['shadow']
    mr, mg, mb = _COLORS['mid']
    br, bg, bb = _COLORS['bright']
    xr, xg, xb = _COLORS['specular']
    if v > 0.75:
        # Specular — bright transitions to near-white specular
        p = (v - 0.75) / 0.25
        r = min(255, int(br + p * (xr - br)))
        g = min(255, int(bg + p * (xg - bg)))
        b = min(255, int(bb + p * (xb - bb)))
    elif v > 0.45:
        # Upper mid — mid tone rises to bright
        p = (v - 0.45) / 0.30
        r = int(mr + p * (br - mr))
        g = int(mg + p * (bg - mg))
        b = int(mb + p * (bb - mb))
    elif v > 0.18:
        # Lower mid — shadow accent fades into mid tone
        p = (v - 0.18) / 0.27
        r = int(sr * 0.6 + p * (mr - sr * 0.6))
        g = int(sg * 0.6 + p * (mg - sg * 0.6))
        b = int(sb * 0.6 + p * (mb - sb * 0.6))
    else:
        # Deep shadow — darkest color fades up to shadow accent
        p = v / 0.18
        r = int(dr + p * (sr * 0.6 - dr))
        g = int(dg + p * (sg * 0.6 - dg))
        b = int(db + p * (sb * 0.6 - db))
    return f'\033[38;2;{r};{g};{b}m'


def glow_color(i, total, t, alpha=1.0):
    pos = i / max(total - 1, 1)
    wave = math.sin(t * 2.5 - pos * 4) * 0.5 + 0.5
    base = max(0.0, 1.0 - pos * 1.2)
    intensity = base * 0.6 + wave * 0.4
    br, bg, bb = _COLORS['bright']
    tr, tg, tb = _COLORS['text']
    r = min(255, int((intensity * br + (1 - intensity) * tr * 0.15 + 15) * alpha))
    g = min(255, int((intensity * bg + (1 - intensity) * tg * 0.15 + 15) * alpha))
    b = min(255, int((intensity * bb + (1 - intensity) * tb * 0.15 + 20) * alpha))
    return f'\033[38;2;{r};{g};{b}m'


CHAR_SPEED = 20  # characters revealed per second (1 char/frame at 20fps)

def get_text_lines(t):
    """Return list of text lines for current typewriter state."""
    chars_shown = min(len(GREETING), int(t * CHAR_SPEED))
    typing_done = chars_shown >= len(GREETING)

    # Blinking cursor: 2Hz blink while typing, gone when done
    if not typing_done:
        cursor = '\u2588' if int(t * 4) % 2 == 0 else ' '
        greeting_line = GREETING[:chars_shown] + cursor
    else:
        greeting_line = GREETING

    # Date/time fades in after typing completes
    t_done = len(GREETING) / CHAR_SPEED
    if typing_done:
        fade_frames = (t - t_done) * FPS
        date_alpha = min(1.0, max(0.0, fade_frames / 8))
        now = datetime.datetime.now()
        date_line = now.strftime('%a %b %-d  \u00b7  %-I:%M %p')
    else:
        date_alpha = 0.0
        date_line = ''

    return ['', greeting_line, '', date_line, ''], date_alpha


def render_frame(t, top_row=1, light_angle=None, explode_progress=0.0, light_override=None, show_text=True):
    cx = W // 2
    cy = H // 2
    r = RADIUS * (1.0 + explode_progress * 5.0) if explode_progress > 0 else RADIUS
    render_w = (cx + int(r) + 2) if explode_progress > 0 else W

    # During explosion extend the row range so the expanding orb isn't clipped
    if explode_progress > 0:
        vert_r = int(r / 2.1) + 1
        y_start = cy - vert_r
        y_end = cy + vert_r + 1
        if top_row + y_start < 1:
            y_start = 1 - top_row
        render_top = top_row + y_start
    else:
        y_start = 0
        y_end = H
        render_top = top_row

    orb_rows = []
    for y in range(y_start, y_end):
        row = ''
        for x in range(render_w):
            v = orb_sample(x, y, cx, cy, t, radius=r, light_angle=light_angle, light_override=light_override)
            if explode_progress > 0:
                flash = 1.0 + 1.5 * math.exp(-explode_progress * 12.0)
                fade = max(0.0, (1.0 - explode_progress) ** 0.7)
                v = min(1.0, v * flash) * fade
            ch = ORB_CHARS[int(v * (len(ORB_CHARS) - 1))]
            row += orb_color(v) + ch
        orb_rows.append(row)

    if PANEL_MODE:
        buf = '\033[?2026h\033[H'
        for i in range(H):
            suffix = '\n' if i < H - 1 else ''
            buf += orb_rows[i] + '\033[0m\033[K' + suffix
        buf += '\033[?2026l'
    else:
        buf = f'\033[?25l\033[{render_top};1H'
        if not show_text:
            for row in orb_rows:
                buf += '\033[2K' + row + '\033[0m\n'
        else:
            text_lines, date_alpha = get_text_lines(t)
            text_start = (H - len(text_lines)) // 2
            for i, row in enumerate(orb_rows):
                y = y_start + i
                row = row + '\033[0m  '
                ti = y - text_start
                if 0 <= ti < len(text_lines):
                    line = text_lines[ti]
                    alpha = date_alpha if ti == 3 else 1.0
                    for ci, ch in enumerate(line):
                        row += glow_color(ci, len(line), t, alpha=alpha) + ch
                buf += row + '\033[0m\033[K\n'
    return buf


def cleanup(sig=None, frame=None):
    sys.stdout.write('\033[?25h\033[?1049l\033[0m')
    sys.stdout.flush()
    sys.exit(0)


def main():
    if not sys.stdout.isatty():
        return

    os.system('')  # Enable ANSI escape codes on Windows

    global W, H, RADIUS
    frame_time = 1.0 / FPS
    t = 0.0

    if PANEL_MODE:
        try:
            _sz = os.get_terminal_size()
            H = max(5, _sz.lines)
            W = max(10, _sz.columns)
            RADIUS = min(W * 0.42, H * 2.1 * 0.42)
        except Exception:
            pass

        signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
        sys.stdout.write('\033[2J\033[H\033[?25l')
        sys.stdout.flush()
        try:
            while True:
                try:
                    sz = os.get_terminal_size()
                    if sz.lines != H or sz.columns != W:
                        H = max(5, sz.lines)
                        W = max(10, sz.columns)
                        RADIUS = min(W * 0.42, H * 2.1 * 0.42)
                except Exception:
                    pass
                start = time.monotonic()
                sys.stdout.write(render_frame(t))
                sys.stdout.flush()
                t += 0.05
                elapsed = time.monotonic() - start
                remaining = frame_time - elapsed
                if remaining > 0:
                    time.sleep(remaining)
        finally:
            sys.stdout.write('\033[?25h\033[0m')
            sys.stdout.flush()
    else:
        signal.signal(signal.SIGINT, cleanup)
        sys.stdout.write('\033[?1049h\033[?25l\033[H')
        sys.stdout.flush()

        import termios
        import tty
        import select

        def kbhit():
            return select.select([sys.stdin], [], [], 0)[0] != []

        def getch():
            return sys.stdin.read(1).encode()

        old_term = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())

        max_frames = FPS * 3 if SPLASH_FORCE else None
        frame_count = 0
        top_row = 1

        try:
            while True:
                try:
                    if kbhit():
                        key = getch()
                        # swallow escape sequences (arrow keys etc)
                        if key in (b'\x00', b'\x1b'):
                            while kbhit():
                                getch()
                        else:
                            cancelled = False

                            # Spin phase: light orbits the orb, blending from current position
                            lx_t = math.sin(t * _L[0]) * math.cos(t * _L[1]) * _L[2] + math.sin(t * _L[3] + _L[4]) * _L[5]
                            ly_t = math.cos(t * _L[6]) * math.sin(t * _L[7] + _L[8]) * _L[9] + math.cos(t * _L[10]) * _L[11]
                            lz_t = 0.5 + math.sin(t * _L[12]) * 0.2
                            start_angle = math.atan2(ly_t / 0.45, lx_t / 0.9)
                            SPIN_FRAMES = 50
                            BLEND_FRAMES = 8
                            for sf in range(SPIN_FRAMES):
                                if kbhit():
                                    getch()
                                    cancelled = True
                                    break
                                p = sf / SPIN_FRAMES
                                angle = start_angle + (p ** 2) * math.pi * 2
                                lx_c = math.cos(angle) * 0.9
                                ly_c = math.sin(angle) * 0.45
                                lz_c = 0.4
                                if sf < BLEND_FRAMES:
                                    b = (sf + 1) / BLEND_FRAMES
                                    lo = (lx_t*(1-b)+lx_c*b, ly_t*(1-b)+ly_c*b, lz_t*(1-b)+lz_c*b)
                                else:
                                    lo = None
                                start = time.monotonic()
                                sys.stdout.write(render_frame(t, top_row=top_row,
                                    light_angle=angle if lo is None else None,
                                    light_override=lo, show_text=False))
                                sys.stdout.flush()
                                t += 0.05
                                elapsed = time.monotonic() - start
                                remaining = frame_time - elapsed
                                if remaining > 0:
                                    time.sleep(remaining)

                            if not cancelled:
                                # Explosion phase: orb expands and fades
                                EXPLODE_FRAMES = 30
                                sys.stdout.write('\033[?7l')
                                sys.stdout.flush()
                                for ef in range(EXPLODE_FRAMES):
                                    if kbhit():
                                        getch()
                                        cancelled = True
                                        break
                                    ep = (ef + 1) / EXPLODE_FRAMES
                                    angle = start_angle + math.pi * 2 + (ef / EXPLODE_FRAMES) * math.pi * 0.5
                                    start = time.monotonic()
                                    sys.stdout.write(render_frame(t, top_row=top_row,
                                        light_angle=angle, explode_progress=ep, show_text=False))
                                    sys.stdout.flush()
                                    t += 0.05
                                    elapsed = time.monotonic() - start
                                    remaining = frame_time - elapsed
                                    if remaining > 0:
                                        time.sleep(remaining)
                                sys.stdout.write('\033[?7h')
                            break
                except Exception:
                    pass

                if max_frames is not None:
                    frame_count += 1
                    if frame_count >= max_frames:
                        break

                prev_top_row = top_row
                try:
                    sz = os.get_terminal_size()
                    new_w, new_h, new_r = orb_size_for_terminal()
                    if new_h != H or new_w != W:
                        H, W, RADIUS = new_h, new_w, new_r
                        sys.stdout.write('\033[2J')
                    top_row = max(1, (sz.lines - H) // 2 + 1)
                except Exception:
                    top_row = 1
                if top_row != prev_top_row:
                    sys.stdout.write('\033[2J')

                start = time.monotonic()
                sys.stdout.write(render_frame(t, top_row=top_row))
                sys.stdout.flush()
                t += 0.05
                elapsed = time.monotonic() - start
                remaining = frame_time - elapsed
                if remaining > 0:
                    time.sleep(remaining)
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_term)
            cleanup()


if __name__ == '__main__':
    main()
