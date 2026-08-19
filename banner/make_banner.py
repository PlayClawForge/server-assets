#!/usr/bin/env python3
"""TBI FiveM browser banner generator — v2 (self-contained).

Run from anywhere:  python3 banner/make_banner.py
Reads  : banner/frames/f00..f29.png  (pristine frames of the original design — committed)
Writes : tbi-banner-animated.gif     (repo root — the live banner via raw URL hot-swap)
Font   : banner/DejaVuSans-Bold.ttf  (bundled, redistributable) with system fallback.

To change the banner text: edit the CONFIG block, rerun, commit the new GIF.
The design (wordmark, chevrons, subline, chart animation) is carried by the source
frames and is never redrawn — only the two text zones below are repainted.
v2 fixes vs the first committed version: correct right-zone bounds (v1's detector
ate the chart arrow), true fade-in frame (17, not 0), fitted copy with a hard
width assertion so text can never collide with the chart again.
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import sys

# ── CONFIG — edit these, rerun ──────────────────────────────────────────────
PAGE2_LINE1 = "RECORDING STUDIO  \u00b7  STAGE NIGHTS"
PAGE2_LINE2 = "MUSIC CITY  \u00b7  DRONES OVERHEAD"
RIGHT_TOP   = "INVITE-ONLY"        # at public launch e.g. "PUBLIC LAUNCH"
RIGHT_BOT   = "BETA LIVE"          #                    e.g. "JOIN THE CITY"
PAGE1_HOLD_MS, PAGE2_HOLD_MS = 900, 2000
# ────────────────────────────────────────────────────────────────────────────

HERE  = Path(__file__).resolve().parent          # .../banner
ROOT  = HERE.parent                              # repo root
OUT   = ROOT / "tbi-banner-animated.gif"
FRAMES= HERE / "frames"

# geometry — measured against the source frames (1865x108); do not change
# without re-measuring: rz was the v1 bug (oversized box ate the chart arrow).
BZ = (1015, 18, 1495, 105)     # bullet text zone (right edge stops before chart)
RZ = (1665, 27, 1814, 81)      # right stacked-text zone (FOUNDING -> beta status)
RIGHT_START = 17               # frame where right text fades in (matches original)
CHART_X = 1520                 # hard stop: no bullet text may cross this
TEAL, WHITE, ORANGE = (94, 224, 196), (245, 245, 245), (255, 148, 54)

def load_font(size):
    for p in (HERE / "DejaVuSans-Bold.ttf",
              Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
              Path("C:/Windows/Fonts/arialbd.ttf")):
        if p.exists():
            return ImageFont.truetype(str(p), size)
    sys.exit("no usable bold font found — keep DejaVuSans-Bold.ttf next to this script")

fS, fR = load_font(17), load_font(19)

def tracked(d, xy, s, f, fill, t=2):
    x, y = xy
    for ch in s:
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + t

def tw(d, s, f, t=2):
    return sum(d.textlength(c, font=f) + t for c in s) - t

frames = [Image.open(FRAMES / f"f{i:02d}.png").convert("RGB") for i in range(30)]
assert frames[0].size == (1865, 108), "unexpected source frame size"
b_plate = frames[1].crop(BZ)          # clean background plates from an early frame
r_plate = frames[1].crop(RZ)

_meas = ImageDraw.Draw(frames[0].copy())
MAXW = CHART_X - (BZ[0] + 22) - 12
for s in (PAGE2_LINE1, PAGE2_LINE2):
    w = tw(_meas, s, fS)
    assert w <= MAXW, f"line too wide for the zone: {s!r} ({w:.0f}px > {MAXW}px) — shorten it"

def draw_right(img, alpha=1.0):
    d = ImageDraw.Draw(img)
    cx = (RZ[0] + RZ[2]) // 2
    col = lambda c: tuple(int(v * alpha) for v in c)
    tracked(d, (cx - tw(d, RIGHT_TOP, fR) // 2, 31), RIGHT_TOP, fR, col(WHITE))
    tracked(d, (cx - tw(d, RIGHT_BOT, fR) // 2, 57), RIGHT_BOT, fR, col(ORANGE))

def draw_bullets(img, lines):
    d = ImageDraw.Draw(img)
    for s, y in zip(lines, (30, 62)):
        d.ellipse((BZ[0] + 4, y + 6, BZ[0] + 11, y + 13), fill=TEAL)
        tracked(d, (BZ[0] + 22, y), s, fS, TEAL)

out, durs = [], []
for i, fr in enumerate(frames[:29]):                       # original growth animation
    f = fr.copy()
    if i >= RIGHT_START:                                   # beta-status text, original fade
        f.paste(r_plate, RZ)
        draw_right(f, min(1.0, (i - RIGHT_START + 1) / 4))
    out.append(f); durs.append(100)

hold1 = frames[29].copy()
hold1.paste(r_plate, RZ); draw_right(hold1)
out.append(hold1); durs.append(PAGE1_HOLD_MS)              # page 1: economy bullets

page2 = hold1.copy()
page2.paste(b_plate, (BZ[0], BZ[1]))
draw_bullets(page2, [PAGE2_LINE1, PAGE2_LINE2])
for k in range(1, 4):                                      # crossfade
    out.append(Image.blend(hold1, page2, k / 4)); durs.append(80)
out.append(page2); durs.append(PAGE2_HOLD_MS)              # page 2: music / drones

q = [f.quantize(colors=256, method=Image.MEDIANCUT) for f in out]
q[0].save(OUT, save_all=True, append_images=q[1:], duration=durs, loop=0, optimize=True)
print(f"wrote {OUT.name}: {len(out)} frames, {sum(durs)/1000:.2f}s loop, {OUT.stat().st_size} bytes")
