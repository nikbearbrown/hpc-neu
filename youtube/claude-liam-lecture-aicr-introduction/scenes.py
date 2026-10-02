from manim import *
import numpy as np
import json as _json, os as _os

# ═════════════════════════════ ISO KIT (show-tell) ═════════════════════════════
STAGE = "#F2F0E9"; INK = "#3D3929"; TERRA = "#D97757"; DIM = "#8B8F96"; GHOST = "#D9D4C7"; CARD = "#FAF9F5"
BOX_TOP, BOX_L, BOX_R = "#F3E9D8", "#DCC9AA", "#C7AE86"          # kraft cardboard: top, left face, right face (deep enough for Gate V contrast)
BOX_IN1, BOX_IN2, BOX_FLOOR = "#CDB894", "#BFA67E", "#B39A72"     # inside walls + floor
DARK_TOP, DARK_L, DARK_R = "#3A3530", "#26221F", "#1E1B18"        # MCP / server blocks
PAGE_TOP, PAGE_L, PAGE_R = "#FFFFFF", "#ECE7DF", "#E2DCD2"         # skill pages
BAR1, BAR2, BAR3 = "#8B8F96", "#B4AFA6", "#D9D4C7"                # chart segments, dim to ghost
SERIF = "EB Garamond"
C30 = 0.8660254
config.background_color = STAGE


def T(s, size=36, color=INK, bold=False):
    return Text(s, font=SERIF, color=color, font_size=size, weight="BOLD" if bold else "NORMAL")


class Iso:
    """Isometric projection: x runs right-up, y runs left-up, z runs up. (ox, oy) is where (0,0,0) lands."""
    def __init__(self, ox=0.0, oy=0.0, s=1.0):
        self.ox, self.oy, self.s = ox, oy, s

    def p(self, x, y, z=0.0):
        return np.array([self.ox + (x - y) * C30 * self.s, self.oy + (x + y) * 0.5 * self.s + z * self.s, 0.0])

    def v(self, dx, dy, dz=0.0):
        return self.p(dx, dy, dz) - self.p(0, 0, 0)

    def quad(self, pts, fill, stroke=INK, sw=4):
        return Polygon(*[self.p(*q) for q in pts], fill_color=fill, fill_opacity=1, stroke_color=stroke, stroke_width=sw)

    def box(self, x0, y0, z0, w, d, h, top=BOX_TOP, left=BOX_L, right=BOX_R, sw=4):
        """Closed box: the two front faces (x = x0 and y = y0) plus the top."""
        x1, y1, z1 = x0 + w, y0 + d, z0 + h
        return VGroup(
            self.quad([(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)], left, sw=sw),
            self.quad([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], right, sw=sw),
            self.quad([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], top, sw=sw))

    def open_box(self, x0, y0, z0, w, d, h):
        """(back, front): floor + inner back walls, then the front walls. Put contents between them."""
        x1, y1, z1 = x0 + w, y0 + d, z0 + h
        back = VGroup(
            self.quad([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)], BOX_FLOOR),
            self.quad([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], BOX_IN1),
            self.quad([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], BOX_IN2))
        front = VGroup(
            self.quad([(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)], BOX_L),
            self.quad([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], BOX_R))
        back.set_z_index(0); front.set_z_index(2)
        return back, front

    def tape(self, x0, y0, z1, w, d, drop=0.35, t=0.22):
        """Terracotta tape across the top (along x) and down the left front face."""
        ym = y0 + d / 2
        return VGroup(
            self.quad([(x0, ym - t, z1), (x0 + w, ym - t, z1), (x0 + w, ym + t, z1), (x0, ym + t, z1)], TERRA, sw=0),
            self.quad([(x0, ym - t, z1), (x0, ym + t, z1), (x0, ym + t, z1 - drop), (x0, ym - t, z1 - drop)], TERRA, sw=0))

    def mcp(self, x0, y0, z0, w=1.3, d=1.3, h=0.7):
        """Dark MCP block with two light ports on its right front face."""
        body = self.box(x0, y0, z0, w, d, h, DARK_TOP, DARK_L, DARK_R)
        ports = VGroup(*[self.box(x0 + w * f, y0 - 0.18, z0 + h * 0.3, w * 0.16, 0.18, h * 0.3, GHOST, BOX_IN1, BOX_IN2, sw=1)
                         for f in (0.22, 0.58)])
        return VGroup(body, ports)

    def page(self, x0, y0, z0, w=1.1, d=1.4):
        """A skill page lying flat: white slab, three ghost text lines, one terracotta dot."""
        slab = self.box(x0, y0, z0, w, d, 0.06, PAGE_TOP, PAGE_L, PAGE_R, sw=1.5)
        zt = z0 + 0.06
        lines = VGroup(*[Line(self.p(x0 + 0.2, y0 + d * f, zt), self.p(x0 + w - 0.2, y0 + d * f, zt), color=GHOST, stroke_width=4)
                         for f in (0.3, 0.5, 0.7)])
        dot = Dot(self.p(x0 + 0.2, y0 + d * 0.86, zt), radius=0.06, color=TERRA)
        return VGroup(slab, lines, dot)

    def server(self, x0, y0, z0, w=1.4, d=1.4, slab=0.42, n=3):
        """A stack of dark server slabs; returns (stack, lights) — lights start ghost, turn terracotta."""
        stack = VGroup(*[self.box(x0, y0, z0 + i * (slab + 0.04), w, d, slab, DARK_TOP, DARK_L, DARK_R) for i in range(n)])
        lights = VGroup(*[Dot(self.p(x0 + 0.25, y0, z0 + i * (slab + 0.04) + slab / 2), radius=0.06, color=GHOST) for i in range(n)])
        return stack, lights


def ease_in(t):
    """Quadratic ease-in (things dropping into a box). Local: Gate A's stub has no ease_in_quad."""
    return t * t


def check(x, y, s=0.2, color=INK, w=7):
    return VGroup(Line([x - s, y, 0], [x - s * 0.3, y - s * 0.75, 0], color=color, stroke_width=w),
                  Line([x - s * 0.3, y - s * 0.75, 0], [x + s * 1.1, y + s * 0.85, 0], color=color, stroke_width=w))


def cursor(x, y, s=0.45):
    return Polygon([x, y, 0], [x, y - s, 0], [x + s * 0.28, y - s * 0.72, 0], [x + s * 0.62, y - s * 0.66, 0],
                   fill_color=INK, fill_opacity=1, stroke_color=CARD, stroke_width=2)


def pill(x, y, w, h=0.62, fill="#FFFFFF"):
    return RoundedRectangle(width=w, height=h, corner_radius=h / 2, fill_color=fill, fill_opacity=1, stroke_width=0).move_to([x, y, 0])


# ═════════════════════════════ pacing (narration is the clock) ═════════════════════════════
try:
    _SHEET = _json.load(open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "beat_sheet.json")))
    _TARGET = {b["beat_id"]: float(b.get("actual_duration_s") or b.get("estimated_duration_s") or 0) for b in _SHEET["beats"]}
    _NARR = {b["beat_id"]: b["narration_text"] for b in _SHEET["beats"]}
except Exception:
    _TARGET, _NARR = {}, {}


def _elapsed(self):
    rt = getattr(getattr(self, "renderer", None), "time", None)
    return float(rt) if isinstance(rt, (int, float)) else 0.0


def until(self, phrase, lead=0.25):
    """Wait until `phrase` is spoken (its character share of the narration × the measured audio)."""
    bid = type(self).__name__.split("_")[0]
    n, target = _NARR.get(bid, ""), _TARGET.get(bid, 0)
    if not n or not target or phrase not in n:
        return
    gap = target * n.index(phrase) / len(n) - lead - _elapsed(self)
    if gap > 0.05:
        self.wait(gap)


def finish(self):
    target = _TARGET.get(type(self).__name__.split("_")[0], 0)
    self.wait(max(0.3, target - _elapsed(self)) if target else 2.0)


# ─────────────── midpoint guard: GATE T and Gate V sample each clip at its midpoint ───────────────
class ST:
    """Midpoint guard: no animation straddles the clip midpoint. Attached to every beat class at the
    bottom of scenes.py (run.sh finds scenes only by the literal `(Scene)`)."""
    def play(self, *anims, **kw):
        if not all(isinstance(a, Wait) for a in anims):
            kw["run_time"] = guard(self, float(kw.get("run_time", 1.0)))
        return Scene.play(self, *anims, **kw)


