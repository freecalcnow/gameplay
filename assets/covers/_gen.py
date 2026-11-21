#!/usr/bin/env python3
"""Generate 100 DISTINCT original SVG cover artworks for Arcadia Global 100.

Reads ../games.json, writes <id>.svg (960x540) into this directory.
Every cover is drawn from scratch with SVG shapes only -- no copied art,
no emoji, no text except single letters/digits as game pieces (letter
tiles, sudoku cells, number pads). Each game's two palette colours from
games.json are used so covers stay coherent with the site.

Usage: python3 _gen.py
"""
import hashlib
import json
import math
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAMES = json.loads((HERE.parent.parent / "games.json").read_text())
W, H = 960, 540


# ---------------------------------------------------------------- colours
def hx(c):
    c = c.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))


def rgb(t):
    return "#%02x%02x%02x" % (max(0, min(255, int(t[0]))),
                              max(0, min(255, int(t[1]))),
                              max(0, min(255, int(t[2]))))


def mix(a, b, t):
    A, B = hx(a), hx(b)
    return rgb(tuple(A[i] + (B[i] - A[i]) * t for i in range(3)))


def shade(c, f):
    """f>0 lighten toward white, f<0 darken toward black."""
    return mix(c, "#ffffff", f) if f >= 0 else mix(c, "#000000", -f)


