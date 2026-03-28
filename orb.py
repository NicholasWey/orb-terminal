#!/usr/bin/env python3
"""Animated ASCII orb splash screen for your terminal."""

import sys
import time
import math
import signal
import os

# --splash: show full-screen splash then exit (auto-exits after 3s or keypress)
# --panel: persistent panel mode (launched as a WT native side pane)
# --name NAME: customize the welcome message (default: "my")
SPLASH_FORCE = '--splash' in sys.argv
PANEL_MODE = '--panel' in sys.argv

_name_idx = sys.argv.index('--name') if '--name' in sys.argv else -1
TERMINAL_NAME = sys.argv[_name_idx + 1] if _name_idx >= 0 and _name_idx + 1 < len(sys.argv) else 'my'

ORB_CHARS = ' .:-=+*#@'
FPS = 20

if PANEL_MODE:
    W, H, RADIUS = 40, 34, 16.0
else:
    W, H = 45, 19
    RADIUS = 14.0


def noise2d(x, y, t):
    return (
        math.sin(x * 0.8 + t * 1.1) * math.cos(y * 1.2 - t * 0.7)
        + math.sin(x * 1.5 - t * 0.9) * math.cos(y * 0.6 + t * 1.3) * 0.5
        + math.sin(x * 0.4 + y * 0.8 + t * 0.5) * 0.25
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
        lx = math.sin(t * 0.7) * math.cos(t * 0.31) * 0.85 + math.sin(t * 1.13 + 1.7) * 0.15
        ly = math.cos(t * 0.53) * math.sin(t * 0.19 + 0.9) * 0.45 + math.cos(t * 0.83) * 0.1
        lz = 0.5 + math.sin(t * 0.41) * 0.2
    diffuse = max(0.0, nx * lx + ny * ly + nz * lz)
    n = noise2d(nx * 3 + t * 0.3, ny * 3 - t * 0.2, t) * 0.3
    edge = (1.0 - dist / r) ** 0.4
    return max(0.0, min(1.0, diffuse * 0.75 + n * edge + edge * 0.1))


def orb_color(v):
    r = int(v * 160 + (1 - v) * 20)
    g = int(v * 220 + (1 - v) * 30)
    b = int(v * 255 + (1 - v) * 120)
    return f'\033[38;2;{r};{g};{b}m'


def glow_color(i, total, t):
    pos = i / max(total - 1, 1)
    wave = math.sin(t * 2.5 - pos * 4) * 0.5 + 0.5
    base = max(0.0, 1.0 - pos * 1.2)
    intensity = base * 0.6 + wave * 0.4
    r = min(255, int(intensity * 160 + 60))
    g = min(255, int(intensity * 200 + 80))
    b = min(255, int(intensity * 255 + 100))
    return f'\033[38;2;{r};{g};{b}m'


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
            welcome = f"Welcome to {TERMINAL_NAME}'s terminal" if TERMINAL_NAME != 'my' else "Welcome to my terminal"
            text_lines = [
                '',
                welcome,
                '',
                'any key to skip',
                '',
            ]
            text_start = (H - len(text_lines)) // 2
            for i, row in enumerate(orb_rows):
                y = y_start + i
                row = row + '\033[0m  '
                ti = y - text_start
                if 0 <= ti < len(text_lines):
                    line = text_lines[ti]
                    for ci, ch in enumerate(line):
                        row += glow_color(ci, len(line), t) + ch
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

        try:
            import msvcrt
            _msvcrt = msvcrt
        except Exception:
            _msvcrt = None

        max_frames = FPS * 3 if SPLASH_FORCE else None
        frame_count = 0
        top_row = 1

        try:
            while True:
                if _msvcrt:
                    try:
                        if _msvcrt.kbhit():
                            key = _msvcrt.getch()
                            if key in (b'\x00', b'\xe0'):
                                if _msvcrt.kbhit():
                                    _msvcrt.getch()
                            else:
                                cancelled = False

                                # Spin phase: light orbits the orb, blending from current position
                                lx_t = math.sin(t * 0.7) * math.cos(t * 0.31) * 0.85 + math.sin(t * 1.13 + 1.7) * 0.15
                                ly_t = math.cos(t * 0.53) * math.sin(t * 0.19 + 0.9) * 0.45 + math.cos(t * 0.83) * 0.1
                                lz_t = 0.5 + math.sin(t * 0.41) * 0.2
                                start_angle = math.atan2(ly_t / 0.45, lx_t / 0.9)
                                SPIN_FRAMES = 50
                                BLEND_FRAMES = 8
                                for sf in range(SPIN_FRAMES):
                                    if _msvcrt and _msvcrt.kbhit():
                                        _msvcrt.getch()
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
                                        if _msvcrt and _msvcrt.kbhit():
                                            _msvcrt.getch()
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
                top_row = 1
                try:
                    sz = os.get_terminal_size()
                    new_h = min(19, max(5, sz.lines))
                    new_w = min(45, max(10, sz.columns))
                    if new_h != H or new_w != W:
                        H = new_h
                        W = new_w
                        RADIUS = min(W * 0.42, H * 2.1 * 0.42, 14.0)
                    top_row = max(1, (sz.lines - H) // 2 + 1)
                except Exception:
                    pass
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
            cleanup()


if __name__ == '__main__':
    main()
