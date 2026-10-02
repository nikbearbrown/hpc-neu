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