# ---------------------------------------------------------------- scene
class Scene:
    def __init__(self, game, rng):
        self.g = game
        self.rng = rng
        self.c1, self.c2 = game["colors"]
        self.el = []
        self.defs = []
        self._gid = 0

    # -- low level ------------------------------------------------------
    def _a(self, attrs):
        out = []
        for k, v in attrs.items():
            k = k.rstrip("_").replace("_", "-")
            out.append(f'{k}="{v}"')
        return " ".join(out)

    def add(self, tag, **attrs):
        self.el.append(f"<{tag} {self._a(attrs)}/>")
        return self

    def raw(self, s):
        self.el.append(s)
        return self

    def rect(self, x, y, w, h, fill, rx=None, **kw):
        a = dict(x=round(x, 1), y=round(y, 1), width=round(w, 1),
                 height=round(h, 1), fill=fill)
        if rx is not None:
            a["rx"] = rx
        a.update(kw)
        return self.add("rect", **a)

    def circle(self, cx, cy, r, fill, **kw):
        a = dict(cx=round(cx, 1), cy=round(cy, 1), r=round(r, 1), fill=fill)
        a.update(kw)
        return self.add("circle", **a)

    def ellipse(self, cx, cy, rx, ry, fill, **kw):
        a = dict(cx=round(cx, 1), cy=round(cy, 1), rx=round(rx, 1),
                 ry=round(ry, 1), fill=fill)
        a.update(kw)
        return self.add("ellipse", **a)

    def path(self, d, fill=None, **kw):
        a = dict(d=d)
        if fill is not None:
            a["fill"] = fill
        a.update(kw)
        return self.add("path", **a)

    def poly(self, pts, fill, **kw):
        a = dict(points=" ".join(f"{round(x,1)},{round(y,1)}" for x, y in pts),
                 fill=fill)
        a.update(kw)
        return self.add("polygon", **a)

    def line(self, x1, y1, x2, y2, stroke, sw=4, **kw):
        a = dict(x1=round(x1, 1), y1=round(y1, 1), x2=round(x2, 1),
                 y2=round(y2, 1), stroke=stroke, stroke_width=sw)
        a.update(kw)
        return self.add("line", **a)

    def text(self, x, y, s, size, fill, weight="bold", anchor="middle",
             family="Arial, Helvetica, sans-serif"):
        self.el.append(
            f'<text x="{round(x,1)}" y="{round(y,1)}" font-family="{family}" '
            f'font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'text-anchor="{anchor}">{s}</text>')
        return self

    def grad(self, gid, stops, x1="0", y1="0", x2="0", y2="1"):
        st = "".join(
            f'<stop offset="{o}" stop-color="{c}"'
            + (f' stop-opacity="{op}"' if op is not None else "")
            + "/>" for o, c, op in stops)
        self.defs.append(
            f'<linearGradient id="{gid}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">{st}</linearGradient>')
        return gid

    # -- backgrounds ----------------------------------------------------
    def sky(self, kind=None):
        """kind: day | sunset | night | dawn | none (flat)."""
        r = self.rng
        kind = kind or r.choice(["day", "day", "sunset", "night", "dawn"])
        c1, c2 = self.c1, self.c2
        if kind == "day":
            self.grad("bg", [(0, mix(c1, "#ffffff", .55), None),
                             (1, mix(c2, "#ffffff", .25), None)])
            self.rect(0, 0, W, H, "url(#bg)")
            self.sun(r.choice([True, False]))
            self.clouds(r.randint(2, 4))
        elif kind == "sunset":
            self.grad("bg", [(0, mix(c2, "#ffb347", .25), None),
                             (.55, mix(c1, "#ff8c69", .3), None),
                             (1, shade(c2, -.25), None)])
            self.rect(0, 0, W, H, "url(#bg)")
            self.circle(r.randint(620, 780), r.randint(150, 210), r.randint(46, 62),
                        mix(c1, "#ffd27d", .5), opacity=".95")
            self.clouds(r.randint(1, 3), tint=mix(c1, "#ffffff", .4))
        elif kind == "night":
            self.grad("bg", [(0, shade(c2, -.45), None),
                             (1, shade(c2, -.05), None)])
            self.rect(0, 0, W, H, "url(#bg)")
            self.stars(r.randint(14, 26))
            self.moon()
            self.clouds(r.randint(1, 2), tint=shade(c2, .25))
        elif kind == "dawn":
            self.grad("bg", [(0, mix(c1, "#ffffff", .35), None),
                             (.6, mix(c1, c2, .5), None),
                             (1, mix(c2, "#ffffff", .1), None)])
            self.rect(0, 0, W, H, "url(#bg)")
            self.sun(False, low=True)
            self.clouds(r.randint(2, 3))
        else:  # flat
            self.grad("bg", [(0, mix(c1, "#ffffff", .45), None),
                             (1, mix(c2, "#ffffff", .12), None)])
            self.rect(0, 0, W, H, "url(#bg)")
        if r.random() < 0.5:
            self.birds(r.randint(1, 3))
        return self

    def sun(self, rays=True, low=False):
        r = self.rng
        x = r.randint(90, 260) if not low else r.randint(380, 620)
        y = r.randint(70, 130) if not low else r.randint(190, 240)
        rad = r.randint(38, 52)
        col = mix(self.c1, "#ffe9a8", .55)
        if rays:
            for i in range(8):
                a = i * math.pi / 4 + .2
                self.line(x + math.cos(a) * (rad + 8), y + math.sin(a) * (rad + 8),
                          x + math.cos(a) * (rad + 24), y + math.sin(a) * (rad + 24),
                          col, sw=5, stroke_linecap="round", opacity=".8")
        self.circle(x, y, rad, col)
        self.circle(x, y, rad * .72, mix(self.c1, "#ffffff", .55))
        return self

    def moon(self):
        r = self.rng
        x, y = r.randint(720, 850), r.randint(70, 130)
        self.circle(x, y, 42, mix(self.c1, "#ffffff", .6))
        self.circle(x - 12, y - 8, 9, mix(self.c1, "#ffffff", .35))
        self.circle(x + 10, y + 12, 6, mix(self.c1, "#ffffff", .35))
        self.circle(x + 14, y - 14, 5, mix(self.c1, "#ffffff", .35))
        return self

    def stars(self, n):
        r = self.rng
        for _ in range(n):
            x, y = r.randint(20, 940), r.randint(15, 300)
            s = r.choice([2, 2.5, 3, 4])
            col = r.choice(["#ffffff", mix(self.c1, "#ffffff", .7)])
            self.circle(x, y, s, col, opacity=round(r.uniform(.5, 1), 2))
            if r.random() < .3:
                self.line(x - s * 2.4, y, x + s * 2.4, y, col, sw=1.2, opacity=".7")
                self.line(x, y - s * 2.4, x, y + s * 2.4, col, sw=1.2, opacity=".7")
        return self

    def clouds(self, n, tint=None):
        r = self.rng
        tint = tint or "#ffffff"
        for _ in range(n):
            x, y = r.randint(40, 900), r.randint(30, 170)
            s = r.uniform(.6, 1.25)
            op = round(r.uniform(.5, .85), 2)
            for dx, dy, rr in [(-38, 6, 22), (0, -6, 28), (38, 6, 22), (0, 10, 24)]:
                self.circle(x + dx * s, y + dy * s, rr * s, tint, opacity=op)
        return self

    def birds(self, n):
        r = self.rng
        col = shade(self.c2, -.3)
        for _ in range(n):
            x, y = r.randint(120, 840), r.randint(60, 180)
            s = r.uniform(.7, 1.3)
            self.path(f"M{x-14*s:.0f} {y:.0f} Q{x-6*s:.0f} {y-9*s:.0f} {x:.0f} {y:.0f} "
                      f"Q{x+6*s:.0f} {y-9*s:.0f} {x+14*s:.0f} {y:.0f}",
                      fill="none", stroke=col, stroke_width=3,
                      stroke_linecap="round", opacity=".55")
        return self

    def hills(self, y=430, col=None, col2=None):
        r = self.rng
        col = col or shade(self.c2, .15)
        col2 = col2 or shade(self.c2, -.05)
        self.path(f"M0 {y-40} Q{r.randint(150,250)} {y-r.randint(90,140)} "
                  f"{r.randint(380,480)} {y-30} T960 {y-50} V540 H0Z", fill=col, opacity=".8")
        self.path(f"M0 {y+10} Q{r.randint(200,300)} {y-r.randint(40,80)} "
                  f"{r.randint(500,620)} {y} T960 {y-20} V540 H0Z", fill=col2)
        return self

    # -- reusable props -------------------------------------------------
    def gem(self, cx, cy, r, kind, fill):
        """Gem shapes: circle, diamond, square, triangle, star, hex."""
        dark = shade(fill, -.25)
        if kind == "circle":
            self.circle(cx, cy, r, fill)
            self.circle(cx - r * .3, cy - r * .3, r * .3, "#ffffff", opacity=".55")
        elif kind == "diamond":
            self.poly([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill)
            self.poly([(cx, cy - r), (cx + r * .4, cy - r * .2), (cx, cy + r * .3),
                       (cx - r * .4, cy - r * .2)], "#ffffff", opacity=".35")
        elif kind == "square":
            self.rect(cx - r * .85, cy - r * .85, r * 1.7, r * 1.7, fill, rx=r * .3)
            self.rect(cx - r * .5, cy - r * .5, r * .6, r * .6, "#ffffff", rx=r * .2, opacity=".4")
        elif kind == "triangle":
            self.poly([(cx, cy - r), (cx + r, cy + r * .8), (cx - r, cy + r * .8)], fill)
            self.circle(cx, cy + r * .2, r * .25, "#ffffff", opacity=".5")
        elif kind == "star":
            pts = []
            for i in range(10):
                a = -math.pi / 2 + i * math.pi / 5
                rr = r if i % 2 == 0 else r * .45
                pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
            self.poly(pts, fill)
            self.circle(cx, cy, r * .22, "#ffffff", opacity=".5")
        else:  # hex
            pts = [(cx + math.cos(math.pi / 3 * i) * r,
                    cy + math.sin(math.pi / 3 * i) * r) for i in range(6)]
            self.poly(pts, fill)
            self.circle(cx - r * .25, cy - r * .25, r * .22, "#ffffff", opacity=".5")
        self.circle(cx, cy, r, "none", stroke=dark, stroke_width=2, opacity=".4")
        return self

    def flag(self, x, y, h=64, col=None):
        col = col or self.c1
        self.line(x, y, x, y - h, shade(self.c2, -.3), sw=5, stroke_linecap="round")
        self.poly([(x, y - h), (x + 42, y - h + 12), (x, y - h + 26)], col)
        self.circle(x, y - h - 4, 5, mix(col, "#ffffff", .4))
        return self

    def coin(self, cx, cy, r, col=None):
        col = col or mix(self.c1, "#ffd76a", .45)
        self.circle(cx, cy, r, col)
        self.circle(cx, cy, r * .68, "none", stroke=shade(col, -.3),
                    stroke_width=2.5, opacity=".7")
        self.circle(cx - r * .3, cy - r * .3, r * .2, "#ffffff", opacity=".6")
        return self

    def character(self, x, y, sc=1.0, body=None, pose="stand", acc=None,
                  flip=False):
        """Original blob character: body, face, limbs. (x,y) = feet centre."""
        r = self.rng
        body = body or self.c1
        dark = shade(body, -.35)
        light = mix(body, "#ffffff", .35)
        sgn = -1 if flip else 1
        # legs
        leg = shade(body, -.2)
        if pose == "run":
            self.path(f"M{x-8*sc:.0f} {y-34*sc:.0f} L{x-26*sgn*sc:.0f} {y-2*sc:.0f}",
                      fill="none", stroke=leg, stroke_width=9 * sc,
                      stroke_linecap="round")
            self.path(f"M{x+8*sc:.0f} {y-34*sc:.0f} L{x+22*sgn*sc:.0f} {y-6*sc:.0f}",
                      fill="none", stroke=leg, stroke_width=9 * sc,
                      stroke_linecap="round")
        elif pose == "jump":
            self.path(f"M{x-10*sc:.0f} {y-36*sc:.0f} Q{x-22*sc:.0f} {y-18*sc:.0f} {x-6*sc:.0f} {y-6*sc:.0f}",
                      fill="none", stroke=leg, stroke_width=9 * sc,
                      stroke_linecap="round")
            self.path(f"M{x+10*sc:.0f} {y-36*sc:.0f} Q{x+24*sc:.0f} {y-16*sc:.0f} {x+8*sc:.0f} {y-4*sc:.0f}",
                      fill="none", stroke=leg, stroke_width=9 * sc,
                      stroke_linecap="round")
        elif pose == "push":
            self.path(f"M{x-6*sc:.0f} {y-34*sc:.0f} L{x-24*sgn*sc:.0f} {y-2*sc:.0f}",
                      fill="none", stroke=leg, stroke_width=9 * sc,
                      stroke_linecap="round")
            self.path(f"M{x+8*sc:.0f} {y-34*sc:.0f} L{x+26*sgn*sc:.0f} {y-2*sc:.0f}",
                      fill="none", stroke=leg, stroke_width=9 * sc,
                      stroke_linecap="round")
        else:  # stand
            self.line(x - 9 * sc, y - 34 * sc, x - 9 * sc, y - 2 * sc, leg,
                      sw=9 * sc, stroke_linecap="round")
            self.line(x + 9 * sc, y - 34 * sc, x + 9 * sc, y - 2 * sc, leg,
                      sw=9 * sc, stroke_linecap="round")
        # body blob
        self.ellipse(x, y - 62 * sc, 30 * sc, 34 * sc, body)
        self.ellipse(x - 8 * sc, y - 72 * sc, 12 * sc, 14 * sc, light, opacity=".5")
        # arms
        arm = shade(body, -.15)
        if pose == "jump":
            self.path(f"M{x-24*sc:.0f} {y-70*sc:.0f} Q{x-40*sc:.0f} {y-96*sc:.0f} {x-30*sgn*sc:.0f} {y-104*sc:.0f}",
                      fill="none", stroke=arm, stroke_width=8 * sc, stroke_linecap="round")
            self.path(f"M{x+24*sc:.0f} {y-70*sc:.0f} Q{x+40*sc:.0f} {y-96*sc:.0f} {x+30*sgn*sc:.0f} {y-104*sc:.0f}",
                      fill="none", stroke=arm, stroke_width=8 * sc, stroke_linecap="round")
        elif pose == "push":
            self.path(f"M{x+10*sc:.0f} {y-72*sc:.0f} L{x+38*sgn*sc:.0f} {y-66*sc:.0f}",
                      fill="none", stroke=arm, stroke_width=8 * sc, stroke_linecap="round")
            self.path(f"M{x+8*sc:.0f} {y-58*sc:.0f} L{x+36*sgn*sc:.0f} {y-52*sc:.0f}",
                      fill="none", stroke=arm, stroke_width=8 * sc, stroke_linecap="round")
        elif pose == "run":
            self.path(f"M{x-24*sc:.0f} {y-70*sc:.0f} Q{x-38*sc:.0f} {y-52*sc:.0f} {x-20*sgn*sc:.0f} {y-46*sc:.0f}",
                      fill="none", stroke=arm, stroke_width=8 * sc, stroke_linecap="round")
            self.path(f"M{x+24*sc:.0f} {y-70*sc:.0f} Q{x+40*sc:.0f} {y-84*sc:.0f} {x+26*sgn*sc:.0f} {y-90*sc:.0f}",
                      fill="none", stroke=arm, stroke_width=8 * sc, stroke_linecap="round")
        else:
            self.path(f"M{x-24*sc:.0f} {y-70*sc:.0f} Q{x-34*sc:.0f} {y-52*sc:.0f} {x-22*sc:.0f} {y-44*sc:.0f}",
                      fill="none", stroke=arm, stroke_width=8 * sc, stroke_linecap="round")
            self.path(f"M{x+24*sc:.0f} {y-70*sc:.0f} Q{x+34*sc:.0f} {y-52*sc:.0f} {x+22*sc:.0f} {y-44*sc:.0f}",
                      fill="none", stroke=arm, stroke_width=8 * sc, stroke_linecap="round")
        # face (offset toward facing direction)
        fx = x + 6 * sgn * sc
        self.circle(fx - 8 * sc, y - 70 * sc, 4.5 * sc, "#ffffff")
        self.circle(fx + 9 * sc, y - 70 * sc, 4.5 * sc, "#ffffff")
        self.circle(fx - 7 * sc, y - 70 * sc, 2.2 * sc, dark)
        self.circle(fx + 10 * sc, y - 70 * sc, 2.2 * sc, dark)
        self.path(f"M{fx-6*sc:.0f} {y-56*sc:.0f} Q{fx+2*sc:.0f} {y-48*sc:.0f} {fx+10*sc:.0f} {y-56*sc:.0f}",
                  fill="none", stroke=dark, stroke_width=3 * sc, stroke_linecap="round")
        # cheeks
        self.circle(fx - 15 * sc, y - 58 * sc, 4 * sc, mix(body, "#ff9db0", .5), opacity=".7")
        self.circle(fx + 17 * sc, y - 58 * sc, 4 * sc, mix(body, "#ff9db0", .5), opacity=".7")
        # accessory
        if acc == "hat":
            self.path(f"M{x-26*sc:.0f} {y-88*sc:.0f} Q{x:.0f} {y-118*sc:.0f} {x+26*sc:.0f} {y-88*sc:.0f} Z",
                      fill=shade(self.c2, .1))
            self.rect(x - 32 * sc, y - 92 * sc, 64 * sc, 7 * sc,
                      shade(self.c2, -.15), rx=3 * sc)
        elif acc == "antenna":
            self.line(x, y - 94 * sc, x, y - 112 * sc, dark, sw=3 * sc, stroke_linecap="round")
            self.circle(x, y - 116 * sc, 6 * sc, mix(self.c1, "#ffd76a", .4))
        elif acc == "scarf":
            self.path(f"M{x-24*sc:.0f} {y-88*sc:.0f} Q{x:.0f} {y-76*sc:.0f} {x+24*sc:.0f} {y-88*sc:.0f} "
                      f"L{x+20*sc:.0f} {y-76*sc:.0f} Q{x:.0f} {y-66*sc:.0f} {x-20*sc:.0f} {y-76*sc:.0f} Z",
                      fill=mix(self.c2, "#ffffff", .25))
            self.path(f"M{x+18*sc:.0f} {y-80*sc:.0f} Q{x+34*sgn*sc:.0f} {y-66*sc:.0f} {x+26*sgn*sc:.0f} {y-48*sc:.0f}",
                      fill="none", stroke=mix(self.c2, "#ffffff", .25),
                      stroke_width=7 * sc, stroke_linecap="round")
        elif acc == "headband":
            self.path(f"M{x-28*sc:.0f} {y-84*sc:.0f} Q{x:.0f} {y-96*sc:.0f} {x+28*sc:.0f} {y-84*sc:.0f}",
                      fill="none", stroke=mix(self.c2, "#ffffff", .3),
                      stroke_width=7 * sc, stroke_linecap="round")
        elif acc == "crown":
            self.poly([(x - 20 * sc, y - 88 * sc), (x - 20 * sc, y - 106 * sc),
                       (x - 8 * sc, y - 94 * sc), (x, y - 110 * sc),
                       (x + 8 * sc, y - 94 * sc), (x + 20 * sc, y - 106 * sc),
                       (x + 20 * sc, y - 88 * sc)], mix(self.c1, "#ffd76a", .5))
        return self

    def svg(self):
        defs = f"<defs>{''.join(self.defs)}</defs>" if self.defs else ""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" '
                f'viewBox="0 0 960 540">{defs}{"".join(self.el)}</svg>')


# ================================================================ scenes
def scene_racing(s, g, r):
    name, desc = g["name"].lower(), g["desc"].lower()
    c1, c2 = s.c1, s.c2
    if "boat" in desc or "tide" in name or "harbor" in name:
        # --- speedboat on water
        s.sky("day")
        sea = shade(c2, -.1)
        s.rect(0, 300, W, 240, sea)
        s.path("M0 300 Q120 288 240 300 T480 300 T720 300 T960 300 V540 H0Z",
               fill=mix(c1, "#ffffff", .25), opacity=".5")
        for i in range(5):
            x = r.randint(40, 900)
            s.ellipse(x, 330 + i * 38, r.randint(30, 70), 5, "#ffffff", opacity=".35")
        # floating markers
        for x in (180, 480, 780):
            s.poly([(x, 330), (x + 16, 356), (x - 16, 356)], mix(c1, "#ffd76a", .3))
            s.line(x, 330, x, 356, shade(c2, -.2), sw=4)
        # boat
        bx, by = 480, 400
        s.path(f"M{bx-110} {by} L{bx+110} {by} L{bx+80} {by+34} L{bx-80} {by+34} Z",
               fill=mix(c1, "#ffffff", .15))
        s.rect(bx - 46, by - 42, 92, 42, shade(c2, .1), rx=8)
        s.rect(bx - 30, by - 34, 60, 24, mix(c1, "#ffffff", .5), rx=4)
        s.path(f"M{bx-110} {by+34} Q{bx} {by+70} {bx+130} {by+30}",
               fill="none", stroke="#ffffff", stroke_width=6, opacity=".6",
               stroke_linecap="round")
        s.path(f"M{bx-140} {by+10} L{bx-190} {by+2} M{bx-140} {by+26} L{bx-200} {by+20}",
               fill="none", stroke="#ffffff", stroke_width=5, opacity=".7",
               stroke_linecap="round")
        return
    if "marble" in name:
        # --- rolling marble on a curvy track
        s.sky("day")
        s.hills(470)
        s.path("M0 470 Q240 400 480 470 T960 440 V540 H0Z", fill=shade(c2, .1))
        s.path("M0 500 Q300 450 600 505 T960 480", fill="none",
               stroke=mix(c1, "#ffffff", .3), stroke_width=10, opacity=".8")
        mx, my = 480, 392
        s.circle(mx, my, 46, c1)
        s.circle(mx - 14, my - 14, 14, "#ffffff", opacity=".7")
        s.path(f"M{mx-46} {my} A46 46 0 0 1 {mx+46} {my}",
               fill="none", stroke=shade(c2, -.2), stroke_width=5, opacity=".5")
        for i, (ox, oy) in enumerate([(180, 430), (760, 420), (300, 450)]):
            s.rect(ox - 18, oy - 26, 36, 52, shade(c2, .25), rx=6)
            s.rect(ox - 18, oy - 26, 36, 12, mix(c1, "#ffffff", .3), rx=6)
        s.path(f"M{mx-70} {my+30} L{mx-120} {my+40} M{mx-70} {my+44} L{mx-110} {my+56}",
               fill="none", stroke="#ffffff", stroke_width=5, opacity=".6",
               stroke_linecap="round")
        return
    if "midnight" in name or "night" in desc:
        # --- night traffic, headlights
        s.sky("night")
        s.path("M0 540 L300 260 L660 260 L960 540 Z", fill=shade(c2, -.15))
        s.path("M430 540 L478 260 L482 260 L530 540 Z", fill=shade(c2, .3))
        for i, y in enumerate([300, 360, 430, 510]):
            w = 6 + i * 8
            s.rect(480 - w // 2, y, w, 10 + i * 6, mix(c1, "#ffffff", .6), rx=3)
        # rival cars as tail lights
        for x, y, sc in [(360, 330, .55), (620, 300, .45), (560, 420, .7)]:
            s.rect(x - 34 * sc, y - 26 * sc, 68 * sc, 30 * sc, shade(c2, .2), rx=8 * sc)
            s.circle(x - 20 * sc, y - 8 * sc, 6 * sc, "#ff5a5a")
            s.circle(x + 20 * sc, y - 8 * sc, 6 * sc, "#ff5a5a")
        # hero car from behind
        cx, cy = 480, 470
        s.rect(cx - 62, cy - 40, 124, 52, c1, rx=14)
        s.rect(cx - 48, cy - 62, 96, 30, shade(c2, .15), rx=10)
        s.rect(cx - 40, cy - 56, 80, 18, mix(c1, "#ffffff", .45), rx=6)
        s.circle(cx - 38, cy + 8, 8, "#ffe9a8")
        s.circle(cx + 38, cy + 8, 8, "#ffe9a8")
        s.path(f"M{cx-50} {cy+16} L{cx-90} {cy+60} M{cx+50} {cy+16} L{cx+90} {cy+60}",
               fill="none", stroke=mix(c1, "#ffe9a8", .4), stroke_width=10,
               opacity=".5", stroke_linecap="round")
        return
    if "orbit" in name or "circular" in desc:
        # --- top-down circular track
        s.sky("day")
        s.circle(480, 290, 190, shade(c2, .15))
        s.circle(480, 290, 150, mix(c1, "#ffffff", .55))
        s.circle(480, 290, 110, shade(c2, .15))
        for i in range(12):
            a = i * math.pi / 6
            x, y = 480 + math.cos(a) * 130, 290 + math.sin(a) * 130
            s.circle(x, y, 5, "#ffffff", opacity=".8")
        # car on the ring
        a = r.uniform(0, 6.28)
        x, y = 480 + math.cos(a) * 130, 290 + math.sin(a) * 130
        ang = math.degrees(a) + 90
        s.raw(f'<g transform="rotate({ang:.0f} {x:.0f} {y:.0f})">'
              f'<rect x="{x-14:.0f}" y="{y-26:.0f}" width="28" height="52" rx="9" fill="{c1}"/>'
              f'<rect x="{x-9:.0f}" y="{y-14:.0f}" width="18" height="16" rx="4" fill="{mix(c1, "#ffffff", .5)}"/>'
              f'<circle cx="{x-11:.0f}" cy="{y-20:.0f}" r="4" fill="#ffe9a8"/>'
              f'<circle cx="{x+11:.0f}" cy="{y-20:.0f}" r="4" fill="#ffe9a8"/></g>')
        # second car
        a2 = a + 2.4
        x2, y2 = 480 + math.cos(a2) * 130, 290 + math.sin(a2) * 130
        s.raw(f'<g transform="rotate({math.degrees(a2)+90:.0f} {x2:.0f} {y2:.0f})">'
              f'<rect x="{x2-13:.0f}" y="{y2-24:.0f}" width="26" height="48" rx="9" fill="{shade(c2, .2)}"/></g>')
        s.circle(480, 290, 46, mix(c1, "#ffd76a", .4))
        s.text(480, 306, "GO", 30, shade(c2, -.2))
        return
    if "canyon" in name:
        s.sky("sunset")
        # canyon walls
        s.poly([(0, 540), (0, 260), (150, 200), (220, 540)], shade(c2, -.1))
        s.poly([(960, 540), (960, 230), (820, 180), (740, 540)], shade(c2, .05))
        s.poly([(150, 200), (220, 540), (330, 540), (260, 240)], shade(c2, .2))
        s.poly([(820, 180), (740, 540), (640, 540), (700, 230)], shade(c2, -.05))
        # winding road
        s.path("M480 540 C420 430 560 380 480 300 C430 250 500 210 480 160 L520 160 "
               "C560 210 490 250 540 300 C620 380 480 430 540 540 Z",
               fill=shade(c2, -.2))
        for t in [0.15, 0.35, 0.55, 0.75, 0.92]:
            y = 540 - t * 380
            x = 510 - 30 * math.sin(t * 9)
            s.rect(x - 4, y, 8, 16, mix(c1, "#ffffff", .6), rx=3)
        # courier van
        vx, vy = 505, 430
        s.rect(vx - 52, vy - 44, 104, 52, c1, rx=10)
        s.rect(vx + 18, vy - 44, 34, 52, shade(c2, .1), rx=8)
        s.rect(vx + 24, vy - 38, 22, 20, mix(c1, "#ffffff", .5), rx=4)
        s.circle(vx - 28, vy + 12, 12, "#222222")
        s.circle(vx + 28, vy + 12, 12, "#222222")
        s.circle(vx - 28, vy + 12, 5, "#bbbbbb")
        s.circle(vx + 28, vy + 12, 5, "#bbbbbb")
        s.rect(vx - 40, vy - 30, 26, 22, mix(c1, "#ffd76a", .4), rx=3)
        return
    if "rooftop" in name:
        s.sky("dawn")
        # city skyline
        for x, w, h in [(0, 150, 190), (140, 130, 260), (260, 170, 150),
                        (420, 140, 230), (550, 160, 170), (700, 130, 250),
                        (820, 140, 180)]:
            s.rect(x, 540 - h, w, h, shade(c2, .05 if (x // 130) % 2 else -.1))
            for wy in range(540 - h + 22, 520, 44):
                for wx in range(x + 16, x + w - 16, 34):
                    s.rect(wx, wy, 14, 18, mix(c1, "#ffe9a8", .35), opacity=".85")
        # rooftop road
        s.rect(0, 380, W, 90, shade(c2, -.2))
        s.rect(0, 380, W, 8, mix(c1, "#ffffff", .3))
        for x in range(30, 960, 90):
            s.rect(x, 420, 46, 8, mix(c1, "#ffffff", .7), rx=4)
        # sportscar
        cx, cy = 480, 408
        s.path(f"M{cx-95} {cy} Q{cx-80} {cy-26} {cx-40} {cy-30} L{cx+10} {cy-52} "
               f"L{cx+52} {cy-52} Q{cx+92} {cy-48} {cx+98} {cy} Z", fill=c1)
        s.path(f"M{cx-30} {cy-30} L{cx+2} {cy-48} L{cx+44} {cy-48} L{cx+40} {cy-30} Z",
               fill=mix(c1, "#ffffff", .45))
        s.circle(cx - 52, cy + 2, 17, "#1c1c22")
        s.circle(cx + 52, cy + 2, 17, "#1c1c22")
        s.circle(cx - 52, cy + 2, 7, "#cfd6e4")
        s.circle(cx + 52, cy + 2, 7, "#cfd6e4")
        for dx in (-130, -150, 150, 170):
            s.line(cx + dx, cy - 12, cx + dx + 26, cy - 12, "#ffffff", sw=4,
                   opacity=".55", stroke_linecap="round")
        return
    if "skyway" in name or "elevated" in desc:
        s.sky("day")
        # elevated bridge with pillars
        s.rect(0, 330, W, 46, shade(c2, -.1))
        s.rect(0, 330, W, 10, mix(c1, "#ffffff", .35))
        for x in (160, 480, 800):
            s.rect(x - 16, 376, 32, 164, shade(c2, .2))
            s.rect(x - 40, 520, 80, 20, shade(c2, .1), rx=6)
        for x in range(40, 960, 100):
            s.rect(x, 348, 52, 7, mix(c1, "#ffffff", .7), rx=3)
        # road blocks
        for x, w in [(300, 44), (640, 44)]:
            s.rect(x, 296, w, 34, mix(c1, "#ffd76a", .35), rx=6)
            s.rect(x, 296, w, 10, mix(c1, "#ffffff", .4), rx=5)
        # hero car
        cx, cy = 480, 330
        s.path(f"M{cx-88} {cy} Q{cx-76} {cy-24} {cx-38} {cy-28} L{cx+8} {cy-48} "
               f"L{cx+48} {cy-48} Q{cx+86} {cy-44} {cx+92} {cy} Z", fill=c1)
        s.path(f"M{cx-28} {cy-28} L{cx} {cy-44} L{cx+40} {cy-44} L{cx+36} {cy-28} Z",
               fill=mix(c1, "#ffffff", .45))
        s.circle(cx - 48, cy + 2, 16, "#1c1c22")
        s.circle(cx + 48, cy + 2, 16, "#1c1c22")
        s.circle(cx - 48, cy + 2, 6, "#cfd6e4")
        s.circle(cx + 48, cy + 2, 6, "#cfd6e4")
        # city below
        for x, w, h in [(60, 110, 90), (250, 90, 130), (700, 120, 100), (850, 80, 140)]:
            s.rect(x, 540 - h, w, h, shade(c2, .1), opacity=".9")
        return
    # --- default: coastal / neon highway, perspective road
    coastal = "coast" in name or "coast" in desc
    s.sky("sunset" if coastal else r.choice(["day", "sunset"]))
    if coastal:
        s.rect(0, 300, 300, 240, mix(c1, "#ffffff", .3))
        s.path("M0 300 Q150 288 300 300 V540 H0Z", fill=mix(c1, "#ffffff", .45))
        s.rect(660, 300, 300, 240, shade(c2, .05))
        s.path("M660 300 Q810 288 960 300 V540 H660Z", fill=shade(c2, -.05))
    else:
        s.hills(430)
    s.path("M0 540 L340 250 L620 250 L960 540 Z", fill=shade(c2, -.15))
    s.path("M430 540 L470 250 L490 250 L530 540 Z", fill=shade(c2, .3))
    for i, y in enumerate([290, 340, 400, 470]):
        w = 8 + i * 9
        s.rect(480 - w // 2, y, w, 12 + i * 7, "#ffffff", rx=3, opacity=".9")
    # rival cars
    for x, y, sc, col in [(350, 320, .5, shade(c2, .25)), (640, 300, .42, shade(c2, .25))]:
        s.rect(x - 30 * sc, y - 24 * sc, 60 * sc, 28 * sc, col, rx=7 * sc)
        s.rect(x - 22 * sc, y - 38 * sc, 44 * sc, 18 * sc, shade(c2, .1), rx=6 * sc)
    # hero car
    cx, cy = 480, 468
    s.rect(cx - 66, cy - 42, 132, 54, c1, rx=15)
    s.rect(cx - 50, cy - 66, 100, 32, shade(c2, .12), rx=11)
    s.rect(cx - 42, cy - 60, 84, 20, mix(c1, "#ffffff", .5), rx=6)
    s.circle(cx - 40, cy + 10, 8, "#ffe9a8")
    s.circle(cx + 40, cy + 10, 8, "#ffe9a8")
    s.rect(cx - 58, cy - 30, 12, 20, mix(c1, "#ffffff", .4), rx=4)
    s.rect(cx + 46, cy - 30, 12, 20, mix(c1, "#ffffff", .4), rx=4)
    for dx in (-120, 120):
        s.line(cx + dx, cy - 16, cx + dx + 30, cy - 16, "#ffffff", sw=5,
               opacity=".55", stroke_linecap="round")


def scene_platform(s, g, r):
    name = g["name"].lower()
    c1, c2 = s.c1, s.c2
    theme = ("lantern" if "lantern" in name else "jungle" if "jungle" in name
             else "pixel" if "pixel" in name else "lava" if "lava" in name
             else "candy" if "candy" in name else "trap")
    s.sky("night" if theme in ("lantern", "lava") else "day")
    ground_y = 480
    if theme == "lava":
        s.rect(0, ground_y, W, 60, "#e8542f")
        for i in range(6):
            x = 60 + i * 160
            s.ellipse(x, ground_y + 14, 34, 10, "#ffb347", opacity=".8")
            s.ellipse(x + 60, ground_y + 34, 22, 7, "#ffd76a", opacity=".7")
        s.path("M0 480 Q200 440 420 478 T960 470 V540 H0Z", fill="#c73e1d", opacity=".7")
    elif theme == "jungle":
        s.hills(470, col=shade(c2, .2), col2=shade(c2, .05))
        for x in (90, 850):
            s.rect(x, 300, 14, 180, shade(c2, -.1))
            s.ellipse(x + 7, 280, 70, 34, mix(c1, "#ffffff", .25))
            s.ellipse(x - 40, 300, 44, 24, mix(c1, "#ffffff", .15))
            s.ellipse(x + 54, 300, 44, 24, mix(c1, "#ffffff", .15))
    elif theme == "pixel":
        s.rect(0, 0, W, H, shade(c2, -.25))
        for _ in range(40):
            s.rect(r.randint(0, 940), r.randint(0, 380), 12, 12,
                   mix(c1, "#ffffff", .3), opacity=round(r.uniform(.15, .5), 2))
        s.rect(0, ground_y, W, 60, shade(c2, .1))
    elif theme == "candy":
        s.rect(0, ground_y, W, 60, mix(c1, "#ff9db0", .3))
        for x, col in [(120, "#ff8fb5"), (830, "#ffd76a"), (700, "#9bd9ff")]:
            s.circle(x, 430, 26, col)
            s.rect(x - 26, 404, 52, 10, "#ffffff", rx=5, opacity=".7")
    else:
        s.hills(470)
    # platforms (ascending staircase, gaps)
    plats = [(90, 430, 170), (300, 350, 150), (500, 280, 160),
             (700, 350, 150), (820, 430, 110)]
    if theme == "lantern":
        for x, y, w in plats:
            s.rect(x, y, w, 18, shade(c2, .2), rx=9)
            s.line(x + w // 2, y, x + w // 2, y - 46, shade(c2, -.2), sw=3)
            s.ellipse(x + w // 2, y - 52, 20, 26, mix(c1, "#ffd76a", .5))
            s.ellipse(x + w // 2, y - 52, 10, 14, "#ffe9a8")
    elif theme == "pixel":
        for x, y, w in plats:
            s.rect(x, y, w, 20, shade(c2, .25))
            for px in range(x + 6, x + w - 10, 22):
                s.rect(px, y + 4, 12, 12, mix(c1, "#ffffff", .35))
    elif theme == "candy":
        for x, y, w in plats:
            s.rect(x, y, w, 20, mix(c1, "#ffffff", .25), rx=10)
            s.circle(x + 14, y + 10, 7, "#ffffff", opacity=".8")
            s.circle(x + w - 14, y + 10, 7, mix(c1, "#ffd76a", .5))
    else:
        for x, y, w in plats:
            s.rect(x, y, w, 18, shade(c2, .15), rx=9)
            s.rect(x, y, w, 7, mix(c1, "#ffffff", .35), rx=3)
            if theme == "jungle":
                s.ellipse(x + 12, y - 4, 18, 8, mix(c1, "#ffffff", .3))
                s.ellipse(x + w - 16, y - 4, 14, 7, mix(c1, "#ffffff", .3))
    # traps for trap-tower
    if theme == "trap":
        for x, y in [(330, 350), (540, 280)]:
            for i in range(4):
                s.poly([(x + i * 18, y), (x + i * 18 + 9, y - 22),
                        (x + i * 18 + 18, y)], shade(c2, -.3))
    # character mid-jump between platforms
    jump_x = 430 if theme != "lantern" else 580
    s.character(jump_x, 300, 1.05, c1, pose="jump",
                acc=r.choice(["hat", "antenna", "scarf", "headband", None]))
    # coins / energy along the arc
    for x, y in [(250, 300), (620, 210), (770, 300)]:
        if r.random() < .8:
            s.coin(x, y, 15)
    # goal flag on the top platform
    s.flag(700 + 130, 280)


def scene_runner(s, g, r):
    name = g["name"].lower()
    c1, c2 = s.c1, s.c2
    theme = ("cloud" if "cloud" in name else "canyon" if "canyon" in name
             else "moon" if "moon" in name else "star" if "star" in name
             else "forest" if "forest" in name else "skyrail" if "skyrail" in name
             else "dodge")
    s.sky("night" if theme in ("moon", "star") else "day")
    gy = 440
    if theme == "cloud":
        s.rect(0, gy, W, 100, mix(c1, "#ffffff", .6))
        for x in (140, 480, 820):
            s.ellipse(x, gy - 6, 150, 26, "#ffffff", opacity=".95")
            s.ellipse(x + 40, gy - 24, 90, 22, "#ffffff", opacity=".9")
        for x in (330, 660):
            s.ellipse(x, gy + 40, 90, 18, mix(c1, "#ffffff", .5), opacity=".7")
    elif theme == "canyon":
        s.poly([(0, 540), (0, 300), (220, 240), (300, 540)], shade(c2, -.05))
        s.poly([(960, 540), (960, 280), (740, 230), (660, 540)], shade(c2, .1))
        s.rect(0, gy, W, 100, shade(c2, -.15))
        s.path("M300 540 L340 440 L620 440 L660 540 Z", fill=shade(c2, -.25))
    elif theme == "moon":
        s.rect(0, gy, W, 100, shade(c2, -.1))
        for x, y, rr in [(150, 480, 26), (420, 500, 18), (700, 478, 30), (880, 505, 16)]:
            s.ellipse(x, y, rr, rr * .45, shade(c2, -.3))
        s.circle(760, 110, 44, mix(c1, "#ffffff", .6))
        s.circle(745, 100, 9, mix(c1, "#ffffff", .35))
        s.circle(775, 122, 6, mix(c1, "#ffffff", .35))
    elif theme == "forest":
        s.hills(gy)
        for x, h in [(70, 190), (200, 230), (880, 200), (760, 160)]:
            s.rect(x, gy - h, 18, h, shade(c2, -.25))
            s.poly([(x - 46, gy - h + 40), (x + 9, gy - h - 70), (x + 64, gy - h + 40)],
                   mix(c1, "#ffffff", .2))
            s.poly([(x - 40, gy - h + 90), (x + 9, gy - h - 10), (x + 58, gy - h + 90)],
                   mix(c1, "#ffffff", .12))
    elif theme == "skyrail":
        s.rect(0, gy, W, 100, shade(c2, -.3))
        for x in (200, 480, 760):
            s.rect(x - 10, gy + 10, 20, 90, shade(c2, .1))
        s.rect(0, gy - 14, W, 12, mix(c1, "#ffffff", .4))
        for x in range(20, 960, 90):
            s.rect(x, gy - 34, 8, 22, shade(c2, .2))
            s.rect(x, gy - 34, 54, 6, shade(c2, .2))
    else:
        s.rect(0, gy, W, 100, shade(c2, .05))
        s.rect(0, gy, W, 8, mix(c1, "#ffffff", .4))
        for x in range(30, 960, 110):
            s.rect(x, gy + 46, 56, 9, mix(c1, "#ffffff", .55), rx=4)
    # obstacles
    if theme == "dodge":
        for x, h in [(560, 52), (760, 70)]:
            s.rect(x, gy - h, 26, h, mix(c1, "#ffd76a", .3), rx=6)
            s.rect(x, gy - h, 26, 12, "#ffffff", rx=6, opacity=".6")
        s.poly([(660, gy), (660, gy - 60), (700, gy - 30)], shade(c2, .2))
    elif theme == "canyon":
        s.rect(430, gy - 60, 120, 60, shade(c2, -.25))
        s.path("M430 440 L550 440 L550 500 L430 500 Z", fill=shade(c2, -.35))
    elif theme == "star":
        for x, y in [(600, 330), (760, 300)]:
            s.gem(x, y, 20, "star", mix(c1, "#ffd76a", .4))
    # collectibles arc
    for i, (x, y) in enumerate([(300, 330), (360, 290), (420, 270), (480, 270)]):
        if theme == "star":
            s.gem(x, y, 14, "star", mix(c1, "#ffd76a", .45))
        elif theme == "moon":
            s.circle(x, y, 12, mix(c1, "#ffffff", .5))
            s.circle(x - 4, y - 4, 4, "#ffffff", opacity=".7")
        else:
            s.coin(x, y, 14)
    # running character
    s.character(210, gy, 1.15, c1, pose="run",
                acc=r.choice(["headband", "scarf", "antenna", None]))
    # speed lines
    for i in range(3):
        y = 300 + i * 40
        s.line(60, y, 130 + i * 20, y, "#ffffff", sw=4, opacity=".45",
               stroke_linecap="round")


def scene_blocks(s, g, r):
    name = g["name"].lower()
    c1, c2 = s.c1, s.c2
    s.sky("flat")
    hexb = "hex" in name or "hexa" in name
    # board
    bx, by, cell = 250, 70, 52
    cols, rows = (7, 6) if hexb else (8, 7)
    s.rect(bx - 16, by - 16, cols * cell + 32, rows * cell + 32,
           shade(c2, -.05), rx=18)
    s.rect(bx - 16, by - 16, cols * cell + 32, rows * cell + 32, "none",
           stroke=mix(c1, "#ffffff", .4), stroke_width=3, opacity=".6")
    shapes = ["square", "diamond", "circle", "triangle", "star", "hex"]
    palette = [c1, mix(c1, "#ffffff", .35), mix(c1, "#ffd76a", .3),
               mix(c2, "#ffffff", .35), shade(c1, -.15)]
    # filled cells: a few complete rows + scattered
    full_rows = r.sample(range(rows), 2)
    for row in range(rows):
        for col in range(cols):
            x, y = bx + col * cell, by + row * cell
            if row in full_rows or r.random() < .28:
                if hexb:
                    s.gem(x + cell / 2, y + cell / 2, cell * .36, "hex",
                          palette[(row + col) % len(palette)])
                else:
                    s.rect(x + 4, y + 4, cell - 8, cell - 8,
                           palette[(row * 3 + col) % len(palette)], rx=8)
                    s.rect(x + 10, y + 10, cell - 20, 10, "#ffffff", rx=5,
                           opacity=".35")
            else:
                s.rect(x + 4, y + 4, cell - 8, cell - 8, shade(c2, .15), rx=8,
                       opacity=".55")
    # floating piece tray (right side)
    tx = 760
    s.rect(tx - 30, 150, 150, 220, shade(c2, .1), rx=16, opacity=".9")
    piece = [[(0, 0), (1, 0), (0, 1), (1, 1)],
             [(0, 0), (1, 0), (2, 0), (1, 1)],
             [(0, 0), (0, 1), (0, 2), (1, 2)],
             [(0, 0), (1, 0), (2, 0)]][r.randrange(4)]
    for dx, dy in piece:
        s.rect(tx + dx * 34, 190 + dy * 34, 30, 30, c1, rx=7)
        s.rect(tx + dx * 34 + 4, 194 + dy * 34, 22, 8, "#ffffff", rx=4, opacity=".4")
    piece2 = [[(0, 0), (1, 0)], [(0, 0), (0, 1), (1, 1)]][r.randrange(2)]
    for dx, dy in piece2:
        s.rect(tx + dx * 34, 300 + dy * 34, 30, 30,
               mix(c1, "#ffd76a", .3), rx=7)
    # left side: small stack of pieces
    s.rect(90, 380, 90, 30, mix(c1, "#ffffff", .3), rx=7)
    s.rect(110, 350, 60, 30, c1, rx=7)
    s.rect(120, 320, 40, 30, mix(c2, "#ffffff", .35), rx=7)


def scene_bubble(s, g, r):
    c1, c2 = s.c1, s.c2
    s.sky(r.choice(["day", "dawn"]))
    # bubble cluster (hex packing)
    palette = [c1, mix(c1, "#ffffff", .4), mix(c1, "#ffd76a", .35),
               mix(c2, "#ffffff", .45), shade(c1, -.1)]
    rows = [8, 7, 8, 7, 6]
    y0 = 60
    for ri, n in enumerate(rows):
        y = y0 + ri * 46
        x0 = 480 - (n - 1) * 30 + (23 if ri % 2 else 0)
        for ci in range(n):
            x = x0 + ci * 60
            if r.random() < .12:
                continue
            col = palette[(ri * 2 + ci) % len(palette)]
            s.circle(x, y, 26, col)
            s.circle(x - 8, y - 9, 8, "#ffffff", opacity=".65")
            s.circle(x, y, 26, "none", stroke=shade(col, -.25),
                     stroke_width=2, opacity=".4")
    # matched cluster glow
    mx, my = 480, 60 + 2 * 46
    s.circle(mx, my, 34, "none", stroke="#ffffff", stroke_width=4, opacity=".8")
    s.circle(mx - 60, my, 34, "none", stroke="#ffffff", stroke_width=4, opacity=".8")
    s.circle(mx + 60, my, 34, "none", stroke="#ffffff", stroke_width=4, opacity=".8")
    # cannon at bottom
    s.rect(430, 470, 100, 40, shade(c2, .1), rx=14)
    s.circle(480, 452, 34, c1)
    s.circle(472, 444, 10, "#ffffff", opacity=".7")
    s.circle(480, 452, 34, "none", stroke=shade(c1, -.25), stroke_width=3)
    # aim line
    s.line(480, 420, 480, 330, "#ffffff", sw=4, opacity=".6",
           stroke_dasharray="10 12", stroke_linecap="round")
    s.circle(480, 318, 16, mix(c1, "#ffd76a", .3))
    # side bubbles
    s.circle(120, 420, 30, mix(c2, "#ffffff", .4))
    s.circle(840, 400, 24, c1)
    s.circle(860, 460, 16, mix(c1, "#ffffff", .4))


def scene_merge(s, g, r):
    c1, c2 = s.c1, s.c2
    s.sky("flat")
    # 4x4 tile board
    bx, by, cell = 300, 80, 92
    s.rect(bx - 18, by - 18, 4 * cell + 36, 4 * cell + 36, shade(c2, -.05), rx=20)
    # pip counts standing in for tile values
    vals = [[0, 1, 0, 2], [3, 0, 1, 0], [0, 2, 4, 1], [1, 0, 0, 3]]
    r.shuffle(vals)
    for row in range(4):
        for col in range(4):
            v = vals[row][col]
            x, y = bx + col * cell, by + row * cell
            if v == 0:
                s.rect(x + 5, y + 5, cell - 10, cell - 10, shade(c2, .18), rx=12)
                continue
            colr = [mix(c1, "#ffffff", .55), c1, mix(c1, "#ffd76a", .35),
                    mix(c2, "#ffffff", .4), shade(c1, -.15)][v - 1]
            hot = (row == 2 and col == 2)
            s.rect(x + 5, y + 5, cell - 10, cell - 10, colr, rx=12)
            if hot:
                s.rect(x + 5, y + 5, cell - 10, cell - 10, "none",
                       stroke="#ffffff", stroke_width=4, rx=12)
            # pips
            pts = {1: [(0, 0)], 2: [(-18, -18), (18, 18)],
                   3: [(-20, -20), (0, 0), (20, 20)],
                   4: [(-18, -18), (18, -18), (-18, 18), (18, 18)]}[v]
            for dx, dy in pts:
                s.circle(x + cell / 2 + dx, y + cell / 2 + dy, 9, "#ffffff",
                         opacity=".9")
    # merge arrow + incoming tile
    s.path("M210 250 L262 250 M262 250 L246 236 M262 250 L246 264",
           fill="none", stroke="#ffffff", stroke_width=6, stroke_linecap="round")
    s.rect(120, 206, 88, 88, mix(c1, "#ffd76a", .35), rx=14)
    s.circle(164, 250, 10, "#ffffff")
    s.circle(120, 420, 26, c1, opacity=".6")
    s.circle(850, 120, 20, mix(c1, "#ffffff", .4))
    s.circle(860, 430, 30, mix(c2, "#ffffff", .4))


def scene_breaker(s, g, r):
    c1, c2 = s.c1, s.c2
    s.sky("night" if r.random() < .5 else "day")
    # brick wall
    palette = [c1, mix(c1, "#ffffff", .35), mix(c1, "#ffd76a", .3),
               mix(c2, "#ffffff", .4)]
    rows = r.randint(4, 5)
    bw, bh = 108, 34
    x0 = 480 - (7 * bw + 6 * 8) / 2
    for row in range(rows):
        for col in range(7):
            x = x0 + col * (bw + 8)
            y = 60 + row * (bh + 8)
            if r.random() < .14:
                continue  # cleared brick gap
            colr = palette[(row + col) % len(palette)]
            s.rect(x, y, bw, bh, colr, rx=8)
            s.rect(x + 6, y + 5, bw - 12, 9, "#ffffff", rx=4, opacity=".35")
    # ball with trail
    bx, by = 480 + r.randint(-120, 120), 330
    for i in range(4):
        s.circle(bx - i * 16, by + i * 14, 13 - i * 2, c1,
                 opacity=round(.85 - i * .2, 2))
    s.circle(bx, by, 13, "#ffffff")
    s.circle(bx - 4, by - 4, 4, c1)
    # paddle
    px = 480
    s.rect(px - 90, 470, 180, 22, mix(c1, "#ffffff", .25), rx=11)
    s.rect(px - 90, 470, 180, 8, "#ffffff", rx=4, opacity=".5")
    # side sparks
    for x, y in [(140, 380), (820, 360)]:
        s.gem(x, y, 16, "star", mix(c1, "#ffd76a", .4))


def _gen_maze(r, cols, rows):
    """DFS maze: returns set of wall segments ((x,y),(x2,y2)) on grid."""
    visited = [[False] * cols for _ in range(rows)]
    walls = set()
    for y in range(rows):
        for x in range(cols):
            walls.add(((x, y), (x + 1, y)))
            walls.add(((x, y), (x, y + 1)))
    stack = [(0, 0)]
    visited[0][0] = True
    while stack:
        x, y = stack[-1]
        nb = []
        for dx, dy, w in [(1, 0, ((x + 1, y), (x + 1, y + 1))),
                          (-1, 0, ((x, y), (x, y + 1))),
                          (0, 1, ((x, y + 1), (x + 1, y + 1))),
                          (0, -1, ((x, y), (x + 1, y)))]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < cols and 0 <= ny < rows and not visited[ny][nx]:
                nb.append((nx, ny, w))
        if not nb:
            stack.pop()
            continue
        nx, ny, w = r.choice(nb)
        walls.discard(w)
        visited[ny][nx] = True
        stack.append((nx, ny))
    return walls


def scene_maze(s, g, r):
    c1, c2 = s.c1, s.c2
    s.sky("flat")
    cols, rows = 10, 6
    cell = 62
    ox, oy = (W - cols * cell) // 2, 90
    s.rect(ox - 14, oy - 14, cols * cell + 28, rows * cell + 28,
           shade(c2, -.05), rx=18)
    walls = _gen_maze(r, cols, rows)
    # dotted solution path: walk from start to goal through open cells
    # (re-run DFS pathfinding on the wall set)
    def open_(x, y, nx, ny):
        if nx < 0 or ny < 0 or nx >= cols or ny >= rows:
            return False
        if nx == x + 1:
            return ((x + 1, y), (x + 1, y + 1)) not in walls
        if nx == x - 1:
            return ((x, y), (x, y + 1)) not in walls
        if ny == y + 1:
            return ((x, y + 1), (x + 1, y + 1)) not in walls
        return ((x, y), (x + 1, y)) not in walls
    from collections import deque
    prev = {(0, 0): None}
    dq = deque([(0, 0)])
    while dq:
        x, y = dq.popleft()
        if (x, y) == (cols - 1, rows - 1):
            break
        for nx, ny in [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]:
            if (nx, ny) not in prev and open_(x, y, nx, ny):
                prev[(nx, ny)] = (x, y)
                dq.append((nx, ny))
    path = []
    cur = (cols - 1, rows - 1)
    while cur is not None:
        path.append(cur)
        cur = prev.get(cur)
    path.reverse()
    for (x, y) in path:
        s.circle(ox + x * cell + cell / 2, oy + y * cell + cell / 2, 6,
                 mix(c1, "#ffffff", .5), opacity=".85")
    # walls
    for (x1, y1), (x2, y2) in walls:
        s.line(ox + x1 * cell, oy + y1 * cell, ox + x2 * cell, oy + y2 * cell,
               mix(c1, "#ffffff", .55), sw=6, stroke_linecap="round")
    # player marble at start, flag at goal
    s.circle(ox + cell / 2, oy + cell / 2, 16, c1)
    s.circle(ox + cell / 2 - 5, oy + cell / 2 - 5, 5, "#ffffff", opacity=".7")
    s.flag(ox + (cols - 1) * cell + cell / 2 + 8, oy + (rows - 1) * cell + cell / 2 + 10, h=44)
    # decoy dots
    for _ in range(3):
        s.circle(ox + r.randrange(cols) * cell + cell / 2,
                 oy + r.randrange(rows) * cell + cell / 2, 5,
                 mix(c2, "#ffffff", .4), opacity=".7")


def scene_stack(s, g, r):
    c1, c2 = s.c1, s.c2
    s.sky(r.choice(["day", "sunset", "dawn"]))
    s.hills(500)
    # tower of offset blocks
    bw, bh = 220, 34
    x = 480 - bw // 2
    y = 500
    palette = [c1, mix(c1, "#ffffff", .35), mix(c1, "#ffd76a", .3),
               mix(c2, "#ffffff", .4), shade(c1, -.12)]
    n = r.randint(7, 9)
    for i in range(n):
        off = r.randint(-34, 34)
        colr = palette[i % len(palette)]
        s.rect(x + off, y - bh, bw, bh, colr, rx=7)
        s.rect(x + off + 8, y - bh + 5, bw - 16, 7, "#ffffff", rx=3, opacity=".3")
        y -= bh + 2
    top_y = y
    # swinging block above (crane line)
    swing = r.randint(-90, 90)
    s.line(480 + swing, top_y - 90, 480 + swing, top_y - 34, shade(c2, -.2),
           sw=4, stroke_dasharray="6 6")
    s.rect(480 + swing - bw // 2, top_y - 34, bw, bh,
           mix(c1, "#ffffff", .15), rx=7, opacity=".95")
    s.rect(480 + swing - bw // 2 + 8, top_y - 29, bw - 16, 7, "#ffffff", rx=3,
           opacity=".4")
    # target marker + character watching
    s.path(f"M{480-14} {top_y-70} L{480} {top_y-56} L{480+14} {top_y-70}",
           fill=mix(c1, "#ffd76a", .4))
    s.character(760, 500, 0.9, c1, pose="stand", acc=r.choice(["hat", None]))
    s.circle(150, 420, 18, mix(c1, "#ffd76a", .4))
    s.circle(120, 350, 12, "#ffffff", opacity=".7")


def scene_match(s, g, r):
    c1, c2 = s.c1, s.c2
    s.sky("flat")
    cols, rows, cell = 7, 6, 66
    bx, by = (W - cols * cell) // 2, 60
    s.rect(bx - 16, by - 16, cols * cell + 32, rows * cell + 32,
           shade(c2, -.05), rx=18)
    kinds = ["circle", "diamond", "square", "triangle", "star", "hex"]
    palette = [c1, mix(c1, "#ffffff", .4), mix(c1, "#ffd76a", .35),
               mix(c2, "#ffffff", .45), shade(c1, -.12)]
    # a matched row of three in the middle
    match_row, match_col = r.randint(1, 4), r.randint(0, 3)
    mk, mp = r.choice(kinds), r.choice(palette)
    for row in range(rows):
        for col in range(cols):
            cx = bx + col * cell + cell / 2
            cy = by + row * cell + cell / 2
            if row == match_row and match_col <= col < match_col + 3:
                s.gem(cx, cy, 24, mk, mp)
                s.circle(cx, cy, 30, "none", stroke="#ffffff", stroke_width=3,
                         opacity=".85")
            else:
                s.gem(cx, cy, 22, r.choice(kinds), r.choice(palette))
    # swap arrow on the matched row
    y = by + match_row * cell + cell / 2
    s.path(f"M{bx-70} {y} L{bx-34} {y} M{bx-34} {y} L{bx-48} {y-12} M{bx-34} {y} L{bx-48} {y+12}",
           fill="none", stroke="#ffffff", stroke_width=5, stroke_linecap="round")
    # sparkles
    for x, y in [(120, 130), (850, 450)]:
        s.gem(x, y, 18, "star", mix(c1, "#ffd76a", .4))


def scene_memory(s, g, r):
    name = g["name"].lower()
    c1, c2 = s.c1, s.c2
    s.sky("flat")
    cols, rows, cell = 5, 3, 120
    bx, by = (W - cols * cell) // 2, 110
    # two face-up cards reveal a matching pair
    up = r.sample([(col, row) for row in range(rows) for col in range(cols)], 2)
    sym = r.choice(["star", "heart", "moon", "sun", "flower", "gem"])
    for row in range(rows):
        for col in range(cols):
            x, y = bx + col * cell, by + row * cell
            if (col, row) in up:
                s.rect(x + 8, y + 8, cell - 16, cell - 16, "#ffffff", rx=14)
                s.rect(x + 8, y + 8, cell - 16, cell - 16, "none",
                       stroke=c1, stroke_width=4, rx=14)
                cx, cy = x + cell / 2, y + cell / 2
                if sym == "star":
                    s.gem(cx, cy, 30, "star", mix(c1, "#ffd76a", .35))
                elif sym == "heart":
                    s.path(f"M{cx} {cy+22} C{cx-34} {cy-2} {cx-26} {cy-26} {cx-8} {cy-22} "
                           f"C{cx-2} {cy-20} {cx} {cy-14} {cx} {cy-12} "
                           f"C{cx} {cy-14} {cx+2} {cy-20} {cx+8} {cy-22} "
                           f"C{cx+26} {cy-26} {cx+34} {cy-2} {cx} {cy+22} Z",
                           fill=mix(c1, "#ff8fb5", .3))
                elif sym == "moon":
                    s.circle(cx, cy, 26, mix(c1, "#ffd76a", .35))
                    s.circle(cx + 12, cy - 8, 22, "#ffffff")
                elif sym == "sun":
                    s.circle(cx, cy, 22, mix(c1, "#ffd76a", .4))
                    for i in range(8):
                        a = i * math.pi / 4
                        s.line(cx + math.cos(a) * 28, cy + math.sin(a) * 28,
                               cx + math.cos(a) * 38, cy + math.sin(a) * 38,
                               mix(c1, "#ffd76a", .4), sw=4, stroke_linecap="round")
                elif sym == "flower":
                    for i in range(6):
                        a = i * math.pi / 3
                        s.ellipse(cx + math.cos(a) * 16, cy + math.sin(a) * 16,
                                  12, 12, c1)
                    s.circle(cx, cy, 10, mix(c1, "#ffd76a", .4))
                else:
                    s.gem(cx, cy, 28, "diamond", c1)
            else:
                s.rect(x + 8, y + 8, cell - 16, cell - 16, shade(c2, .1), rx=14)
                s.rect(x + 8, y + 8, cell - 16, cell - 16, "none",
                       stroke=mix(c1, "#ffffff", .4), stroke_width=3, rx=14)
                cx, cy = x + cell / 2, y + cell / 2
                s.circle(cx, cy, 16, "none", stroke=mix(c1, "#ffffff", .5),
                         stroke_width=3)
                s.circle(cx, cy, 6, mix(c1, "#ffffff", .5))
    # garden / museum / cosmos dressing
    if "garden" in name:
        for x in (60, 900):
            s.ellipse(x, 470, 40, 60, mix(c1, "#ffffff", .25))
            s.circle(x, 420, 18, c1)
    elif "cosmos" in name:
        s.stars(10)
    elif "museum" in name:
        s.rect(60, 430, 840, 10, shade(c2, .2))
        s.rect(120, 380, 60, 50, mix(c1, "#ffffff", .3), rx=6)
        s.rect(780, 380, 60, 50, mix(c2, "#ffffff", .35), rx=6)


def scene_sudoku(s, g, r):
    c1, c2 = s.c1, s.c2
    s.sky("flat")
    cell = 96
    bx, by = (W - 4 * cell) // 2, 64
    s.rect(bx - 14, by - 14, 4 * cell + 28, 4 * cell + 28, shade(c2, -.05), rx=18)
    grid = [[1, 0, 3, 0], [0, 4, 0, 2], [2, 0, 4, 0], [0, 3, 0, 1]]
    if r.random() < .5:
        grid = [[0, 2, 0, 4], [4, 0, 1, 0], [0, 1, 0, 3], [3, 0, 2, 0]]
    hot = (r.randrange(4), r.randrange(4))
    for row in range(4):
        for col in range(4):
            x, y = bx + col * cell, by + row * cell
            fill = "#ffffff" if (row, col) == hot else shade(c2, .18)
            s.rect(x + 4, y + 4, cell - 8, cell - 8, fill, rx=10)
            if grid[row][col]:
                s.text(x + cell / 2, y + cell / 2 + 16, str(grid[row][col]), 40,
                       c1 if (row, col) != hot else shade(c2, -.1))
            if (row, col) == hot:
                s.rect(x + 4, y + 4, cell - 8, cell - 8, "none", stroke=c1,
                       stroke_width=4, rx=10)
    # thick 2x2 separators
    for i in (1, 2, 3):
        s.line(bx + i * cell, by + 6, bx + i * cell, by + 4 * cell - 6,
               mix(c1, "#ffffff", .4), sw=2 if i != 2 else 5, opacity=".7")
        s.line(bx + 6, by + i * cell, bx + 4 * cell - 6, by + i * cell,
               mix(c1, "#ffffff", .4), sw=2 if i != 2 else 5, opacity=".7")
    # number picker row
    for i, n in enumerate([1, 2, 3, 4]):
        x = 330 + i * 100
        s.circle(x, 490, 32, mix(c1, "#ffffff", .3) if i != 1 else c1)
        s.text(x, 502, str(n), 30, "#ffffff" if i == 1 else shade(c2, -.1))


def scene_word(s, g, r):
    name = g["name"].lower()
    c1, c2 = s.c1, s.c2
    s.sky(r.choice(["day", "dawn", "flat"]))
    letters = [ch for ch in g["name"].replace(" ", "") if ch.isalpha()]
    r.shuffle(letters)
    # a row of tiles forming the first word
    word = g["name"].split()[0].upper()
    tw = len(word) * 84
    x0 = (W - tw) // 2
    y = 180
    for i, ch in enumerate(word):
        x = x0 + i * 84
        s.rect(x, y, 72, 72, c1 if i % 2 == 0 else mix(c1, "#ffffff", .3), rx=12)
        s.rect(x, y, 72, 72, "none", stroke=shade(c2, -.15), stroke_width=3,
               rx=12, opacity=".4")
        s.text(x + 36, y + 50, ch, 40, "#ffffff")
    # scattered tiles
    for i in range(7):
        x = r.randint(60, 860)
        yy = r.choice([330, 340, 420, 430, 440])
        ch = letters[i % len(letters)].upper()
        s.raw(f'<g transform="rotate({r.randint(-14, 14)} {x} {yy})">'
              f'<rect x="{x-30}" y="{yy-30}" width="60" height="60" rx="10" '
              f'fill="{mix(c2, "#ffffff", .3 if i % 2 else .45)}"/>'
              f'<text x="{x}" y="{yy+13}" font-family="Arial, Helvetica, sans-serif" '
              f'font-size="32" font-weight="bold" fill="#ffffff" '
              f'text-anchor="middle">{ch}</text></g>')
    # pencil + hint bubble
    s.raw(f'<g transform="rotate(-24 780 420)">'
          f'<rect x="740" y="400" width="120" height="22" rx="6" fill="{mix(c1, "#ffd76a", .4)}"/>'
          f'<polygon points="860,400 890,411 860,422" fill="{shade(c2, .2)}"/>'
          f'<rect x="724" y="400" width="18" height="22" rx="4" fill="#ff8fb5"/></g>')
    if "riddle" in name or "daily" in name:
        s.circle(150, 130, 52, mix(c1, "#ffd76a", .4))
        s.text(150, 148, "?", 52, "#ffffff")


def scene_sokoban(s, g, r):
    name = g["name"].lower()
    c1, c2 = s.c1, s.c2
    s.sky("flat")
    cell = 74
    cols, rows = 8, 5
    bx, by = (W - cols * cell) // 2, 100
    s.rect(bx - 12, by - 12, cols * cell + 24, rows * cell + 24,
           shade(c2, -.05), rx=16)
    # floor tiles
    for row in range(rows):
        for col in range(cols):
            x, y = bx + col * cell, by + row * cell
            s.rect(x + 3, y + 3, cell - 6, cell - 6,
                   shade(c2, .12) if (row + col) % 2 else shade(c2, .22), rx=8)
    # target marks
    targets = [(6, 1), (6, 3), (5, 2)] if "light" in name else [(6, 1), (6, 3)]
    for tx, ty in targets:
        x, y = bx + tx * cell + cell / 2, by + ty * cell + cell / 2
        s.circle(x, y, 20, "none", stroke=mix(c1, "#ffd76a", .4), stroke_width=5)
        s.circle(x, y, 6, mix(c1, "#ffd76a", .4))
    # crates
    crates = [(4, 1), (4, 3)] if "light" in name else [(4, 1), (5, 3), (3, 2)]
    for cx, cy in crates:
        x, y = bx + cx * cell, by + cy * cell
        on_target = (cx, cy) in targets
        colr = mix(c1, "#ffd76a", .35) if on_target else mix(c1, "#ffffff", .25)
        s.rect(x + 8, y + 8, cell - 16, cell - 16, colr, rx=10)
        s.rect(x + 8, y + 8, cell - 16, cell - 16, "none",
               stroke=shade(c2, -.2), stroke_width=3, rx=10)
        s.line(x + 8, y + 8, x + cell - 8, y + cell - 8, shade(c2, -.15), sw=3)
        s.line(x + cell - 8, y + 8, x + 8, y + cell - 8, shade(c2, -.15), sw=3)
    # glowing path pieces for light-path
    if "light" in name:
        s.line(bx + 1 * cell + 37, by + 2 * cell + 37, bx + 4 * cell + 37,
               by + 2 * cell + 37, mix(c1, "#ffd76a", .5), sw=8,
               stroke_linecap="round", stroke_dasharray="14 10")
        s.circle(bx + 1 * cell + 37, by + 2 * cell + 37, 14, "#ffffff")
        s.circle(bx + 6 * cell + 37, by + 2 * cell + 37, 14, "#ffffff")
    # player pushing a crate
    px = bx + 3 * cell + cell / 2
    py = by + 1 * cell + cell
    s.character(px, py, 0.95, c1, pose="push", acc="hat", flip=False)
    # wall blocks top-left
    s.rect(bx + 3, by + 3, cell - 6, cell - 6, shade(c2, -.3), rx=8)
    s.rect(bx + cell + 3, by + 3, cell - 6, cell - 6, shade(c2, -.3), rx=8)


def scene_pattern(s, g, r):
    name = g["name"].lower()
    c1, c2 = s.c1, s.c2
    s.sky("flat")
    shapes = ["circle", "diamond", "square", "triangle", "star", "hex"]
    palette = [c1, mix(c1, "#ffffff", .4), mix(c1, "#ffd76a", .35),
               mix(c2, "#ffffff", .45)]
    # top row: the pattern to study (repeating A B A B)
    y = 150
    seq = [r.choice(shapes) for _ in range(2)] + [r.choice(palette) for _ in range(2)]
    a_kind, b_kind = r.sample(shapes, 2)
    a_col, b_col = r.sample(palette, 2)
    for i in range(5):
        x = 180 + i * 130
        kind = a_kind if i % 2 == 0 else b_kind
        colr = a_col if i % 2 == 0 else b_col
        s.rect(x - 52, y - 52, 104, 104, shade(c2, .1), rx=16)
        s.gem(x, y, 30, kind, colr)
    # next tile: dotted outline (the question)
    x = 180 + 5 * 130
    s.rect(x - 52, y - 52, 104, 104, "none", stroke="#ffffff", stroke_width=4,
           stroke_dasharray="12 10", rx=16)
    s.text(x, y + 18, "?", 52, "#ffffff")
    # bottom row: answer choices
    y2 = 360
    choices = [(a_kind, a_col), (b_kind, b_col),
               (r.choice(shapes), r.choice(palette))]
    r.shuffle(choices)
    for i, (kind, colr) in enumerate(choices):
        x = 250 + i * 230
        s.rect(x - 62, y2 - 62, 124, 124,
               c1 if i == 0 else shade(c2, .15), rx=18)
        s.rect(x - 62, y2 - 62, 124, 124, "none",
               stroke="#ffffff" if i == 0 else "none", stroke_width=4, rx=18,
               opacity=".9" if i == 0 else "0")
        s.gem(x, y2, 34, kind, colr)
    if "odd" in name:
        # one tile breaks the pattern: highlight it
        s.circle(180 + 2 * 130, 150, 62, "none", stroke=mix(c1, "#ffd76a", .4),
                 stroke_width=5, stroke_dasharray="8 8")


def scene_reaction(s, g, r):
    name, desc = g["name"].lower(), g["desc"].lower()
    c1, c2 = s.c1, s.c2
    if "table tennis" in name or "table-tennis" in g["id"]:
        s.sky("day")
        # table
        s.poly([(120, 300), (840, 300), (900, 470), (60, 470)], mix(c1, "#ffffff", .2))
        s.poly([(120, 300), (840, 300), (900, 470), (60, 470)], "none",
               stroke="#ffffff", stroke_width=4)
        s.line(480, 300, 480, 470, "#ffffff", sw=4)
        s.line(120, 300, 900, 470, "#ffffff", sw=3, opacity=".5")
        s.line(840, 300, 60, 470, "#ffffff", sw=3, opacity=".5")
        # net
        s.rect(430, 330, 100, 26, "none", stroke="#ffffff", stroke_width=3)
        for x in range(436, 530, 12):
            s.line(x, 330, x, 356, "#ffffff", sw=1.5, opacity=".7")
        # paddles + ball
        s.circle(300, 250, 34, mix(c1, "#ff8fb5", .2))
        s.rect(300 - 8, 276, 16, 44, shade(c2, .1), rx=8)
        s.circle(660, 420, 34, c1)
        s.rect(660 - 8, 446, 16, 44, shade(c2, .1), rx=8)
        s.circle(560, 300, 14, "#ffffff")
        s.circle(556, 296, 4, c1)
        return
    if "soccer" in name:
        s.sky("day")
        s.rect(0, 380, W, 160, mix(c1, "#ffffff", .25))
        s.rect(0, 380, W, 8, "#ffffff", opacity=".6")
        # goal
        s.rect(300, 150, 360, 230, "none", stroke="#ffffff", stroke_width=8)
        for x in range(312, 660, 36):
            s.line(x, 158, x, 372, "#ffffff", sw=2, opacity=".5")
        for y in range(166, 380, 36):
            s.line(308, y, 652, y, "#ffffff", sw=2, opacity=".5")
        # keeper
        s.character(480, 380, 1.0, shade(c2, .2), pose="stand", acc="hat")
        # ball + boot
        s.circle(480, 470, 30, "#ffffff")
        s.poly([(480, 440), (500, 458), (480, 476), (460, 458)], shade(c2, -.2))
        s.poly([(480, 440), (494, 446), (480, 452), (466, 446)], c1)
        return
    if "comet" in name:
        s.sky("night")
        for _ in range(3):
            x, y = r.randint(150, 800), r.randint(120, 320)
            a = r.uniform(-.5, .2)
            s.line(x, y, x - 130, y - 130 * math.tan(a) if False else y + 40,
                   mix(c1, "#ffffff", .6), sw=5, opacity=".8", stroke_linecap="round")
            s.circle(x, y, 14, "#ffffff")
            s.circle(x, y, 22, mix(c1, "#ffffff", .5), opacity=".6")
        s.circle(480, 430, 40, mix(c1, "#ffd76a", .4))
        s.circle(480, 430, 40, "none", stroke="#ffffff", stroke_width=4)
        return
    if "tempo" in name or "metronome" in desc:
        s.sky("flat")
        # metronome
        s.poly([(410, 470), (550, 470), (505, 160), (455, 160)], shade(c2, .15))
        s.poly([(410, 470), (550, 470), (505, 160), (455, 160)], "none",
               stroke=mix(c1, "#ffffff", .4), stroke_width=3)
        s.line(480, 440, 560, 200, c1, sw=10, stroke_linecap="round")
        s.circle(560, 200, 14, mix(c1, "#ffd76a", .4))
        # beat dots
        for i, x in enumerate([200, 320, 640, 760]):
            s.circle(x, 420, 26 if i == 1 else 20,
                     c1 if i == 1 else mix(c2, "#ffffff", .35))
            if i == 1:
                s.circle(x, 420, 36, "none", stroke="#ffffff", stroke_width=4)
        return
    # --- generic: glowing targets
    s.sky("night" if r.random() < .5 else "flat")
    targets = [(480, 250, 74), (220, 400, 48), (740, 380, 54), (760, 140, 40),
               (200, 150, 42)]
    r.shuffle(targets)
    for i, (x, y, rr) in enumerate(targets):
        hot = i == 0
        colr = mix(c1, "#ffd76a", .4) if hot else mix(c2, "#ffffff", .3)
        s.circle(x, y, rr, colr, opacity=".9" if hot else ".75")
        s.circle(x, y, rr * .62, "none", stroke="#ffffff", stroke_width=4,
                 opacity=".9" if hot else ".5")
        s.circle(x, y, rr * .3, "#ffffff" if hot else mix(c1, "#ffffff", .5))
        if hot:
            s.circle(x, y, rr + 14, "none", stroke="#ffffff", stroke_width=3,
                     opacity=".7", stroke_dasharray="8 10")
    # lightning bolt accent
    s.poly([(120, 470), (160, 470), (140, 510), (180, 510), (130, 540), (150, 505),
            (115, 505)], mix(c1, "#ffd76a", .4))
    if "switch" in name:
        for i, colr in enumerate([c1, mix(c1, "#ff8fb5", .3),
                                  mix(c1, "#ffd76a", .35), mix(c2, "#ffffff", .4)]):
            s.rect(300 + i * 95, 470, 80, 40, colr, rx=10)


def scene_hoops(s, g, r):
    name = g["name"].lower()
    c1, c2 = s.c1, s.c2
    if "penalty" in name or "free-kick" in name or "free kick" in name:
        # football goal
        s.sky("day")
        s.rect(0, 400, W, 140, mix(c1, "#ffffff", .3))
        s.rect(0, 400, W, 6, "#ffffff", opacity=".6")
        s.rect(260, 130, 440, 270, "none", stroke="#ffffff", stroke_width=9)
        for x in range(272, 700, 34):
            s.line(x, 139, x, 391, "#ffffff", sw=2, opacity=".45")
        for y in range(146, 400, 34):
            s.line(269, y, 691, y, "#ffffff", sw=2, opacity=".45")
        # target zones
        for x, y in [(300, 170), (660, 170), (480, 360)]:
            s.circle(x, y, 26, mix(c1, "#ffd76a", .4))
            s.circle(x, y, 12, "#ffffff", opacity=".8")
        # defensive wall
        for i, x in enumerate([380, 440, 500]):
            s.character(x, 400, 0.85, shade(c2, .15 + i * .05), pose="stand",
                        acc=None)
        # ball curving in (dashed arc)
        s.path("M480 500 Q560 380 640 210", fill="none", stroke="#ffffff",
               stroke_width=5, stroke_dasharray="12 12", stroke_linecap="round")
        s.circle(648, 198, 26, "#ffffff")
        s.poly([(648, 172), (666, 190), (648, 208), (630, 190)], shade(c2, -.2))
        return
    # --- basketball hoop
    s.sky(r.choice(["day", "sunset", "dawn"]))
    s.rect(0, 420, W, 120, shade(c2, .05))
    s.rect(0, 420, W, 8, mix(c1, "#ffffff", .4))
    s.ellipse(480, 470, 320, 16, "#ffffff", opacity=".25")
    # backboard + rim
    bx = 640
    s.rect(bx - 16, 90, 120, 130, "#ffffff", rx=8, opacity=".92")
    s.rect(bx + 14, 120, 60, 60, "none", stroke=c1, stroke_width=5)
    s.ellipse(bx + 44, 230, 52, 14, "none", stroke=mix(c1, "#ff8fb5", .3),
              stroke_width=7)
    # net
    s.path(f"M{bx-8} 232 L{bx+20} 300 L{bx+68} 300 L{bx+96} 232",
           fill="none", stroke="#ffffff", stroke_width=3, opacity=".85")
    s.line(bx + 20, 266, bx + 68, 266, "#ffffff", sw=2, opacity=".7")
    s.line(bx - 8, 232, bx + 68, 300, "#ffffff", sw=2, opacity=".6")
    s.line(bx + 96, 232, bx + 20, 300, "#ffffff", sw=2, opacity=".6")
    # pole
    s.rect(bx + 100, 90, 14, 330, shade(c2, .2))
    # ball on arc
    s.path("M240 470 Q380 180 640 210", fill="none", stroke="#ffffff",
           stroke_width=5, stroke_dasharray="12 12", stroke_linecap="round")
    ball_x, ball_y = 430, 300
    s.circle(ball_x, ball_y, 34, mix(c1, "#ff8fb5", .25))
    s.circle(ball_x, ball_y, 34, "none", stroke=shade(c2, -.2), stroke_width=3)
    s.path(f"M{ball_x-34} {ball_y} Q{ball_x} {ball_y-6} {ball_x+34} {ball_y}",
           fill="none", stroke=shade(c2, -.2), stroke_width=3)
    s.path(f"M{ball_x} {ball_y-34} Q{ball_x+6} {ball_y} {ball_x} {ball_y+34}",
           fill="none", stroke=shade(c2, -.2), stroke_width=3)
    # player silhouette shooting
    s.character(210, 470, 1.0, c1, pose="jump", acc="headband")
    # second ball / floor lines
    s.circle(120, 480, 20, mix(c2, "#ffffff", .4))
    s.line(60, 500, 900, 500, "#ffffff", sw=3, opacity=".3")


def scene_golf(s, g, r):
    c1, c2 = s.c1, s.c2
    s.sky("day")
    # green
    s.ellipse(480, 380, 420, 130, mix(c1, "#ffffff", .25))
    s.ellipse(480, 380, 330, 100, mix(c1, "#ffffff", .4))
    s.ellipse(480, 380, 200, 62, mix(c1, "#ffffff", .55))
    # sand trap + water
    s.ellipse(260, 430, 90, 26, mix(c1, "#ffd76a", .55))
    s.ellipse(720, 330, 80, 24, mix(c1, "#9bd9ff", .5))
    s.path("M690 330 Q720 318 750 330 Q720 342 690 330 Z", fill="#ffffff", opacity=".5")
    # hole + flag
    hx, hy = 620, 330
    s.ellipse(hx, hy, 26, 10, "#1c1c22")
    s.flag(hx, hy, h=90, col=mix(c1, "#ff8fb5", .3))
    # ball + putt path
    bx, by = 300, 430
    s.circle(bx, by, 16, "#ffffff")
    s.circle(bx - 5, by - 5, 4, "#c9c9c9")
    s.path(f"M{bx+20} {by-6} Q430 {by-70} {hx-30} {hy+6}",
           fill="none", stroke="#ffffff", stroke_width=4, stroke_dasharray="10 10",
           stroke_linecap="round")
    # putter
    s.raw(f'<g transform="rotate(28 {bx-30} {by})">'
          f'<rect x="{bx-34}" y="{by-60}" width="7" height="66" rx="3" fill="{shade(c2, .1)}"/>'
          f'<rect x="{bx-40}" y="{by}" width="20" height="12" rx="4" fill="{shade(c2, -.1)}"/></g>')
    # trees
    for x, h in [(90, 120), (870, 140)]:
        s.rect(x, 380 - h, 14, h, shade(c2, -.2))
        s.circle(x + 7, 380 - h - 20, 46, mix(c1, "#ffffff", .2))
        s.circle(x - 24, 380 - h + 4, 30, mix(c1, "#ffffff", .12))


def scene_bowling(s, g, r):
    c1, c2 = s.c1, s.c2
    s.sky("flat")
    # lane (perspective)
    s.poly([(300, 120), (660, 120), (820, 500), (140, 500)], mix(c1, "#ffd76a", .35))
    s.poly([(300, 120), (660, 120), (820, 500), (140, 500)], "none",
           stroke="#ffffff", stroke_width=4, opacity=".7")
    # lane arrows
    for i, (x, y, sc) in enumerate([(440, 200, .5), (480, 200, .5), (520, 200, .5)]):
        s.poly([(x, y), (x - 14 * sc, y + 26 * sc), (x + 14 * sc, y + 26 * sc)],
               shade(c2, -.2), opacity=".8")
    s.line(480, 130, 480, 480, "#ffffff", sw=3, opacity=".5", stroke_dasharray="16 14")
    # pins triangle
    def pin(x, y, sc):
        s.path(f"M{x} {y-34*sc:.0f} C{x-13*sc:.0f} {y-22*sc:.0f} {x-13*sc:.0f} {y+8*sc:.0f} "
               f"{x-10*sc:.0f} {y+22*sc:.0f} L{x+10*sc:.0f} {y+22*sc:.0f} "
               f"C{x+13*sc:.0f} {y+8*sc:.0f} {x+13*sc:.0f} {y-22*sc:.0f} {x} {y-34*sc:.0f} Z",
               fill="#ffffff")
        s.rect(x - 12 * sc, y - 14 * sc, 24 * sc, 8 * sc, c1, rx=3 * sc)
    rows = [(480, 150, 1.0), (452, 175, .92), (508, 175, .92),
            (428, 200, .85), (480, 200, .85), (532, 200, .85),
            (406, 226, .78), (452, 226, .78), (498, 226, .78), (544, 226, .78)]
    for x, y, sc in rows:
        pin(x, y, sc)
    # ball rolling
    s.circle(480, 430, 44, c1)
    s.circle(466, 416, 7, shade(c2, -.2))
    s.circle(486, 412, 7, shade(c2, -.2))
    s.circle(476, 430, 7, shade(c2, -.2))
    s.circle(466, 416, 14, "#ffffff", opacity=".35")
    # gutters
    s.poly([(280, 120), (300, 120), (140, 500), (110, 500)], shade(c2, .2))
    s.poly([(660, 120), (680, 120), (850, 500), (820, 500)], shade(c2, .2))


def scene_rhythm(s, g, r):
    c1, c2 = s.c1, s.c2
    s.sky("night" if r.random() < .5 else "flat")
    # beat track (vertical lanes)
    lanes = 4
    lw = 110
    x0 = (W - lanes * lw) // 2
    s.rect(x0 - 10, 40, lanes * lw + 20, 460, shade(c2, -.1), rx=18)
    for i in range(lanes + 1):
        s.line(x0 + i * lw, 50, x0 + i * lw, 490, mix(c1, "#ffffff", .3), sw=2,
               opacity=".6")
    # hit line
    s.rect(x0 - 10, 400, lanes * lw + 20, 10, c1, rx=5)
    # notes approaching
    arrows = ["up", "down", "left", "right"]
    for i in range(7):
        lane = r.randrange(lanes)
        y = 80 + i * 44 + r.randint(-8, 8)
        x = x0 + lane * lw + lw / 2
        colr = c1 if i in (2, 5) else mix(c2, "#ffffff", .35)
        if i == 2:
            s.circle(x, y, 34, "none", stroke="#ffffff", stroke_width=4)
        d = arrows[lane % 4]
        if d == "up":
            s.poly([(x, y - 22), (x + 20, y + 14), (x - 20, y + 14)], colr)
        elif d == "down":
            s.poly([(x, y + 22), (x + 20, y - 14), (x - 20, y - 14)], colr)
        elif d == "left":
            s.poly([(x - 22, y), (x + 14, y + 20), (x + 14, y - 20)], colr)
        else:
            s.poly([(x + 22, y), (x - 14, y + 20), (x - 14, y - 20)], colr)
    # music notes (drawn shapes) on the sides
    def note(x, y, sc, colr):
        s.ellipse(x, y, 12 * sc, 9 * sc, colr)
        s.line(x + 11 * sc, y, x + 11 * sc, y - 34 * sc, colr, sw=4 * sc,
               stroke_linecap="round")
        s.path(f"M{x+11*sc:.0f} {y-34*sc:.0f} Q{x+30*sc:.0f} {y-28*sc:.0f} {x+28*sc:.0f} {y-8*sc:.0f}",
               fill="none", stroke=colr, stroke_width=4 * sc, stroke_linecap="round")
    note(120, 200, 1.2, mix(c1, "#ffd76a", .4))
    note(850, 300, 1.0, mix(c1, "#ffffff", .4))
    note(150, 420, .9, c1)
    # speaker / skateboard hint
    if "skate" in g["name"].lower():
        s.ellipse(820, 440, 70, 12, shade(c2, .2))
        s.rect(760, 420, 120, 12, mix(c1, "#ffd76a", .4), rx=6)
        s.circle(780, 436, 8, "#1c1c22")
        s.circle(860, 436, 8, "#1c1c22")


def scene_pool(s, g, r):
    c1, c2 = s.c1, s.c2
    s.sky("flat")
    # table
    s.rect(90, 110, 780, 330, shade(c2, -.15), rx=28)
    s.rect(120, 140, 720, 270, mix(c1, "#ffffff", .3), rx=16)
    s.rect(120, 140, 720, 270, "none", stroke="#ffffff", stroke_width=3, opacity=".5")
    # pockets
    for x, y in [(120, 140), (480, 140), (840, 140), (120, 410), (480, 410), (840, 410)]:
        s.circle(x, y, 22, "#141414")
    # rack of balls
    balls = [(600, 260, mix(c1, "#ff8fb5", .3)), (636, 240, mix(c1, "#ffd76a", .4)),
             (636, 280, c1), (672, 220, mix(c2, "#ffffff", .4)),
             (672, 260, mix(c1, "#ffffff", .4)), (672, 300, shade(c1, -.15)),
             (708, 240, mix(c1, "#ff8fb5", .3)), (708, 280, mix(c1, "#9bd9ff", .4))]
    for x, y, colr in balls:
        s.circle(x, y, 20, colr)
        s.circle(x, y, 9, "#ffffff")
        s.circle(x - 6, y - 7, 5, "#ffffff", opacity=".6")
    # cue ball + aim line
    s.circle(300, 275, 20, "#ffffff")
    s.circle(294, 269, 5, "#d8d8d8")
    s.line(280, 275, 580, 262, "#ffffff", sw=3, opacity=".7", stroke_dasharray="8 10")
    # cue stick
    s.raw(f'<g transform="rotate(-8 220 290)">'
          f'<rect x="120" y="284" width="130" height="10" rx="5" fill="{shade(c2, .2)}"/>'
          f'<rect x="120" y="284" width="26" height="10" rx="5" fill="{mix(c1, "#ffffff", .4)}"/></g>')
    # target ball glow
    s.circle(600, 260, 28, "none", stroke="#ffffff", stroke_width=3, opacity=".8")


def scene_connect(s, g, r):
    c1, c2 = s.c1, s.c2
    s.sky("flat")
    cols, rows, cell = 7, 6, 76
    bx, by = (W - cols * cell) // 2, 60
    s.rect(bx - 14, by - 14, cols * cell + 28, rows * cell + 40,
           shade(c2, -.05), rx=20)
    # discs: a diagonal four in a row wins
    grid = {}
    for row in range(rows):
        for col in range(cols):
            if r.random() < .45:
                grid[(col, row)] = r.choice([0, 1])
    win = [(2, 5), (3, 4), (4, 3), (5, 2)]
    for col, row in win:
        grid[(col, row)] = 0
    for row in range(rows):
        for col in range(cols):
            cx, cy = bx + col * cell + cell / 2, by + row * cell + cell / 2
            if (col, row) in grid:
                colr = c1 if grid[(col, row)] == 0 else mix(c2, "#ffffff", .45)
                s.circle(cx, cy, 28, colr)
                s.circle(cx - 8, cy - 8, 8, "#ffffff", opacity=".5")
                if (col, row) in win:
                    s.circle(cx, cy, 33, "none", stroke="#ffffff", stroke_width=3,
                             opacity=".9")
            else:
                s.circle(cx, cy, 28, shade(c2, .25))
    # falling disc + hand hint
    s.circle(bx + 3 * cell + cell / 2, 30, 26, c1)
    s.circle(bx + 3 * cell + cell / 2 - 7, 23, 7, "#ffffff", opacity=".5")
    # win line
    x1 = bx + 2 * cell + cell / 2
    y1 = by + 5 * cell + cell / 2
    x2 = bx + 5 * cell + cell / 2
    y2 = by + 2 * cell + cell / 2
    s.line(x1, y1, x2, y2, "#ffffff", sw=5, opacity=".85", stroke_linecap="round",
           stroke_dasharray="14 10")


def scene_ttt(s, g, r):
    c1, c2 = s.c1, s.c2
    s.sky("flat")
    cell = 130
    bx, by = (W - 3 * cell) // 2, 60
    s.rect(bx - 16, by - 16, 3 * cell + 32, 3 * cell + 32, shade(c2, -.05), rx=20)
    for i in (1, 2):
        s.line(bx + i * cell, by + 10, bx + i * cell, by + 3 * cell - 10,
               mix(c1, "#ffffff", .45), sw=6, stroke_linecap="round")
        s.line(bx + 10, by + i * cell, bx + 3 * cell - 10, by + i * cell,
               mix(c1, "#ffffff", .45), sw=6, stroke_linecap="round")
    # X wins on the diagonal
    marks = {(0, 0): "X", (1, 1): "X", (2, 2): "X",
             (0, 1): "O", (1, 0): "O", (2, 0): "O"}
    for (col, row), m in marks.items():
        cx, cy = bx + col * cell + cell / 2, by + row * cell + cell / 2
        if m == "X":
            s.line(cx - 30, cy - 30, cx + 30, cy + 30, c1, sw=12, stroke_linecap="round")
            s.line(cx + 30, cy - 30, cx - 30, cy + 30, c1, sw=12, stroke_linecap="round")
        else:
            s.circle(cx, cy, 32, "none", stroke=mix(c2, "#ffffff", .5), stroke_width=11)
    s.line(bx + 30, by + 30, bx + 3 * cell - 30, by + 3 * cell - 30,
           "#ffffff", sw=5, opacity=".8", stroke_dasharray="14 10",
           stroke_linecap="round")
    # side pieces
    s.line(120, 430, 160, 470, c1, sw=10, stroke_linecap="round")
    s.line(160, 430, 120, 470, c1, sw=10, stroke_linecap="round")
    s.circle(840, 450, 30, "none", stroke=mix(c2, "#ffffff", .5), stroke_width=10)


def scene_strategy(s, g, r):
    """Strategy Squares: a thinking match, NOT the plain centred board.
    Night table scene: small board on a stand at left, crowned blob
    character thinking it over at right, thought bubble with X and O."""
    c1, c2 = s.c1, s.c2
    s.sky("night")
    # wooden table
    s.rect(0, 400, 960, 140, shade(c2, -.15))
    s.rect(0, 400, 960, 10, mix(c1, "#ffffff", .25))
    # small 3x3 board on a stand, left side, mid-game state
    cell = 84
    bx, by = 90, 120
    s.rect(bx - 14, by - 14, 3 * cell + 28, 3 * cell + 28, shade(c2, -.05), rx=16)
    for i in (1, 2):
        s.line(bx + i * cell, by + 8, bx + i * cell, by + 3 * cell - 8,
               mix(c1, "#ffffff", .45), sw=5, stroke_linecap="round")
        s.line(bx + 8, by + i * cell, bx + 3 * cell - 8, by + i * cell,
               mix(c1, "#ffffff", .45), sw=5, stroke_linecap="round")
    marks = {(0, 0): "X", (2, 1): "X", (1, 0): "O", (1, 2): "O"}
    for (col, row), m in marks.items():
        cx, cy = bx + col * cell + cell / 2, by + row * cell + cell / 2
        if m == "X":
            s.line(cx - 20, cy - 20, cx + 20, cy + 20, c1, sw=9, stroke_linecap="round")
            s.line(cx + 20, cy - 20, cx - 20, cy + 20, c1, sw=9, stroke_linecap="round")
        else:
            s.circle(cx, cy, 22, "none", stroke=mix(c2, "#ffffff", .5), stroke_width=9)
    # board stand legs down to the table
    s.line(150, by + 3 * cell + 14, 150, 400, shade(c2, -.3), sw=8, stroke_linecap="round")
    s.line(300, by + 3 * cell + 14, 300, 400, shade(c2, -.3), sw=8, stroke_linecap="round")
    # thinking character, crowned, facing the board
    s.character(700, 400, sc=1.5, body=c1, pose="stand", acc="crown", flip=True)
    # thought bubble: X vs O
    s.circle(590, 250, 12, "#ffffff", opacity=".9")
    s.circle(620, 215, 17, "#ffffff", opacity=".9")
    s.ellipse(520, 140, 105, 58, "#ffffff", opacity=".95")
    s.line(490, 122, 514, 146, c2, sw=7, stroke_linecap="round")
    s.line(514, 122, 490, 146, c2, sw=7, stroke_linecap="round")
    s.circle(565, 134, 15, "none", stroke=c2, stroke_width=7)
    # loose pieces on the table
    s.line(450, 432, 478, 460, c1, sw=9, stroke_linecap="round")
    s.line(478, 432, 450, 460, c1, sw=9, stroke_linecap="round")
    s.circle(850, 446, 20, "none", stroke=mix(c2, "#ffffff", .5), stroke_width=9)


def scene_solitaire(s, g, r):
    c1, c2 = s.c1, s.c2
    s.sky("flat")
    # felt table
    s.ellipse(480, 330, 430, 210, mix(c1, "#ffffff", .2))
    s.ellipse(480, 330, 430, 210, "none", stroke="#ffffff", stroke_width=3,
              opacity=".4")

    def suit(cx, cy, kind, colr, sc=1.0):
        if kind == "heart":
            s.path(f"M{cx} {cy+14*sc:.0f} C{cx-24*sc:.0f} {cy-2*sc:.0f} {cx-18*sc:.0f} {cy-18*sc:.0f} "
                   f"{cx-6*sc:.0f} {cy-15*sc:.0f} C{cx-1*sc:.0f} {cy-13*sc:.0f} {cx} {cy-9*sc:.0f} {cx} {cy-8*sc:.0f} "
                   f"C{cx} {cy-9*sc:.0f} {cx+1*sc:.0f} {cy-13*sc:.0f} {cx+6*sc:.0f} {cy-15*sc:.0f} "
                   f"C{cx+18*sc:.0f} {cy-18*sc:.0f} {cx+24*sc:.0f} {cy-2*sc:.0f} {cx} {cy+14*sc:.0f} Z",
                   fill=colr)
        elif kind == "diamond":
            s.poly([(cx, cy - 18 * sc), (cx + 13 * sc, cy), (cx, cy + 18 * sc),
                    (cx - 13 * sc, cy)], colr)
        elif kind == "club":
            for dx, dy in [(0, -12), (-11, 4), (11, 4)]:
                s.circle(cx + dx * sc, cy + dy * sc, 10 * sc, colr)
            s.poly([(cx - 5 * sc, cy + 4 * sc), (cx + 5 * sc, cy + 4 * sc),
                    (cx + 9 * sc, cy + 18 * sc), (cx - 9 * sc, cy + 18 * sc)], colr)
        else:  # spade
            s.path(f"M{cx} {cy-18*sc:.0f} C{cx-16*sc:.0f} {cy-2*sc:.0f} {cx-22*sc:.0f} {cy+10*sc:.0f} "
                   f"{cx-8*sc:.0f} {cy+10*sc:.0f} C{cx-4*sc:.0f} {cy+10*sc:.0f} {cx-6*sc:.0f} {cy+16*sc:.0f} "
                   f"{cx-10*sc:.0f} {cy+20*sc:.0f} L{cx+10*sc:.0f} {cy+20*sc:.0f} "
                   f"C{cx+6*sc:.0f} {cy+16*sc:.0f} {cx+4*sc:.0f} {cy+10*sc:.0f} {cx+8*sc:.0f} {cy+10*sc:.0f} "
                   f"C{cx+22*sc:.0f} {cy+10*sc:.0f} {cx+16*sc:.0f} {cy-2*sc:.0f} {cx} {cy-18*sc:.0f} Z",
                   fill=colr)

    # fanned hand of cards
    kinds = ["heart", "diamond", "club", "spade"]
    cols = [mix(c1, "#ff8fb5", .25), c1, shade(c2, .1), mix(c2, "#ffffff", .4)]
    for i in range(5):
        x = 250 + i * 90
        y = 180 + (abs(i - 2) * 14)
        ang = (i - 2) * 7
        s.raw(f'<g transform="rotate({ang} {x+55} {y+80})">'
              f'<rect x="{x}" y="{y}" width="110" height="150" rx="12" fill="#ffffff"/>'
              f'<rect x="{x}" y="{y}" width="110" height="150" rx="12" fill="none" '
              f'stroke="{shade(c2, -.2)}" stroke-width="3"/></g>')
        # suit drawn unrotated approx at card centre (slight offset ok)
        suit(x + 55, y + 80, kinds[i % 4], cols[i % 4], 1.1)
    # draw pile + foundation
    s.rect(120, 380, 100, 140, shade(c2, .15), rx=12)
    s.rect(120, 380, 100, 140, "none", stroke=mix(c1, "#ffffff", .5),
           stroke_width=3, rx=12)
    s.gem(170, 450, 22, "diamond", c1)
    s.rect(740, 380, 100, 140, "#ffffff", rx=12)
    suit(790, 450, "heart", mix(c1, "#ff8fb5", .25), 1.3)


def scene_farm(s, g, r):
    name = g["name"].lower()
    c1, c2 = s.c1, s.c2
    garden = "garden" in name
    s.sky("day")
    # barn (farm) or greenhouse (garden)
    if not garden:
        s.poly([(700, 250), (800, 170), (900, 250)], shade(c2, -.1))
        s.rect(710, 250, 180, 120, mix(c1, "#ff8fb5", .15))
        s.rect(770, 300, 60, 70, shade(c2, -.2), rx=6)
        s.line(770, 300, 830, 370, shade(c2, -.2), sw=4)
        s.line(830, 300, 770, 370, shade(c2, -.2), sw=4)
    else:
        s.path("M690 370 L690 240 Q790 160 890 240 L890 370 Z",
               fill=mix(c1, "#ffffff", .45))
        s.path("M690 370 L690 240 Q790 160 890 240 L890 370 Z", fill="none",
               stroke=shade(c2, .1), stroke_width=4)
        s.line(790, 200, 790, 370, shade(c2, .1), sw=4)
    # field rows
    s.rect(0, 370, W, 170, shade(c2, .05))
    for row in range(3):
        y = 400 + row * 44
        s.path(f"M0 {y} Q480 {y-14} 960 {y}", fill="none",
               stroke=shade(c2, -.15), stroke_width=10, opacity=".8")
        for i, x in enumerate(range(60, 960, 90)):
            if garden:
                # flowers
                s.circle(x, y - 16, 10, r.choice([c1, mix(c1, "#ff8fb5", .3),
                                                   mix(c1, "#ffd76a", .4)]))
                s.circle(x, y - 16, 4, "#ffffff")
                s.line(x, y - 6, x, y + 6, mix(c1, "#ffffff", .3), sw=4)
            else:
                # crop sprouts
                s.path(f"M{x} {y} Q{x-10} {y-22} {x-18} {y-26} "
                       f"M{x} {y} Q{x+10} {y-22} {x+18} {y-26}",
                       fill="none", stroke=mix(c1, "#ffffff", .35),
                       stroke_width=5, stroke_linecap="round")
                if i % 3 == 0:
                    s.circle(x, y - 8, 9, mix(c1, "#ffd76a", .35))
    # watering can + basket
    if garden:
        s.rect(120, 440, 70, 40, mix(c2, "#ffffff", .4), rx=8)
        s.path("M190 450 L230 430", fill="none", stroke=mix(c2, "#ffffff", .4),
               stroke_width=6, stroke_linecap="round")
        for i in range(3):
            s.circle(236 + i * 6, 446 + i * 8, 3, mix(c1, "#9bd9ff", .4))
    else:
        s.ellipse(150, 470, 60, 26, mix(c1, "#ffd76a", .4))
        s.circle(130, 448, 12, mix(c1, "#ff8fb5", .3))
        s.circle(160, 442, 12, c1)
        s.circle(185, 450, 12, mix(c1, "#ffd76a", .35))
    # sun + fence
    s.rect(0, 356, W, 8, "#ffffff", opacity=".4")
    for x in range(20, 960, 70):
        s.rect(x, 330, 10, 40, shade(c2, -.1), rx=3)
    s.rect(0, 340, W, 8, shade(c2, -.1), rx=4)


def scene_cooking(s, g, r):
    name = g["name"].lower()
    c1, c2 = s.c1, s.c2
    pet = "pet" in name
    s.sky("flat")
    # wall + shelf
    s.rect(0, 0, W, 300, mix(c1, "#ffffff", .5))
    s.rect(0, 300, W, 240, shade(c2, .1))
    s.rect(120, 130, 300, 14, shade(c2, .15), rx=7)
    for i, colr in enumerate([c1, mix(c1, "#ffd76a", .4), mix(c2, "#ffffff", .4)]):
        s.rect(150 + i * 90, 92, 52, 38, colr, rx=8)
    # counter
    s.rect(80, 380, 800, 26, mix(c1, "#ffffff", .3), rx=10)
    s.rect(100, 406, 760, 100, shade(c2, -.05))
    if pet:
        # pet (cat) + care items
        s.ellipse(480, 360, 90, 44, mix(c1, "#ff8fb5", .25))
        s.circle(560, 320, 36, mix(c1, "#ff8fb5", .25))
        s.poly([(536, 296), (544, 268), (556, 292)], mix(c1, "#ff8fb5", .25))
        s.poly([(572, 292), (584, 268), (590, 296)], mix(c1, "#ff8fb5", .25))
        s.circle(548, 316, 4, shade(c2, -.3))
        s.circle(570, 316, 4, shade(c2, -.3))
        s.path("M556 326 Q562 332 568 326", fill="none", stroke=shade(c2, -.3),
               stroke_width=3, stroke_linecap="round")
        s.path("M570 350 Q640 330 660 300", fill="none",
               stroke=mix(c1, "#ff8fb5", .25), stroke_width=12, stroke_linecap="round")
        # food bowl + brush
        s.path("M180 380 L280 380 L268 406 L192 406 Z", fill=c1)
        s.circle(230, 372, 10, mix(c1, "#ffd76a", .4))
        s.circle(250, 368, 8, mix(c1, "#ff8fb5", .3))
        s.rect(700, 340, 90, 26, shade(c2, .2), rx=8)
        for x in range(706, 786, 10):
            s.line(x, 340, x, 326, shade(c2, .2), sw=3)
        s.rect(790, 348, 50, 10, shade(c2, .1), rx=5)
        return
    # chef character
    s.character(180, 380, 1.0, c1, pose="stand", acc="hat")
    # pot with steam
    s.ellipse(480, 380, 120, 34, shade(c2, -.2))
    s.rect(380, 320, 200, 60, shade(c2, .15), rx=16)
    s.ellipse(480, 320, 100, 16, mix(c1, "#ffffff", .3))
    for i, x in enumerate([440, 480, 520]):
        s.path(f"M{x} {300-i*6} Q{x+14} {280-i*6} {x} {258-i*6}",
               fill="none", stroke="#ffffff", stroke_width=5, opacity=".7",
               stroke_linecap="round")
    # order ticket + ingredients
    s.rect(660, 240, 130, 110, "#ffffff", rx=10)
    s.rect(680, 262, 90, 8, c1, rx=4)
    s.rect(680, 282, 70, 8, mix(c2, "#ffffff", .4), rx=4)
    s.rect(680, 302, 80, 8, mix(c2, "#ffffff", .4), rx=4)
    s.circle(330, 380, 20, mix(c1, "#ff8fb5", .3))   # tomato
    s.circle(330, 372, 6, mix(c1, "#ffffff", .4))
    s.ellipse(620, 372, 26, 16, mix(c1, "#ffd76a", .4))  # bread
    s.rect(600, 356, 40, 8, shade(c2, -.1), rx=4)


def scene_builder(s, g, r):
    name = g["name"].lower()
    c1, c2 = s.c1, s.c2
    train = "train" in name
    s.sky(r.choice(["day", "dawn"]))
    if train:
        # tracks + train + stations
        s.rect(0, 420, W, 120, shade(c2, .05))
        s.rect(0, 420, W, 10, "#ffffff", opacity=".4")
        for y in (452, 500):
            s.line(0, y, W, y, shade(c2, -.25), sw=8)
        for x in range(20, 960, 60):
            s.rect(x, 444, 30, 64, shade(c2, -.2), rx=4)
        # train
        for i, x in enumerate([220, 400, 580]):
            s.rect(x, 330, 160, 96, c1 if i % 2 == 0 else mix(c1, "#ffffff", .3),
                   rx=14)
            s.rect(x + 16, 352, 48, 34, mix(c1, "#ffffff", .5), rx=6)
            s.rect(x + 76, 352, 48, 34, mix(c1, "#ffffff", .5), rx=6)
            s.circle(x + 40, 432, 14, "#1c1c22")
            s.circle(x + 120, 432, 14, "#1c1c22")
        # station
        s.rect(60, 330, 110, 96, shade(c2, .15), rx=10)
        s.poly([(50, 330), (115, 280), (180, 330)], mix(c1, "#ffd76a", .4))
        s.rect(90, 380, 50, 46, shade(c2, -.2), rx=6)
        s.flag(115, 280, h=40)
        return
    # town skyline
    s.hills(500, col=shade(c2, .12), col2=shade(c2, -.02))
    houses = [(60, 380, 130, 120), (210, 340, 110, 160), (340, 390, 140, 110),
              (500, 330, 120, 170), (640, 380, 130, 120), (790, 350, 110, 150)]
    for i, (x, y, w, h) in enumerate(houses):
        colr = c1 if i % 2 == 0 else mix(c1, "#ffffff", .3)
        s.rect(x, y, w, h, colr)
        s.poly([(x - 8, y), (x + w / 2, y - 46), (x + w + 8, y)], shade(c2, -.1))
        for wy in range(y + 24, y + h - 20, 40):
            for wx in range(x + 16, x + w - 16, 36):
                s.rect(wx, wy, 16, 20, mix(c1, "#ffe9a8", .5), rx=3)
        s.rect(x + w / 2 - 14, y + h - 44, 28, 44, shade(c2, -.25), rx=6)
    # crane
    s.rect(860, 180, 12, 320, shade(c2, .2))
    s.line(860, 190, 960, 190, shade(c2, .2), sw=8)
    s.line(920, 190, 920, 260, shade(c2, -.2), sw=3, stroke_dasharray="5 5")
    s.rect(896, 260, 48, 34, mix(c1, "#ffd76a", .4), rx=6)
    # road
    s.rect(0, 500, W, 40, shade(c2, -.2))
    for x in range(30, 960, 100):
        s.rect(x, 516, 50, 7, "#ffffff", rx=3, opacity=".7")


def scene_fishing(s, g, r):
    name = g["name"].lower()
    c1, c2 = s.c1, s.c2
    aquarium = "aquarium" in name
    s.sky("day")
    if aquarium:
        # fish tank
        s.rect(180, 110, 600, 330, mix(c1, "#9bd9ff", .35), rx=24)
        s.rect(180, 110, 600, 330, "none", stroke=shade(c2, .2), stroke_width=6,
               rx=24)
        s.rect(160, 90, 640, 24, shade(c2, .15), rx=10)
        s.rect(160, 436, 640, 24, shade(c2, .15), rx=10)
        # plants + pebbles
        for x in (260, 700):
            s.path(f"M{x} 436 Q{x-16} 380 {x-6} 350 M{x} 436 Q{x+4} 372 {x+16} 344",
                   fill="none", stroke=mix(c1, "#ffffff", .3), stroke_width=7,
                   stroke_linecap="round")
        for x in range(220, 760, 60):
            s.ellipse(x, 432, 26, 10, mix(c2, "#ffffff", .4))
        # fish
        def fish(x, y, sc, colr, flip=False):
            sgn = -1 if flip else 1
            s.ellipse(x, y, 34 * sc, 18 * sc, colr)
            s.poly([(x - 30 * sgn * sc, y), (x - 52 * sgn * sc, y - 16 * sc),
                    (x - 52 * sgn * sc, y + 16 * sc)], colr)
            s.circle(x + 14 * sgn * sc, y - 4 * sc, 4 * sc, "#1c1c22")
            s.path(f"M{x+4*sc:.0f} {y+8*sc:.0f} Q{x+12*sc:.0f} {y+12*sc:.0f} {x+20*sc:.0f} {y+8*sc:.0f}",
                   fill="none", stroke="#1c1c22", stroke_width=2 * sc,
                   stroke_linecap="round")
        fish(380, 220, 1.0, c1)
        fish(580, 300, .85, mix(c1, "#ffd76a", .4), flip=True)
        fish(480, 360, .7, mix(c1, "#ff8fb5", .3))
        # bubbles
        for x, y, rr in [(340, 300, 8), (620, 200, 6), (500, 260, 5), (660, 360, 7)]:
            s.circle(x, y, rr, "none", stroke="#ffffff", stroke_width=2.5,
                     opacity=".8")
        return
    # lake + rod
    s.rect(0, 300, W, 240, mix(c1, "#9bd9ff", .3))
    s.path("M0 300 Q120 288 240 300 T480 300 T720 300 T960 300 V540 H0Z",
           fill=mix(c1, "#ffffff", .4), opacity=".6")
    for i in range(4):
        x = r.randint(80, 880)
        s.ellipse(x, 340 + i * 44, r.randint(40, 80), 5, "#ffffff", opacity=".35")
    # fish under water
    for x, y, sc in [(300, 420, .9), (650, 470, 1.1), (800, 400, .7)]:
        s.ellipse(x, y, 36 * sc, 18 * sc, shade(c2, .15))
        s.poly([(x - 32 * sc, y), (x - 56 * sc, y - 16 * sc),
                (x - 56 * sc, y + 16 * sc)], shade(c2, .15))
        s.circle(x + 16 * sc, y - 4 * sc, 4 * sc, "#ffffff")
    # rod + line + bobber
    s.line(120, 120, 480, 330, shade(c2, -.2), sw=7, stroke_linecap="round")
    s.line(480, 330, 480, 380, shade(c2, -.2), sw=3)
    s.circle(480, 396, 16, mix(c1, "#ff8fb5", .3))
    s.circle(480, 396, 16, "none", stroke="#ffffff", stroke_width=3)
    s.circle(480, 388, 6, "#ffffff")
    # ripples
    s.ellipse(480, 412, 46, 8, "none", stroke="#ffffff", stroke_width=3, opacity=".7")
    s.ellipse(480, 412, 70, 12, "none", stroke="#ffffff", stroke_width=2, opacity=".4")
    # dock + character
    s.rect(0, 260, 260, 40, shade(c2, .2), rx=8)
    s.character(140, 260, 0.95, c1, pose="stand", acc="hat")
    s.rect(40, 300, 14, 60, shade(c2, .1))
    s.rect(200, 300, 14, 60, shade(c2, .1))


def scene_sorting(s, g, r):
    c1, c2 = s.c1, s.c2
    s.sky("flat")
    # conveyor + trays
    s.rect(60, 120, 840, 40, shade(c2, .15), rx=12)
    for x in range(80, 900, 50):
        s.circle(x, 140, 10, shade(c2, -.1))
    # three trays
    trays = [(150, c1), (420, mix(c1, "#ffd76a", .35)), (690, mix(c2, "#ffffff", .4))]
    for x, colr in trays:
        s.path(f"M{x} 300 L{x+180} 300 L{x+162} 470 L{x+18} 470 Z", fill=colr)
        s.path(f"M{x} 300 L{x+180} 300 L{x+162} 470 L{x+18} 470 Z", fill="none",
               stroke=shade(c2, -.2), stroke_width=3)
        s.rect(x - 6, 288, 192, 16, shade(c2, .1), rx=8)
    # balls in trays
    balls = [(200, 330, c1), (260, 360, c1), (230, 410, c1),
             (470, 330, mix(c1, "#ffd76a", .35)), (530, 370, mix(c1, "#ffd76a", .35)),
             (740, 340, mix(c2, "#ffffff", .4)), (800, 380, mix(c2, "#ffffff", .4))]
    for x, y, colr in balls:
        s.circle(x, y, 24, colr)
        s.circle(x - 7, y - 7, 7, "#ffffff", opacity=".55")
    # balls on conveyor (unsorted)
    for i, (x, colr) in enumerate([(200, mix(c1, "#ffd76a", .35)),
                                   (420, mix(c2, "#ffffff", .4)),
                                   (640, c1), (800, mix(c1, "#ff8fb5", .3))]):
        s.circle(x, 96, 22, colr)
        s.circle(x - 6, 90, 6, "#ffffff", opacity=".55")
    # falling ball with motion
    s.circle(510, 220, 24, c1)
    s.line(510, 190, 510, 170, "#ffffff", sw=4, opacity=".6", stroke_linecap="round")
    s.line(486, 196, 486, 180, "#ffffff", sw=4, opacity=".6", stroke_linecap="round")
    s.line(534, 196, 534, 180, "#ffffff", sw=4, opacity=".6", stroke_linecap="round")


def scene_color(s, g, r):
    c1, c2 = s.c1, s.c2
    s.sky("flat")
    # canvas with geometric art, half coloured
    cx, cy, cw, ch = 250, 70, 460, 380
    s.rect(cx - 14, cy - 14, cw + 28, ch + 28, "#ffffff", rx=18)
    s.rect(cx - 14, cy - 14, cw + 28, ch + 28, "none", stroke=shade(c2, -.15),
           stroke_width=4, rx=18)
    # big shapes, some filled, some outline-only
    s.circle(cx + 120, cy + 110, 70, c1)
    s.poly([(cx + 260, cy + 40), (cx + 380, cy + 180), (cx + 260, cy + 180)],
           mix(c1, "#ffd76a", .35))
    s.rect(cx + 60, cy + 240, 130, 100, "none", stroke=c1, stroke_width=5, rx=10)
    s.gem(cx + 330, cy + 290, 44, "star", "none" if False else mix(c2, "#ffffff", .4))
    s.circle(cx + 330, cy + 290, 44, "none", stroke=mix(c2, "#ffffff", .4),
             stroke_width=5)
    s.ellipse(cx + 380, cy + 60, 40, 26, "none", stroke=c1, stroke_width=5)
    # palette blobs (right)
    palette = [c1, mix(c1, "#ff8fb5", .3), mix(c1, "#ffd76a", .4),
               mix(c2, "#ffffff", .4), mix(c1, "#9bd9ff", .4)]
    for i, colr in enumerate(palette):
        x, y = 790, 120 + i * 66
        s.circle(x, y, 30, colr)
        s.circle(x, y, 30, "none", stroke=shade(c2, -.15), stroke_width=3,
                 opacity=".5")
        if i == 0:
            s.circle(x, y, 40, "none", stroke="#ffffff", stroke_width=4)
    # paint brush
    s.raw(f'<g transform="rotate(35 180 420)">'
          f'<rect x="168" y="380" width="24" height="90" rx="10" fill="{shade(c2, .15)}"/>'
          f'<rect x="164" y="360" width="32" height="26" rx="6" fill="#cfd6e4"/>'
          f'<path d="M164 360 Q180 320 196 360 Z" fill="{c1}"/></g>')
    # splats
    for x, y, rr in [(140, 150, 16), (880, 470, 20), (120, 470, 12)]:
        s.circle(x, y, rr, mix(c1, "#ff8fb5", .3))
        s.circle(x + rr, y + rr * .5, rr * .4, mix(c1, "#ff8fb5", .3))


def scene_typing(s, g, r):
    c1, c2 = s.c1, s.c2
    s.sky("flat")
    # word display bar
    s.rect(180, 70, 600, 84, shade(c2, -.05), rx=16)
    word = g["name"].split()[0].upper()
    for i, ch in enumerate(word):
        x = 300 + i * (480 // max(len(word), 1)) if len(word) > 1 else 480
        s.text(x, 128, ch, 44, "#ffffff" if i < 2 else mix(c1, "#ffffff", .6))
    s.line(300 + 1.5 * (480 // max(len(word), 1)), 92,
           300 + 1.5 * (480 // max(len(word), 1)), 136, c1, sw=4)
    # keyboard
    rows = ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"]
    kw, kh, gap = 74, 64, 10
    y0 = 200
    for ri, row in enumerate(rows):
        total = len(row) * (kw + gap) - gap
        x0 = (W - total) // 2
        for ci, ch in enumerate(row):
            x = x0 + ci * (kw + gap)
            y = y0 + ri * (kh + gap)
            hot = (ri == 1 and ci == 3)
            s.rect(x, y, kw, kh, c1 if hot else shade(c2, .12), rx=10)
            s.rect(x, y, kw, kh, "none",
                   stroke=mix(c1, "#ffffff", .4) if hot else "none",
                   stroke_width=3, rx=10)
            s.text(x + kw / 2, y + 42, ch, 30, "#ffffff")
            if hot:
                s.rect(x - 6, y - 6, kw + 12, kh + 12, "none", stroke="#ffffff",
                       stroke_width=3, rx=12)
    # space bar
    s.rect(280, y0 + 3 * (kh + gap), 400, 56, shade(c2, .12), rx=12)
    s.rect(280, y0 + 3 * (kh + gap), 400, 56, "none",
           stroke=mix(c1, "#ffffff", .4), stroke_width=3, rx=12)
    s.text(480, y0 + 3 * (kh + gap) + 38, "SPACE", 22, mix(c1, "#ffffff", .6))
    # speed lines + wpm badge
    s.circle(840, 110, 46, mix(c1, "#ffd76a", .4))
    s.text(840, 122, "WPM", 20, "#ffffff")


def scene_sequence(s, g, r):
    name = g["name"].lower()
    c1, c2 = s.c1, s.c2
    s.sky("night" if "memory" in name else "flat")
    if "count" in name:
        # shapes to count
        shapes = []
        for _ in range(r.randint(9, 13)):
            shapes.append((r.randint(90, 870), r.randint(120, 400),
                           r.choice(["circle", "star", "square"]),
                           r.choice([c1, mix(c1, "#ffd76a", .35),
                                     mix(c2, "#ffffff", .45)])))
        for x, y, kind, colr in shapes:
            s.gem(x, y, r.randint(18, 30), kind, colr)
        # count tray
        s.rect(300, 440, 360, 60, shade(c2, -.05), rx=14)
        for i in range(3):
            s.circle(360 + i * 120, 470, 20, mix(c1, "#ffffff", .3))
            s.text(360 + i * 120, 478, "?", 26, "#ffffff")
        return
    # Simon-style pads
    pads = [(330, 130, c1), (550, 130, mix(c1, "#ffd76a", .4)),
            (330, 300, mix(c2, "#ffffff", .45)), (550, 300, mix(c1, "#ff8fb5", .3))]
    order = [0, 2, 1, 3, 0]
    for i, (x, y, colr) in enumerate(pads):
        lit = order[0] == i
        s.rect(x, y, 150, 130, colr, rx=18, opacity="1" if lit else ".75")
        s.rect(x, y, 150, 130, "none", stroke="#ffffff",
               stroke_width=5 if lit else 2, rx=18,
               opacity="1" if lit else ".4")
        s.text(x + 75, y + 82, str(i + 1), 44, "#ffffff")
    # sequence trail
    pts = [(405, 195), (405, 365), (625, 195), (625, 365), (405, 195)]
    d = "M" + " L".join(f"{x} {y}" for x, y in pts)
    s.path(d, fill="none", stroke="#ffffff", stroke_width=4,
           stroke_dasharray="12 12", opacity=".7", stroke_linecap="round")
    for i, (x, y) in enumerate(pts[:4]):
        s.circle(x, y, 12, mix(c1, "#ffd76a", .4))
        s.text(x, y + 5, str(i + 1), 14, shade(c2, -.2))
    s.rect(180, 450, 600, 50, shade(c2, -.05), rx=12)
    s.text(480, 483, "REPEAT THE LIGHTS", 24, mix(c1, "#ffffff", .6))


# ================================================================ dispatch
SCENES = {
    "racing": scene_racing, "platform": scene_platform,
    "runner": scene_runner, "blocks": scene_blocks,
    "bubble": scene_bubble, "merge": scene_merge,
    "breaker": scene_breaker, "maze": scene_maze,
    "stack": scene_stack, "match": scene_match,
    "memory": scene_memory, "sudoku": scene_sudoku,
    "word": scene_word, "sokoban": scene_sokoban,
    "pattern": scene_pattern, "reaction": scene_reaction,
    "hoops": scene_hoops, "golf": scene_golf,
    "bowling": scene_bowling, "rhythm": scene_rhythm,
    "pool": scene_pool, "connect": scene_connect,
    "ttt": scene_ttt, "solitaire": scene_solitaire,
    "farm": scene_farm, "cooking": scene_cooking,
    "builder": scene_builder, "fishing": scene_fishing,
    "sorting": scene_sorting, "color": scene_color,
    "typing": scene_typing, "sequence": scene_sequence,
}


SCENE_OVERRIDES = {"strategy-squares": scene_strategy}


def build(game):
    seed = int(hashlib.md5(game["id"].encode()).hexdigest()[:8], 16)
    r = random.Random(seed)
    s = Scene(game, r)
    SCENE_OVERRIDES.get(game["id"], SCENES[game["engine"]])(s, game, r)
    return s.svg()


def main():
    for g in GAMES:
        (HERE / f'{g["id"]}.svg').write_text(build(g))
    print(f"wrote {len(GAMES)} covers")


if __name__ == "__main__":
    main()