def guard(self, rt):
    """If an animation of length rt starting now would straddle the midpoint, either shorten it to land
    before the midpoint or wait until just after it. Returns the run time to use."""
    tgt = _TARGET.get(type(self).__name__.split("_")[0], 0)
    if not tgt:
        return rt
    mid, t0 = tgt / 2.0, _elapsed(self)
    if t0 < mid + 0.22 and t0 + rt > mid - 0.22:
        room = mid - 0.24 - t0
        if room >= 0.6 * rt and room > 0.25:
            return room
        Scene.wait(self, max(0.02, mid + 0.24 - t0))
    return rt


def done(self):
    """finish() plus a pacing report (a clip must not outrun its audio: compile centre-cuts it)."""
    bid = type(self).__name__.split("_")[0]
    t = _elapsed(self)
    tgt = _TARGET.get(bid, 0)
    print(f"[pace] {bid} content={t:.2f}s target={tgt:.2f}s" + ("  OVER" if t > tgt - 0.1 else ""))
    if tgt:
        self.wait(max(0.05, tgt - t - 0.05))     # end 0.05 s under the audio (4K frame rounding)
    else:
        self.wait(2.0)


# ═════════════════════════════ the lecture's cast (shared by every act) ═════════════════════════════
# One cast, whole film. The same object is the same picture in every beat:
#   EXPLORER  small dark rack, 2 slabs      (Northeastern's own cluster)      explorer_rack()
#   AICR      large dark rack, 4 slabs, wide (the shared GPU cluster)          aicr_rack()
#   JOB       a small kraft box with one terracotta tape                        job_box()
#   HOME      a small closed kraft box                                          home_box()
#   SCRATCH   a wide open kraft bin                                             scratch_bin()  -> (back, front)
#   PROJECT   a tall white cabinet with ghost drawer lines                      project_cabinet()
#   GPU       a dark block with a ghost light that turns terracotta when busy   gpu_block()    -> (body, light)
MONO = "Menlo"


def M(s, size=34, color=INK):
    """Mono label for real paths, usernames and commands."""
    return Text(s, font=MONO, color=color, font_size=size)


def explorer_rack(iso, x0=0.0, y0=0.0, z0=0.0):
    return iso.server(x0, y0, z0, w=1.3, d=1.3, slab=0.42, n=2)


def aicr_rack(iso, x0=0.0, y0=0.0, z0=0.0):
    return iso.server(x0, y0, z0, w=2.4, d=1.6, slab=0.46, n=4)


def job_box(iso, x0=0.0, y0=0.0, z0=0.0, s=0.7):
    return VGroup(iso.box(x0, y0, z0, s, s, s * 0.8), iso.tape(x0, y0, z0 + s * 0.8, s, s, drop=0.18, t=0.08))


def home_box(iso, x0=0.0, y0=0.0, z0=0.0):
    return iso.box(x0, y0, z0, 1.2, 1.2, 0.9)


def scratch_bin(iso, x0=0.0, y0=0.0, z0=0.0):
    return iso.open_box(x0, y0, z0, 2.8, 1.8, 0.8)


def project_cabinet(iso, x0=0.0, y0=0.0, z0=0.0):
    body = iso.box(x0, y0, z0, 1.3, 1.1, 2.0, PAGE_TOP, PAGE_L, PAGE_R)
    lines = VGroup(*[Line(iso.p(x0 + 0.12, y0, z0 + 2.0 * f), iso.p(x0 + 1.18, y0, z0 + 2.0 * f), color=BAR1, stroke_width=4)
                     for f in (0.34, 0.67)])
    return VGroup(body, lines)


def gpu_block(iso, x0=0.0, y0=0.0, z0=0.0):
    body = iso.box(x0, y0, z0, 1.0, 1.0, 0.5, DARK_TOP, DARK_L, DARK_R)
    light = Dot(iso.p(x0 + 0.2, y0, z0 + 0.25), radius=0.07, color=GHOST)
    return body, light
# ═════════════════════════════ PART A · Act I (B10–B13) and Act II (B20, B22) ═════════════════════════════
# Stage map. Act I: the AICR rack stands centre (PA_RACK) in B10 and B12 and steps right (PA_RACK_R) in B13,
# where the Explorer rack takes the left. Act II: B20 runs on one diagonal (PA20), B22 is the username row.
PA_KRAFT = "#9C8462"                        # deep-kraft connector (drawing law: lines and belt edges are never ink)
PA_RACK = Iso(-0.25, -1.75, 0.7)            # the AICR rack, centre stage (B10, B12)
PA_RACK_R = Iso(3.35, -1.75, 0.7)           # the AICR rack, stepped right (B13)
PA_RACK_TOP = 1.96                          # z of the AICR rack's top face (4 slabs)


def pa_title(s):
    """Act title, top-left, for the whole first beat of an act."""
    t = T(s, 40)
    return t.move_to([-6.1 + t.width / 2, 3.0, 0])


def pa_slide_in(self, mob, vec, rt=0.7):
    """Slide a whole object in from off-stage, fully opaque (GATE T: never a half-faded dark block)."""
    rt = guard(self, rt)
    mob.shift(-vec)
    self.add(mob)
    self.play(mob.animate.shift(vec), run_time=rt)


def pa_drop(self, mobs, rt=0.55, lag=0.2, dist=5.0):
    rt = guard(self, rt)
    mobs = list(mobs)
    for m in mobs:
        m.shift(UP * dist)
        self.add(m)
    self.play(LaggedStart(*[m.animate.shift(DOWN * dist) for m in mobs], lag_ratio=lag), run_time=rt, rate_func=ease_in)


# ─────────────── B10 · six campuses, one shared cluster ───────────────
PA10_SITES = [(-4.7, 0.75), (-5.25, -1.15), (-3.9, -2.85), (4.7, 0.75), (5.25, -1.15), (3.9, -2.85)]
PA10_HUB = np.array([0.0, -0.35, 0.0])      # the rack's visual centre


def pa10_campus(k):
    """A small campus block: a kraft base with one smaller block on top."""
    iso = Iso(PA10_SITES[k][0], PA10_SITES[k][1], 0.6)
    return VGroup(iso.box(0, 0, 0, 1.2, 1.2, 0.5), iso.box(0.35, 0.35, 0.5, 0.5, 0.5, 0.45))


def pa10_ends(k):
    """(start, end) of the line from campus k to the cluster; both stop short of the blocks."""
    c = np.array([PA10_SITES[k][0], PA10_SITES[k][1] + 0.55, 0.0])
    u = (PA10_HUB - c) / np.linalg.norm(PA10_HUB - c)
    return c + u * 1.0, PA10_HUB - u * 2.05


def pa10_line(k):
    a, b = pa10_ends(k)
    return Line(a, b, color=PA_KRAFT, stroke_width=5)


def pa10_pad(outline=False):
    """The site: the footprint the cluster stands on."""
    pts = [(-0.3, -0.3, 0), (2.7, -0.3, 0), (2.7, 1.9, 0), (-0.3, 1.9, 0)]
    if outline:
        return Polygon(*[PA_RACK.p(*q) for q in pts], stroke_color=PA_KRAFT, stroke_width=4, fill_opacity=0)
    return PA_RACK.quad(pts, GHOST, sw=0)


def pa_aicr_label(iso=PA_RACK):
    return T("AICR", 44).move_to([iso.ox + 0.25, iso.oy - 0.66, 0])


class B10_SixIntoOne(Scene):
    def construct(self):
        self.add(pa_title("I · What AICR Is"))
        until(self, "AICR stands")
        pad = pa10_pad()
        self.play(GrowFromCenter(pad), run_time=0.5)
        self.add(pa_aicr_label())
        until(self, "Six universities")
        sites = VGroup(*[pa10_campus(k) for k in range(6)])
        self.play(LaggedStart(*[GrowFromCenter(s) for s in sites], lag_ratio=0.3), run_time=1.1)
        until(self, "at the Massachusetts")
        lines = VGroup(*[pa10_line(k) for k in range(6)])
        self.play(LaggedStart(*[Create(l) for l in lines], lag_ratio=0.25), run_time=1.3)
        until(self, "together with")
        self.play(Create(pa10_pad(outline=True)), run_time=0.7)
        until(self, "built one cluster")
        st, li = aicr_rack(PA_RACK)
        self.play(LaggedStart(*[FadeIn(s, shift=UP * 0.3) for s in st], lag_ratio=0.25), run_time=0.75)
        self.play(LaggedStart(*[GrowFromCenter(l) for l in li], lag_ratio=0.2), run_time=0.3)
        until(self, "and they share it", lead=0.1)
        dots = VGroup(*[Dot(pa10_ends(k)[0], radius=0.1, color=TERRA) for k in range(6)])
        self.add(dots)
        self.play(*[d.animate.move_to(pa10_ends(k)[1]) for k, d in enumerate(dots)], run_time=0.65)
        self.play(FadeOut(dots), run_time=0.2)
        done(self)


