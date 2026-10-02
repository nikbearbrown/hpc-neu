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
