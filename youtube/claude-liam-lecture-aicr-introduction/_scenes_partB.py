

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