# ─────────────── B11 · 248 + 152 = 400 GPUs ───────────────
PA11_P, PA11_S, PA11_BOT = 0.28, 0.21, -1.4       # cell pitch, square side, grid bottom; ten squares to a column
PA11_XL, PA11_XR = -6.0, 1.52                     # left edge of each grid (25 columns, then 16)


def pa11_grid(x0, n, fill):
    """n squares, ten to a column, filled from the bottom, column by column from the left. Returns the columns."""
    cols = []
    for c in range((n + 9) // 10):
        k = min(10, n - 10 * c)
        cols.append(VGroup(*[Square(side_length=PA11_S, fill_color=fill, fill_opacity=1, stroke_width=0)
                             .move_to(np.array([x0 + PA11_P * (c + 0.5), PA11_BOT + PA11_P * (r + 0.5), 0.0]))
                             for r in range(k)]))
    return cols


def pa11_counts(n, x):
    """One numeral per column (10, 20, … n); only one is ever visible."""
    return [T(str(min(n, 10 * (c + 1))), 100).move_to([x, 2.02, 0]) for c in range((n + 9) // 10)]


def pa11_fill(self, cols, nums, rt):
    """The squares fill column by column while the counter climbs with them (one play, any frame rate)."""
    n = len(cols)
    for m in cols + nums:
        m.set_opacity(0)
    self.add(*cols, *nums)
    holder = VGroup(*cols, *nums)

    def upd(m, a):
        k = min(n, int(a * n + 0.5))
        for i, c in enumerate(cols):
            c.set_opacity(1.0 if i < k else 0.0)
        for i, t in enumerate(nums):
            t.set_opacity(1.0 if i == k - 1 else 0.0)

    self.play(UpdateFromAlphaFunc(holder, upd), run_time=rt, rate_func=linear)
    upd(holder, 1.0)


class B11_GpuCount(Scene):
    def construct(self):
        xl, xr = PA11_XL + 12.5 * PA11_P, PA11_XR + 8 * PA11_P            # grid centres
        slots = VGroup(*pa11_grid(PA11_XL, 248, BAR3), *pa11_grid(PA11_XR, 152, BAR3))
        self.add(slots)
        until(self, "two kinds")
        lab_l, lab_r = T("B200", 46).move_to([xl, 3.0, 0]), T("RTX PRO 6000", 46).move_to([xr, 3.0, 0])
        self.play(FadeIn(lab_l), FadeIn(lab_r), run_time=0.4)
        until(self, "Two hundred forty-eight")
        nums_l = pa11_counts(248, xl)
        pa11_fill(self, pa11_grid(PA11_XL, 248, BAR1), nums_l, 1.6)
        until(self, "one hundred fifty-two")
        nums_r = pa11_counts(152, xr)
        pa11_fill(self, pa11_grid(PA11_XR, 152, BAR1), nums_r, 1.2)
        until(self, "That's four hundred")
        hero = T("400", 150).move_to([0, -2.5, 0])
        c1, c2 = nums_l[-1].copy(), nums_r[-1].copy()
        self.add(c1, c2)
        self.play(c1.animate.move_to([-0.6, -2.5, 0]).set_opacity(0), c2.animate.move_to([0.6, -2.5, 0]).set_opacity(0),
                  FadeIn(hero, scale=0.7), run_time=0.7)
        self.remove(c1, c2)
        done(self)


# ─────────────── B12 · around the GPUs: storage, software, a CPU-only section ───────────────
PA12_ST = Iso(-4.0, -1.55, 0.7)              # storage block, left of the rack
PA12_CPU = Iso(3.75, -1.55, 0.7)             # CPU-only block, right of the rack


def pa12_storage():
    """A dark storage block with three light drive bays on its front."""
    iso = PA12_ST
    body = iso.box(0, 0, 0, 1.7, 1.4, 1.0, DARK_TOP, DARK_L, DARK_R)
    bays = VGroup(*[iso.quad([(0.22 + 0.5 * k, 0, 0.3), (0.52 + 0.5 * k, 0, 0.3), (0.52 + 0.5 * k, 0, 0.7), (0.22 + 0.5 * k, 0, 0.7)],
                             GHOST, sw=0) for k in range(3)])
    return VGroup(body, bays)


def pa12_cpu():
    """The CPU-only section: two lighter slabs, no GPU lights."""
    return VGroup(*[PA12_CPU.box(0, 0, i * 0.46, 1.4, 1.4, 0.42, BAR3, BAR2, BAR1) for i in range(2)])


def pa12_pages():
    """The software stack: three pages on top of the rack."""
    return VGroup(*[PA_RACK.page(0.5 + 0.07 * k, 0.14 + 0.03 * k, PA_RACK_TOP + 0.1 * k, 1.3, 1.3) for k in range(3)])


def pa12_job():
    return job_box(PA12_CPU, 0.35, 0.35, 0.88)


def pa12_check():
    return check(3.78, 0.42, 0.2, TERRA, 8)


def pa12_labels():
    return (T("storage", 42).move_to([-3.85, -2.2, 0]), T("software", 42).move_to([0.0, 1.75, 0]),
            T("CPU only", 42).move_to([3.85, -2.2, 0]))


class B12_Around(Scene):
    def construct(self):
        st, li = aicr_rack(PA_RACK)
        self.add(st, li)
        l_st, l_sw, l_cpu = pa12_labels()
        until(self, "fast storage")
        pa_slide_in(self, pa12_storage(), RIGHT * 6, 0.7)
        self.add(l_st)
        until(self, "a modern software stack")
        pa_drop(self, pa12_pages(), 0.9, 0.3)
        self.add(l_sw)
        until(self, "and a CPU-only section", lead=0.6)
        pa_slide_in(self, pa12_cpu(), LEFT * 6, 0.7)
        self.add(l_cpu)
        until(self, "for the work")
        pa_drop(self, [pa12_job()], 0.5)
        until(self, "like cleaning")
        self.play(Create(pa12_check()), run_time=0.35)
        done(self)


# ─────────────── B13 · develop on Explorer, run production on AICR ───────────────
PA13_EXP = Iso(-4.9, -1.5, 0.7)              # the Explorer rack, left
PA13_RIDE = 4.65                             # how far the job rides along the belt


def pa13_belt():
    """A pale belt from Explorer to AICR: deep-kraft edges, ghost centre dashes (never ink)."""
    band = Rectangle(width=5.9, height=0.62, fill_color=CARD, fill_opacity=1, stroke_color=PA_KRAFT, stroke_width=3).move_to([-0.8, -1.16, 0])
    dashes = DashedLine([-3.5, -1.16, 0], [1.9, -1.16, 0], color=GHOST, stroke_width=4, dash_length=0.18)
    return VGroup(band, dashes)


def pa13_job():
    return job_box(Iso(-3.1, -1.42, 0.7))


def pa13_guests():
    """Three more jobs, from the other partners, on top of the shared rack."""
    return [job_box(PA_RACK_R, x, 0.5, PA_RACK_TOP, s=0.55) for x in (1.75, 0.95, 0.15)]


class B13_ExplorerToAicr(Scene):
    def construct(self):
        st, li = aicr_rack(PA_RACK)
        around = VGroup(pa12_storage(), pa12_pages(), pa12_cpu(), pa12_job(), pa12_check(), *pa12_labels())
        self.add(st, li, around)
        self.play(FadeOut(around), VGroup(st, li).animate.shift(RIGHT * 3.6), run_time=0.7)
        until(self, "its own cluster")
        est, eli = explorer_rack(PA13_EXP)
        exp = VGroup(est, eli)
        pa_slide_in(self, exp, RIGHT * 5, 0.7)
        until(self, "called Explorer")
        self.play(FadeIn(T("Explorer", 44).move_to([-4.85, -2.15, 0])), run_time=0.3)
        until(self, "Treat AICR")
        belt = pa13_belt()
        self.play(GrowFromEdge(belt, LEFT), FadeIn(pa_aicr_label(PA_RACK_R)), run_time=0.8)
        until(self, "You develop")
        job = pa13_job()
        pa_drop(self, [job], 0.5)
        until(self, "test on Explorer")
        ck = check(-3.05, -0.12, 0.2, TERRA, 8)
        self.play(Create(ck), run_time=0.35)
        until(self, "you bring it")
        self.play(VGroup(job, ck).animate.shift(RIGHT * PA13_RIDE), run_time=1.1)
        until(self, "for the production run")
        self.play(LaggedStart(*[l.animate.set_color(TERRA) for l in li], lag_ratio=0.25), run_time=0.6)
        until(self, "AICR is shared")
        pa_drop(self, pa13_guests(), 0.9, 0.3, dist=4.0)
        until(self, "so it isn")
        self.play(Indicate(exp, color=None, scale_factor=1.08), run_time=0.7)
        done(self)


# ─────────────── B20 · a proposal opens the gate to a project ───────────────
PA20 = Iso(0.6, -0.9, 0.72)                  # one diagonal: people and page lower-left, gate centre, project upper-right
PA20_PIVOT = PA20.p(0.11, 2.0, 0.9)          # the boom turns on the far post
PA20_LANE = 1.55                             # the y the users walk along (the page keeps to y < 1.1)


def pa20_token(x):
    """A user token standing on the floor at (x, PA20_LANE)."""
    b = PA20.p(x, PA20_LANE, 0)
    body = Polygon(b + np.array([-0.2, 0, 0]), b + np.array([0.2, 0, 0]), b + np.array([0.1, 0.5, 0]), b + np.array([-0.1, 0.5, 0]),
                   fill_color=BAR1, fill_opacity=1, stroke_color=INK, stroke_width=4)
    head = Circle(radius=0.18, fill_color=BAR1, fill_opacity=1, stroke_color=INK, stroke_width=4).move_to(b + np.array([0, 0.66, 0]))
    return VGroup(body, head).set_z_index(7)


def pa20_posts():
    far = PA20.box(0, 2.0, 0, 0.22, 0.22, 1.0, DARK_TOP, DARK_L, DARK_R)
    near = PA20.box(0, -0.2, 0, 0.22, 0.22, 1.0, DARK_TOP, DARK_L, DARK_R).set_z_index(6)
    return far, near


def pa20_boom():
    return Line(PA20_PIVOT, PA20.p(0.11, -0.09, 0.9), color=DARK_L, stroke_width=14).set_z_index(5)


class B20_Proposal(Scene):
    def construct(self):
        self.add(pa_title("II · Getting On"))
        far, near = pa20_posts()
        boom = pa20_boom()
        ta, tb = pa20_token(-5.4), pa20_token(-6.3)
        self.add(far, boom, near, ta, tb)
        until(self, "a faculty member")
        self.play(ta.animate.shift(UP * 0.3), run_time=0.45, rate_func=there_and_back)
        until(self, "The principal investigator")
        page = PA20.page(-4.8, 0.1, 0, 1.1, 1.0)
        self.play(FadeIn(page, shift=DOWN * 0.4), run_time=0.4)
        until(self, "submits a brief proposal", lead=0.55)
        self.play(page.animate.shift(PA20.v(3.5, 0)), run_time=0.65)
        self.add(T("proposal", 42).move_to([0.25, -1.95, 0]))
        until(self, "through a request form")
        self.play(Rotate(boom, angle=2 * PI / 3, about_point=PA20_PIVOT), run_time=0.6)
        until(self, "Access comes")
        cab = project_cabinet(PA20, 3.4, 0.15, 0)
        self.play(FadeIn(cab, shift=UP * 0.3), run_time=0.45)
        self.add(T("project", 42).move_to([4.6, 1.3, 0]))
        self.play(VGroup(ta, tb).animate.shift(PA20.v(8.3, 0)), run_time=1.1)
        done(self)


# ─────────────── B22 · j.smith on Explorer is j_smith_neu on AICR ───────────────
PA22_XE, PA22_XA, PA22_Y, PA22_SZ = -3.9, 3.2, -0.75, 54         # column centres, username row, mono size
PA22_E, PA22_A = Iso(PA22_XE, 1.0, 0.55), Iso(PA22_XA - 0.2, 1.0, 0.55)    # the two racks, small, over their columns


def pa22_rows():
    """Other accounts on the shared cluster: three grey rows under where yours will land."""
    return VGroup(*[pill(0.8 + w / 2, PA22_Y - 0.95 - 0.62 * k, w, 0.34, fill) for k, (w, fill) in
                    enumerate(((4.3, BAR2), (3.4, BAR3), (4.8, BAR2)))])


def pa22_match(text, ref):
    """Mono text whose first glyph sits exactly on `ref` (a glyph of the full AICR username)."""
    t = M(text, PA22_SZ)
    return t.shift(np.array(ref.get_center()) - np.array(t[0].get_center()))


class B22_Username(Scene):
    def construct(self):
        est, eli = explorer_rack(PA22_E)
        ast_, ali = aicr_rack(PA22_A)
        self.add(est, eli, ast_, ali, T("Explorer", 44).move_to([PA22_XE, 0.42, 0]), T("AICR", 44).move_to([PA22_XA, 0.42, 0]))
        until(self, "your username")
        old = M("j.smith", PA22_SZ).move_to([PA22_XE, PA22_Y, 0])
        self.play(FadeIn(old, shift=UP * 0.2), run_time=0.4)
        until(self, "On the cluster")
        arrow = Arrow([-1.95, PA22_Y, 0], [0.3, PA22_Y, 0], color=INK, stroke_width=6, buff=0)
        self.play(GrowArrow(arrow), run_time=0.7)
        until(self, "so accounts")
        rows = pa22_rows()
        self.play(LaggedStart(*[GrowFromEdge(r, LEFT) for r in rows], lag_ratio=0.3), run_time=0.9)
        until(self, "j dot smith")
        self.play(Indicate(old, color=None, scale_factor=1.15), run_time=0.6)
        until(self, "you're j underscore", lead=0.5)
        new = M("j_smith_neu", PA22_SZ).move_to([PA22_XA, PA22_Y, 0])           # the finished AICR username (not shown yet)
        cp = old.copy()
        a = np.array(cp.get_center())
        b = a + np.array(new[0].get_center()) - np.array(old[0].get_center())
        self.add(cp)
        self.play(MoveAlongPath(cp, ArcBetweenPoints(a, b, angle=-PI / 4)), run_time=0.7)
        mid = pa22_match("j_smith", new[0])
        self.play(FadeOut(cp[1], shift=DOWN * 0.15), FadeIn(new[1], shift=DOWN * 0.15), run_time=0.35)
        self.remove(cp, *cp, new[1]); self.add(mid)                               # dot gone, underscore in: one clean word (FadeOut of one glyph leaves the rest loose)
        until(self, "smith underscore")
        tail = VGroup(*new[7:11])
        self.play(FadeIn(tail, shift=LEFT * 0.9), run_time=0.5)
        self.remove(mid, tail, *tail); self.add(new)
        until(self, "on AICR")
        self.play(Indicate(new, color=None, scale_factor=1.08), run_time=0.5)
        done(self)


# ═════════════════════════════ PART B · Act III (where files live) + Act IV (compute) ═════════════════════════════
# Act III stage, shared by B30, B31, B32: three containers in one row, each on a thin dark plinth
# (kraft and white on cream alone measure under Gate V's 0.30 contrast floor; the plinths carry it).
#   home_box (left) · scratch_bin (centre) · project_cabinet (right). Names in serif under each; real paths in mono.
PB_S, PB_Y = 1.05, -1.65
PB_HOME = Iso(-4.65, PB_Y, PB_S)
PB_BIN = Iso(-1.15, PB_Y, PB_S)
PB_CAB = Iso(3.5, PB_Y, PB_S)
PB_PAD = "#E3DFD4"                                  # pale slot pad (B41): within 28 of the stage, so Gate V does not count it as ink
PB_KRAFT = "#917A55"                                # dark kraft outline for small dials (GATE T: small ink rings fuse)
PB_NAME_Y, PB_PATH_Y = PB_Y - 0.72, PB_Y - 1.3
PB_DIAL_HOME = np.array([-5.0, 2.15, 0.0])
PB_DIAL_CAB = np.array([3.3, 2.5, 0.0])


def pb_pad(iso, w, d, m=0.15, h=0.1):
    """A thin dark plinth under a container: its top is the floor (z = 0)."""
    return iso.box(-m, -m, -h, w + 2 * m, d + 2 * m, h, DARK_TOP, DARK_L, DARK_R).set_z_index(-1)


def pb_pads():
    return VGroup(pb_pad(PB_HOME, 1.2, 1.2), pb_pad(PB_BIN, 2.8, 1.8), pb_pad(PB_CAB, 1.3, 1.1))


def pb_home():
    return home_box(PB_HOME).set_z_index(1)


def pb_bin():
    back, front = scratch_bin(PB_BIN)
    return back, front


def pb_cab():
    return project_cabinet(PB_CAB).set_z_index(1)


def pb_names():
    return VGroup(T("home", 40).move_to([-4.65, PB_NAME_Y, 0]), T("scratch", 40).move_to([-0.8, PB_NAME_Y, 0]),
                  T("project", 40).move_to([3.6, PB_NAME_Y - 0.05, 0]))


def pb_paths():
    return VGroup(M("/home/$USER", 32).move_to([-4.7, PB_PATH_Y, 0]), M("/scratch/$USER", 32).move_to([-0.85, PB_PATH_Y, 0]),
                  M("/work/neu/$PROJECT", 32).move_to([3.85, PB_PATH_Y, 0]))


def pb_home_size():
    return T("100 GB", 50).move_to([-4.65, PB_PATH_Y + 0.03, 0])


def pb_stage(self):
    """Put the Act III row on stage (the end of B30, minus title and paths). Returns the parts."""
    pads, home, cab, names = pb_pads(), pb_home(), pb_cab(), pb_names()
    bk, fr = pb_bin()
    self.add(pads, home, bk, fr, cab, names)
    return pads, home, bk, fr, cab, names


def pb_land(self, mob, rt=0.55, dist=1.2):
    """A container lands: a short drop onto its pad."""
    self.play(FadeIn(mob, shift=DOWN * dist), run_time=rt)


def pb_dial(c):
    """A seven-day dial: white face, dark-kraft ring, seven grey day marks."""
    ring = Circle(radius=0.62, stroke_color=PB_KRAFT, stroke_width=5, fill_color=PAGE_TOP, fill_opacity=1).move_to(c)
    days = VGroup(*[Dot(c + 0.4 * np.array([np.sin(TAU * k / 7), np.cos(TAU * k / 7), 0.0]), radius=0.05, color=BAR1) for k in range(7)])
    return VGroup(ring, days).set_z_index(3)


def pb_sweep(c):
    """(arc, end dot): the ink sweep through all seven days, and its terracotta end dot."""
    arc = Arc(radius=0.4, start_angle=PI / 2, angle=-TAU * 6 / 7, arc_center=c, color=INK, stroke_width=7).set_z_index(4)
    end = Dot(c + 0.4 * np.array([np.sin(TAU * 6 / 7), np.cos(TAU * 6 / 7), 0.0]), radius=0.085, color=TERRA).set_z_index(5)
    return arc, end


def pb_days(c):
    return T("7 days", 40).move_to([c[0] + 1.6, c[1], 0])


def pb_page():
    """The file page, lying on top of the home box."""
    return PB_HOME.page(0.2, 0.1, 0.9, w=0.8, d=1.0).set_z_index(4)


# ─────────────── B30 · three places: home, scratch, project ───────────────
class B30_ThreePlaces(Scene):
    def construct(self):
        ttl = T("III · Where Files Live", 40)
        ttl.move_to([-6.0 + ttl.width / 2, 3.0, 0])
        self.add(ttl)
        pads = pb_pads()
        until(self, "three places")
        self.play(LaggedStart(*[FadeIn(p) for p in pads], lag_ratio=0.3), run_time=0.8)
        names, paths = pb_names(), pb_paths()
        until(self, "Home, for")
        pb_land(self, pb_home())
        self.play(FadeIn(names[0]), FadeIn(paths[0]), run_time=0.35)
        until(self, "Scratch, for")
        bk, fr = pb_bin()
        pb_land(self, VGroup(bk, fr))
        self.play(FadeIn(names[1]), FadeIn(paths[1]), run_time=0.35)
        until(self, "And the project directory")
        pb_land(self, pb_cab())
        self.play(FadeIn(names[2]), FadeIn(paths[2]), run_time=0.35)
        done(self)


# ─────────────── B31 · home: 100 GB, and seven days to get a deleted file back ───────────────
class B31_SevenDays(Scene):
    def construct(self):
        pads, home, bk, fr, cab, names = pb_stage(self)
        paths = pb_paths()
        self.add(paths)
        self.play(FadeOut(paths), run_time=0.35)
        self.play(FadeIn(pb_home_size(), shift=UP * 0.2), run_time=0.35)
        until(self, "Delete a file")
        pg = pb_page().shift(UP * 0.8)
        self.play(FadeIn(pg, shift=UP * 0.8), run_time=0.6)             # the page lifts out of the box
        self.play(FadeOut(pg, shift=UP * 0.25), run_time=0.4)           # and it is gone
        until(self, "and you have", lead=0.3)
        dial = pb_dial(PB_DIAL_HOME)
        self.play(GrowFromCenter(dial), FadeIn(pb_days(PB_DIAL_HOME)), run_time=0.4)
        arc, end = pb_sweep(PB_DIAL_HOME)
        self.play(Create(arc), run_time=0.5)                            # seven days sweep by
        self.add(end)
        back = pb_page()
        self.play(FadeIn(back, shift=DOWN * 0.8), run_time=0.6)         # the page comes back
        until(self, "same seven-day", lead=0.5)
        dial2 = pb_dial(PB_DIAL_CAB)
        self.play(GrowFromCenter(dial2), FadeIn(pb_days(PB_DIAL_CAB)), run_time=0.4)
        arc2, end2 = pb_sweep(PB_DIAL_CAB)
        self.play(Create(arc2), run_time=0.5)
        self.add(end2)
        done(self)


def b31_extras():
    """What B31 leaves on stage beyond the row: the returned page, both dials, both '7 days' labels."""
    g = VGroup(pb_page())
    for c in (PB_DIAL_HOME, PB_DIAL_CAB):
        arc, end = pb_sweep(c)
        g.add(pb_dial(c), arc, end, pb_days(c))
    return g


# ─────────────── B32 · scratch: 10 TB, no recovery, purged at thirty days ───────────────
B32_W, B32_D, B32_H = 0.5, 0.6, 0.42
B32_LOW = [(i, j, 0) for j in (1, 0) for i in range(4)]
B32_TOP = [(0, 1, 1), (2, 1, 1), (3, 1, 1), (0, 0, 1), (3, 0, 1), (2, 0, 1)]
B32_MARK = (1, 0, 1)                                                 # the important one, top layer, front row
B32_LOST = (1, 1, 1)                                                 # the one that is deleted and never comes back


def b32_block(i, j, lvl, mark=False, iso=PB_BIN, xy=None):
    x, y = xy if xy else (0.2 + 0.65 * i, 0.2 + 0.8 * j)
    z = lvl * B32_H
    g = VGroup(iso.box(x, y, z, B32_W, B32_D, B32_H, sw=3))
    if mark:
        g.add(Dot(iso.p(x + B32_W / 2, y + B32_D / 2, z + B32_H), radius=0.1, color=TERRA))
    return g.set_z_index(1 + 0.25 * lvl + 0.02 * (8 - (x + y)))


def b32_drop(self, mobs, rt=0.8, lag=0.12, dist=5.0):
    rt = guard(self, rt)
    mobs = list(mobs)
    for m in mobs:
        m.shift(UP * dist)
        self.add(m)
    self.play(LaggedStart(*[m.animate.shift(DOWN * dist) for m in mobs], lag_ratio=lag), run_time=rt, rate_func=ease_in)


class B32_ScratchPurge(Scene):
    def construct(self):
        pads, home, bk, fr, cab, names = pb_stage(self)
        gb = pb_home_size()
        ex = b31_extras()
        self.add(gb, ex)
        self.play(FadeOut(ex), run_time=0.35)
        low = [b32_block(*s) for s in B32_LOW]
        b32_drop(self, low, 0.8, 0.1)                                   # "Scratch is huge"
        self.play(FadeIn(T("10 TB", 50).move_to([-0.8, PB_PATH_Y + 0.03, 0]), shift=UP * 0.2), run_time=0.35)
        until(self, "fifteen million")
        mk = b32_block(*B32_MARK, mark=True)
        lost = b32_block(*B32_LOST)
        top = [b32_block(*s) for s in B32_TOP]
        b32_drop(self, top[:3] + [lost, mk] + top[3:], 1.0, 0.1)
        until(self, "But nothing in scratch")
        self.play(lost.animate.shift(UP * 0.7), run_time=0.3)           # a block is deleted ...
        self.play(FadeOut(lost, shift=UP * 0.25), run_time=0.25)
        nodial = DashedVMobject(Circle(radius=0.5, stroke_color=BAR1, stroke_width=5), num_dashes=14).move_to([-0.3, 2.55, 0])
        self.play(GrowFromCenter(nodial), run_time=0.3)                 # ... and no dial comes for it
        self.play(FadeOut(nodial), run_time=0.3)
        until(self, "thirty-day", lead=0.5)
        line = Line(PB_BIN.p(-0.25, -0.2, 0.95), PB_BIN.p(-0.25, 2.0, 0.95), color=TERRA, stroke_width=7).set_z_index(6)
        self.play(Create(line), FadeIn(T("30 days", 40).move_to([-2.3, 1.85, 0])), run_time=0.4)
        self.play(line.animate.shift(PB_BIN.v(0.3, 0, 0)), run_time=0.5)   # the purge line starts across
        until(self, "So move anything important", lead=0.1)
        tgt = b32_block(0, 0, 0, mark=True, iso=PB_CAB, xy=(0.4, 0.25)).shift(PB_CAB.v(0, 0, 2.0))
        mk.set_z_index(8)
        a, b = np.array(mk.get_center()), np.array(tgt.get_center())
        self.play(MoveAlongPath(mk, ArcBetweenPoints(a, b, angle=-PI / 3)), run_time=0.85)   # lifted out to the cabinet
        rest = sorted(low + top, key=lambda m: np.array(m.get_center())[0] + 0.0)
        self.play(line.animate.shift(PB_BIN.v(2.95, 0, 0)), LaggedStart(*[FadeOut(m) for m in rest], lag_ratio=0.07), run_time=0.9)
        self.play(FadeOut(line), run_time=0.3)
        done(self)


# ─────────────── B40 · the partition table ───────────────
B40_ROWS = [("cpu", "none", "24 h"), ("b200-batch", "B200", "24 h"), ("b200-devel", "B200", "4 h"),
            ("rtx-batch", "RTX PRO 6000", "24 h"), ("rtx-devel", "RTX PRO 6000", "4 h")]
B40_X = (-5.45, -1.1, 2.9)                                           # left edge of each column
B40_Y0, B40_DY = 1.3, 0.8                                            # first row centre, row pitch
B40_L, B40_R = -6.0, 6.0


def b40_at(mob, col, y):
    return mob.move_to([B40_X[col] + mob.width / 2, y, 0])


def b40_cell(fn, s, size, col, y):
    """A table cell set on a common baseline: the string is typeset with a trailing 'bp' (one ascender, one
    descender) so every cell has the same vertical extent, then the two extra glyphs are dropped."""
    try:
        full = b40_at(fn(s + "bp", size), col, y)
        g = VGroup(*list(full)[:len(s.replace(" ", ""))])
        if len(g) == 0:
            raise ValueError
        return g
    except Exception:                                                # Gate A's stub has no glyphs: plain centre placement
        return b40_at(fn(s, size), col, y)


def b40_row(k):
    name, gpu, wall = B40_ROWS[k]
    y = B40_Y0 - k * B40_DY
    return VGroup(b40_cell(M, name, 36, 0, y), b40_cell(T, gpu, 40, 1, y), b40_cell(T, wall, 40, 2, y))


def b40_rule(k, color=BAR1, sw=3):
    """The rule under row k (k = -1 is the heavy rule under the header)."""
    y = B40_Y0 - k * B40_DY - B40_DY / 2
    return Line([B40_L, y, 0], [B40_R, y, 0], color=color, stroke_width=sw)


class B40_PartitionTable(Scene):
    def construct(self):
        ttl = T("IV · Compute", 40)
        ttl.move_to([-6.0 + ttl.width / 2, 3.0, 0])
        self.add(ttl)
        hy = B40_Y0 + B40_DY + 0.05
        hb = lambda t, size: T(t, size, bold=True)
        head = VGroup(*[b40_cell(hb, t, 38, k, hy) for k, t in enumerate(("Partition", "GPU", "Max walltime"))])
        rules = [b40_rule(-1, INK, 5)] + [b40_rule(k) for k in range(4)] + [b40_rule(4, INK, 5)]
        until(self, "split into partitions", lead=0.9)
        self.play(FadeIn(head), run_time=0.4)
        self.play(LaggedStart(*[Create(r) for r in rules], lag_ratio=0.25), run_time=1.1)   # the frame splits into rows
        until(self, "One is CPU only")
        self.play(FadeIn(b40_row(0), shift=RIGHT * 0.3), run_time=0.45)
        until(self, "a batch and a devel partition for the B200s")
        self.play(FadeIn(b40_row(1), shift=RIGHT * 0.3), run_time=0.45)
        until(self, "a devel partition for the B200s")
        self.play(FadeIn(b40_row(2), shift=RIGHT * 0.3), run_time=0.45)
        until(self, "and a batch and a devel partition for the RTX cards")
        self.play(FadeIn(b40_row(3), shift=RIGHT * 0.3), run_time=0.45)
        until(self, "a devel partition for the RTX cards")
        self.play(FadeIn(b40_row(4), shift=RIGHT * 0.3), run_time=0.45)
        until(self, "Every GPU node")
        dots = [Dot([-5.75, B40_Y0 - k * B40_DY, 0], radius=0.09, color=TERRA) for k in range(1, 5)]
        self.play(LaggedStart(*[GrowFromCenter(d) for d in dots], lag_ratio=0.2), run_time=0.6)   # the four GPU partitions
        until(self, "two point three terabytes")
        cap = T("2.3 TB memory per GPU node", 40).move_to([0.2, -2.85, 0])
        key = Dot([-3.4, -2.85, 0], radius=0.09, color=TERRA)                  # fixed x: Gate A's stub measures text widths differently
        self.play(FadeIn(cap, shift=UP * 0.2), GrowFromCenter(key), run_time=0.45)
        done(self)


# ─────────────── B41 · batch runs 24 h, devel 4 h and four running jobs ───────────────
B41_X0, B41_UNIT = -4.4, 9.0 / 24                                    # bar start, screen units per hour
B41_YB, B41_YD = 2.3, -0.3                                           # batch bar centre, devel bar centre
B41_SLOT_Y = -2.85
B41_SLOT_X = (-1.6, 0.1, 1.8, 3.5)


def b41_bar(hours, y, fill):
    w = hours * B41_UNIT
    return Rectangle(width=w, height=0.7, fill_color=fill, fill_opacity=1, stroke_width=0).move_to([B41_X0 + w / 2, y, 0])


def b41_slot(x):
    return Iso(x, B41_SLOT_Y, 1.0).quad([(-0.1, -0.1, 0), (0.8, -0.1, 0), (0.8, 0.8, 0), (-0.1, 0.8, 0)], PB_PAD, stroke=BAR1, sw=3).set_z_index(-1)


def b41_job(x):
    return job_box(Iso(x, B41_SLOT_Y, 1.0)).set_z_index(2)


class B41_BatchVsDevel(Scene):
    def construct(self):
        # the chart's skeleton is up from the first frame: two row labels and devel's four empty job slots
        self.add(T("batch", 42).move_to([-5.3, B41_YB, 0]), T("devel", 42).move_to([-5.3, B41_YD, 0]))
        self.add(VGroup(*[b41_slot(x) for x in B41_SLOT_X]))
        until(self, "submit")
        self.play(FadeIn(job_box(Iso(-5.3, 0.8, 0.8)), shift=DOWN * 0.6), run_time=0.5)          # a job, submitted
        until(self, "They run up to", lead=0.1)
        bar = b41_bar(24, B41_YB, BAR1)
        self.play(GrowFromEdge(bar, LEFT), run_time=1.3)                # grows to 24 h
        self.play(FadeIn(T("24 h", 48).move_to([5.42, B41_YB, 0])), run_time=0.3)
        until(self, "and they support")
        gpus = [gpu_block(Iso(x, 0.6, 0.7)) for x in (2.6, 4.2)]
        self.play(*[FadeIn(VGroup(body, light), shift=DOWN * 0.5) for body, light in gpus], run_time=0.45)
        self.play(*[light.animate.set_color(TERRA) for body, light in gpus], run_time=0.3)        # more than one GPU, busy
        until(self, "four hours at most")
        bar2 = b41_bar(4, B41_YD, BAR2)
        self.play(GrowFromEdge(bar2, LEFT), run_time=0.5)               # stops at 4 h
        self.play(FadeIn(T("4 h", 48).move_to([B41_X0 + 4 * B41_UNIT + 0.7, B41_YD, 0])), run_time=0.3)
        until(self, "and four running jobs", lead=0.35)
        jobs = [b41_job(x) for x in B41_SLOT_X]
        self.play(LaggedStart(*[FadeIn(j, shift=DOWN * 0.9) for j in jobs], lag_ratio=0.25),
                  FadeIn(T("4 running jobs", 40).move_to([-4.3, -2.15, 0])), run_time=0.9)
        fifth = b41_job(4.75).shift(RIGHT * 3.2)
        self.add(fifth)
        self.play(fifth.animate.shift(LEFT * 3.2), run_time=0.4, rate_func=ease_in)               # a fifth arrives ...
        self.play(fifth.animate.shift(RIGHT * 0.55), run_time=0.3, rate_func=rate_functions.ease_out_bounce)   # ... and bounces off
        done(self)
# ═════════════════════════════ PART C · B42 B43 B55 B61 B62 ═════════════════════════════
PC_KRAFT = "#9C8462"      # deep kraft: cables and connectors (ink cables fuse the things they join, GATE T)
PC_SMALL = "#917A55"      # dark kraft: outlines of SMALL objects only
PC_BELT = "#E4E0D4"       # belts and pads stay within 28 of the stage (Gate V)
PC_CHIP = "#ECE6DC"


def pc_belt(x0, x1, y, dx=0.3, h=0.3, th=0.2):
    """A flat belt running left-right: front strip, top, pale centre dashes."""
    front = Polygon([x0, y - th, 0], [x1, y - th, 0], [x1, y, 0], [x0, y, 0],
                    fill_color=BOX_R, fill_opacity=1, stroke_color=PC_SMALL, stroke_width=3)
    top = Polygon([x0, y, 0], [x1, y, 0], [x1 + dx, y + h, 0], [x0 + dx, y + h, 0],
                  fill_color=PC_BELT, fill_opacity=1, stroke_color=PC_SMALL, stroke_width=3)
    mid = DashedLine([x0 + 0.45, y + h / 2, 0], [x1 - 0.15, y + h / 2, 0], color=GHOST, stroke_width=3, dash_length=0.14)
    return VGroup(front, top, mid).set_z_index(-1)


# ─────────────── B42 · four GPUs asked for, one used: the other three sit idle ───────────────
B42_X = (-3.9, -1.3, 1.3, 3.9)


def b42_cable(x):
    """Job box down to a bus, along it, down to just above a GPU block (never touching the dark block)."""
    c = VMobject(color=PC_KRAFT, stroke_width=6)
    c.set_points_as_corners([np.array([0.0, 1.62, 0]), np.array([0.0, 1.3, 0]), np.array([x, 1.3, 0]), np.array([x, 0.92, 0])])
    return c


def b42_meter(x):
    return Rectangle(width=1.5, height=0.32, fill_color=CARD, fill_opacity=1, stroke_color=PC_SMALL, stroke_width=3).move_to([x, -1.65, 0])


class B42_IdleCards(Scene):
    def construct(self):
        gpus, lights = VGroup(), VGroup()
        for x in B42_X:
            body, light = gpu_block(Iso(x, -1.05, 1.15))
            light.scale(1.5)
            gpus.add(body); lights.add(light)
        meters = VGroup(*[b42_meter(x) for x in B42_X])
        self.add(gpus, lights, meters)
        job = job_box(Iso(0.0, 1.75, 1.05)).set_z_index(2)
        self.play(FadeIn(job, shift=DOWN * 0.3), run_time=0.5)
        self.add(T("job", 40).move_to([1.35, 2.45, 0]))
        until(self, "more than one GPU")
        cables = VGroup(*[b42_cable(x) for x in B42_X]).set_z_index(1)
        cables[0].set_z_index(2)
        self.play(*[Create(c) for c in cables], run_time=0.8)
        plugs = VGroup(*[Dot([x, 0.9, 0], radius=0.09, color=PC_KRAFT) for x in B42_X]).set_z_index(2)
        self.play(*[GrowFromCenter(p) for p in plugs], run_time=0.3)
        until(self, "use them")
        fill = Rectangle(width=1.36, height=0.18, fill_color=BAR1, fill_opacity=1, stroke_width=0).move_to([-3.9, -1.65, 0])
        self.play(lights[0].animate.set_color(TERRA), GrowFromEdge(fill, LEFT), run_time=0.7)
        until(self, "the extra cards sit idle")
        self.add(T("idle", 44).move_to([1.3, -2.55, 0]))
        rest = VGroup(cables[1], cables[2], cables[3], plugs[1], plugs[2], plugs[3])
        self.play(rest.animate.set_color(BAR3), run_time=0.5)
        done(self)


# ─────────────── B43 · idle is watched: utilization flat, job cancelled, GPU to the next in the queue ───────────────
B43_GPU = Iso(3.7, -0.9, 1.5)
B43_Q1 = np.array([0.3, -2.8, 0.0])
B43_Q2 = np.array([-1.9, -2.8, 0.0])


def b43_axes():
    return VGroup(Line([-5.7, 0.7, 0], [0.9, 0.7, 0], color=BAR1, stroke_width=4),
                  Line([-5.7, 0.7, 0], [-5.7, 2.7, 0], color=BAR1, stroke_width=4))


def b43_glass(x, y):
    return VGroup(Circle(radius=0.4, color=INK, stroke_width=6).move_to([x, y, 0]),
                  Line([x + 0.29, y - 0.29, 0], [x + 0.62, y - 0.62, 0], color=INK, stroke_width=9)).set_z_index(4)


class B43_IdleCancel(Scene):
    def construct(self):
        axes = b43_axes()
        body, light = gpu_block(B43_GPU)
        light.scale(1.7).set_color(TERRA)
        job = job_box(B43_GPU, 0.15, 0.15, 0.5).set_z_index(2)
        q1 = job_box(Iso(0.3, -2.8, 1.5)).set_z_index(2)
        q2 = job_box(Iso(-1.9, -2.8, 1.5)).set_z_index(2)
        self.add(axes, body, light, job, q1, q2,
                 T("GPU utilization", 36).move_to([-3.6, 3.05, 0]), T("queue", 40).move_to([2.05, -2.3, 0]))
        hi = VMobject(color=INK, stroke_width=7)
        hi.set_points_smoothly([np.array(p) for p in ([-5.7, 2.2, 0], [-5.0, 2.36, 0], [-4.3, 2.14, 0], [-3.6, 2.32, 0], [-3.0, 2.2, 0])])
        lo = VMobject(color=INK, stroke_width=7)
        lo.set_points_as_corners([np.array(p) for p in ([-3.0, 2.2, 0], [-2.6, 0.8, 0], [0.7, 0.8, 0])])
        self.play(Create(hi), run_time=1.1)
        self.play(Create(lo), run_time=0.9)
        self.add(T("idle", 40).move_to([-0.9, 1.8, 0]))
        until(self, "tracks GPU utilization")
        glass = b43_glass(-4.6, 2.3)
        self.play(GrowFromCenter(glass), run_time=0.3)
        path = VMobject()
        path.set_points_as_corners([np.array(p) for p in ([-4.49, 2.19, 0], [-2.89, 2.09, 0], [-2.49, 0.69, 0], [-0.79, 0.69, 0])])
        self.play(MoveAlongPath(glass, path), run_time=1.2)
        until(self, "cancels jobs")
        strike = VGroup(Line([3.2, 0.8, 0], [4.2, 1.7, 0], color=INK, stroke_width=9),
                        Line([3.2, 1.7, 0], [4.2, 0.8, 0], color=INK, stroke_width=9)).set_z_index(5)
        self.play(Create(strike), run_time=0.35)
        self.play(FadeOut(job, scale=0.7), FadeOut(strike, scale=0.7), light.animate.set_color(GHOST), run_time=0.5)
        gone = T("cancelled", 40).move_to([3.7, 2.6, 0])
        self.add(gone)
        until(self, "when you're done")
        hop = np.array([3.7, 0.075, 0.0]) - B43_Q1
        self.play(q1.animate.shift(hop), q2.animate.shift(B43_Q1 - B43_Q2), FadeOut(gone), FadeOut(glass), run_time=0.9)
        self.play(light.animate.set_color(TERRA), run_time=0.3)
        until(self, "jobstats")
        self.add(M("jobstats", 34).move_to([-3.6, -0.15, 0]))
        scan = Line([-5.55, 0.55, 0], [-5.55, 2.75, 0], color=TERRA, stroke_width=6).set_z_index(3)
        self.play(Create(scan), run_time=0.25)
        self.play(scan.animate.shift(RIGHT * 6.3), run_time=1.2)
        self.play(FadeOut(scan), run_time=0.25)
        done(self)


# ─────────────── B55 · Open OnDemand: three choices in a browser, the job goes to Slurm, takes a devel slot ───────────────
B55_SLOT_X = (-0.7, 1.2, 3.1, 5.0)
B55_CHIP_Y = (1.8, 1.0, 0.2)


def b55_window():
    win = RoundedRectangle(width=5.6, height=3.5, corner_radius=0.1, fill_color=CARD, fill_opacity=1,
                           stroke_color=GHOST, stroke_width=3).move_to([-3.2, 1.25, 0])
    bar = Rectangle(width=5.6, height=0.5, fill_color=DARK_TOP, fill_opacity=1, stroke_width=0).move_to([-3.2, 2.75, 0])
    dots = VGroup(*[Dot([-5.7 + i * 0.3, 2.75, 0], radius=0.07, color=GHOST) for i in range(3)])
    return VGroup(win, bar, dots)


def b55_slot(x):
    return Iso(x, -2.9, 1.0).quad([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], PC_BELT, stroke=PC_SMALL, sw=3)


class B55_OodToSlurm(Scene):
    def construct(self):
        belt = pc_belt(1.0, 5.6, 1.0)
        slots = VGroup(*[b55_slot(x) for x in B55_SLOT_X]).set_z_index(-1)
        self.add(belt, slots, T("Slurm", 44).move_to([3.3, 2.95, 0]), T("devel", 44).move_to([-2.6, -2.4, 0]))
        until(self, "Open OnDemand")
        win = b55_window()
        self.play(FadeIn(win, shift=UP * 0.3), run_time=0.6)
        until(self, "launches graphical sessions")
        cur = cursor(-1.0, 0.0).set_z_index(6)
        self.play(FadeIn(cur), run_time=0.3)
        self.play(cur.animate.shift(np.array([-1.3, 1.3, 0.0])), run_time=0.7)          # tip now at (-2.3, 1.3)
        tip = [-2.3, 1.3]
        for word, y, cue in (("partition", 1.8, "the partition"), ("time", 1.0, "the time"), ("resources", 0.2, "the resources")):
            until(self, cue)
            chip = pill(-3.9, y, 2.9, 0.62, PC_CHIP)
            dot = Dot([-5.0, y, 0], radius=0.09, color=INK)
            lab = T(word, 36).move_to([-3.75, y, 0])
            step = np.array([-2.75 - tip[0], (y - 0.12) - tip[1], 0.0])
            tip = [-2.75, y - 0.12]
            self.play(FadeIn(chip), FadeIn(dot), FadeIn(lab), cur.animate.shift(step), run_time=0.35)
        until(self, "submits the job")
        job = job_box(Iso(-1.3, 0.3, 1.0)).set_z_index(3)
        self.play(GrowFromCenter(job), FadeOut(cur), run_time=0.35)
        self.play(job.animate.shift(np.array([3.0, 0.8, 0.0])), run_time=0.6)            # onto the belt at (1.7, 1.1)
        self.play(job.animate.shift(np.array([3.3, 0.0, 0.0])), run_time=0.9)            # along it to (5.0, 1.1)
        until(self, "count against")
        self.play(job.animate.shift(np.array([0.0, -3.85, 0.0])), run_time=0.7)          # into the fourth slot
        ring = Circle(radius=0.75, color=TERRA, stroke_width=6).move_to([5.0, -2.2, 0])
        self.play(GrowFromCenter(ring), run_time=0.3)
        self.play(FadeOut(ring, scale=1.4), run_time=0.35)
        done(self)


# ─────────────── B61 · temporary: a year goes round to the annual review gate, renewed, another lap ───────────────
B61_C = np.array([-2.75, -0.45, 0.0])
B61_R = 2.45


def b61_pt(deg, r=B61_R):
    a = deg * PI / 180
    return B61_C + r * np.array([np.cos(a), np.sin(a), 0.0])


def b61_arc(a0, a1):
    return Arc(radius=B61_R, start_angle=a0 * PI / 180, angle=(a1 - a0) * PI / 180, arc_center=B61_C)


def pc_rack_aicr():
    return aicr_rack(Iso(4.4, -1.3, 0.8))


def pc_cabinet(pale=False):
    cab = project_cabinet(Iso(2.0, -1.3, 0.8))
    if pale:
        cab[0].set_fill(STAGE).set_stroke(BAR2)
        cab[1].set_stroke(GHOST)
    return cab


def pc_aicr_label():
    return T("AICR", 40).move_to([4.7, 2.35, 0])


class B61_YearlyReview(Scene):
    def construct(self):
        ring = Circle(radius=B61_R, color=BAR1, stroke_width=4).move_to(B61_C)
        ticks = VGroup(*[Line(b61_pt(15 + 30 * k, B61_R - 0.2), b61_pt(15 + 30 * k, B61_R + 0.2), color=INK, stroke_width=6) for k in range(12)])
        gate = Line([-2.75, 1.55, 0], [-2.75, 2.45, 0], color=INK, stroke_width=11).set_z_index(3)
        hinge = Dot([-2.75, 2.45, 0], radius=0.11, color=INK).set_z_index(3)
        stack, lights = pc_rack_aicr()
        lights.set_color(TERRA)
        cab = pc_cabinet()
        self.add(ring, ticks, gate, hinge, stack, lights, cab, pc_aicr_label(), T("annual review", 40).move_to([-0.5, 2.75, 0]))
        mark = Dot(b61_pt(81), radius=0.17, color=TERRA).set_z_index(4)
        self.play(GrowFromCenter(mark), run_time=0.3)
        self.play(MoveAlongPath(mark, b61_arc(81, -39)), run_time=2.0, rate_func=linear)
        until(self, "project directories")
        self.play(MoveAlongPath(mark, b61_arc(-39, -184)), Transform(cab, pc_cabinet(pale=True)), run_time=2.2, rate_func=linear)
        until(self, "Once a year")
        self.play(MoveAlongPath(mark, b61_arc(-184, -261)), run_time=0.9)
        until(self, "The PI renews")
        ok = check(-4.3, 2.6, 0.26, TERRA, 9)
        self.play(Create(ok), run_time=0.35)
        self.play(Rotate(gate, angle=-95 * PI / 180, about_point=np.array([-2.75, 2.45, 0.0])), Transform(cab, pc_cabinet()), run_time=0.55)
        until(self, "and the project continues")
        self.play(MoveAlongPath(mark, b61_arc(99, -20)), run_time=1.2)
        done(self)


# ─────────────── B62 · the project ends: data rides back to Northeastern, the cabinet empties ───────────────
B62_HOME = Iso(-4.6, -1.3, 0.8)


def b62_block():
    """One block of results, born at the cabinet's front."""
    return Iso(1.55, -1.1, 0.8).box(0, 0, 0, 0.7, 0.6, 0.4, PAGE_TOP, PAGE_L, PAGE_R, sw=3).set_z_index(3)


B62_OUT = np.array([-1.35, 0.25, 0.0])      # cabinet front -> belt's right end
B62_RIDE = np.array([-3.0, 0.0, 0.0])       # along the belt
B62_IN = np.array([-1.5, 0.35, 0.0])        # belt's left end -> into the Northeastern rack


class B62_DataGoesHome(Scene):
    def construct(self):
        stack, lights = pc_rack_aicr()
        lights.set_color(TERRA)
        cab = pc_cabinet()
        home, hl = explorer_rack(B62_HOME)
        belt = pc_belt(-3.3, 0.7, -1.0)
        self.add(belt, stack, lights, cab, home, hl, pc_aicr_label(), T("Northeastern", 40).move_to([-4.5, 1.0, 0]))
        until(self, "the project ends", lead=0.6)
        self.play(lights.animate.set_color(GHOST), run_time=0.5)
        until(self, "the data has to leave")
        b1, b2, b3 = b62_block(), b62_block(), b62_block()
        self.play(FadeIn(b1), run_time=0.25)
        self.play(b1.animate.shift(B62_OUT), run_time=0.8)
        self.add(b2)
        self.play(b1.animate.shift(B62_RIDE), b2.animate.shift(B62_OUT), run_time=1.1)
        self.add(b3)
        self.play(FadeOut(b1, shift=B62_IN, scale=0.5), b2.animate.shift(B62_RIDE), b3.animate.shift(B62_OUT), run_time=1.1)
        self.play(FadeOut(b2, shift=B62_IN, scale=0.5), b3.animate.shift(B62_RIDE), Transform(cab, pc_cabinet(pale=True)), run_time=1.1)
        self.play(FadeOut(b3, shift=B62_IN, scale=0.5), run_time=0.7)
        until(self, "Northeastern resource")
        self.play(hl.animate.set_color(TERRA), run_time=0.4)
        until(self, "at r c help", lead=0.8)
        self.play(FadeIn(M("rchelp@northeastern.edu", 36).move_to([0.0, -2.6, 0]), shift=UP * 0.2), run_time=0.4)
        done(self)


# attach the midpoint guard (see ST); the classes stay literal `(Scene)` for run.sh scene discovery
for _cls in (B10_SixIntoOne, B11_GpuCount, B12_Around, B13_ExplorerToAicr, B20_Proposal, B22_Username, B30_ThreePlaces, B31_SevenDays, B32_ScratchPurge, B40_PartitionTable, B41_BatchVsDevel, B42_IdleCards, B43_IdleCancel, B55_OodToSlurm, B61_YearlyReview, B62_DataGoesHome):
    _cls.play = ST.play
