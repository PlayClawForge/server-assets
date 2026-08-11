#!/usr/bin/env python3
"""TBI banner updater — edits text zones of tbi-banner-animated.gif, preserves design.
Commit this to server-assets/banner/ so the banner has code from now on.
To change features later: edit the lists below, rerun, replace the GIF in the repo root."""
from PIL import Image, ImageDraw, ImageFont, ImageSequence
import os

SRC = "/home/claude/server-assets/tbi-banner-animated.gif"
OUT = "/mnt/user-data/outputs/tbi-banner-animated.gif"
FRD = "/home/claude/frames"          # extracted originals f00..f29 already on disk

# ---- editable content -------------------------------------------------------
PAGE1_KEEP = True                     # original economy bullets stay as page 1
PAGE2_BULLETS = ["MUSIC CITY  \u2014  RECORDING STUDIO LIVE",
                 "STAGE NIGHTS  \u00b7  DRONES OVER THE CITY"]
RIGHT_TOP, RIGHT_BOT = "INVITE-ONLY", "BETA LIVE"   # replaces FOUNDING / CREW OPEN
PAGE1_HOLD_MS, PAGE2_HOLD_MS, XFADE_FRAMES = 900, 2000, 3
# ----------------------------------------------------------------------------

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

frames = [Image.open(f"{FRD}/f{i:02d}.png").convert("RGB") for i in range(30)]
W, H = frames[0].size
last = frames[-1]

def find_zone(img, x0, x1, test):
    """bbox of pixels matching test() inside x-range."""
    px, xs, ys = img.load(), [], []
    for y in range(H):
        for x in range(x0, x1):
            if test(px[x, y]): xs.append(x); ys.append(y)
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None

teal   = lambda p: p[1] > 150 and p[2] > 130 and p[0] < 120          # bullet text
bright = lambda p: sum(p) > 420 or (p[0] > 200 and p[1] > 110 and p[2] < 90)  # white/orange

bz = find_zone(last, 950, 1480, teal)     # bullets zone on the final frame
rz = find_zone(last, 1600, W,   bright)   # right stacked text zone
assert bz and rz, "zone detection failed - inspect frames"
pad = 8
bz = (bz[0]-pad, bz[1]-pad, bz[2]+pad, bz[3]+pad)
rz = (rz[0]-pad, rz[1]-pad, rz[2]+pad, rz[3]+pad)
print("bullet zone:", bz, " right zone:", rz)

# clean background plates from an early frame (zones empty there)
plate = frames[1]
b_plate, r_plate = plate.crop(bz), plate.crop(rz)

# find the frame where the right text first appears (to patch from there on)
def zone_differs(i, zone, ref):
    a = frames[i].crop(zone); import hashlib
    return a.tobytes() != ref.tobytes()
right_start = next((i for i in range(30) if zone_differs(i, rz, r_plate)), 20)
print("right text first appears at frame", right_start)

# text helpers — tracked caps to match the house style
TEAL, WHITE, ORANGE = (94, 224, 196), (245, 245, 245), (255, 148, 54)
def tracked(draw, xy, s, font, fill, track=2):
    x, y = xy
    for ch in s:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + track
def tracked_w(draw, s, font, track=2):
    return sum(draw.textlength(c, font=font) + track for c in s) - track

fS = ImageFont.truetype(FONT, 17)   # bullet size ~ original
fR = ImageFont.truetype(FONT, 19)   # right stack

def draw_bullets(img, lines):
    d = ImageDraw.Draw(img)
    ys = [bz[1] + 6, bz[1] + 6 + 30]
    for s, y in zip(lines, ys):
        d.ellipse((bz[0]+2, y+6, bz[0]+9, y+13), fill=TEAL)
        tracked(d, (bz[0] + 18, y), s, fS, TEAL, track=2)

def draw_right(img):
    d = ImageDraw.Draw(img)
    cx = (rz[0] + rz[2]) // 2
    for s, y, col in [(RIGHT_TOP, rz[1] + 4, WHITE), (RIGHT_BOT, rz[1] + 4 + 26, ORANGE)]:
        tracked(d, (cx - tracked_w(d, s, fR, 2) // 2, y), s, fR, col, 2)

# --- build sequence ---------------------------------------------------------
out, durs = [], []
for i, fr in enumerate(frames[:29]):                 # original growth animation
    f = fr.copy()
    if i >= right_start:                             # swap FOUNDING->INVITE-ONLY
        f.paste(r_plate, rz); draw_right(f)
    out.append(f); durs.append(100)

hold1 = frames[29].copy(); hold1.paste(r_plate, rz); draw_right(hold1)
out.append(hold1); durs.append(PAGE1_HOLD_MS)        # page-1 hold (economy bullets)

page2 = hold1.copy(); page2.paste(b_plate, bz); draw_bullets(page2, PAGE2_BULLETS)
for k in range(1, XFADE_FRAMES + 1):                 # short crossfade to page 2
    out.append(Image.blend(hold1, page2, k / (XFADE_FRAMES + 1))); durs.append(80)
out.append(page2); durs.append(PAGE2_HOLD_MS)        # page-2 hold (music/drones)

q = [f.quantize(colors=256, method=Image.MEDIANCUT) for f in out]
q[0].save(OUT, save_all=True, append_images=q[1:], duration=durs, loop=0, optimize=True)
print("frames:", len(out), "| total loop:", sum(durs) / 1000, "s | bytes:", os.path.getsize(OUT))
page2.save("/home/claude/proof_page2.png"); hold1.save("/home/claude/proof_page1.png")
