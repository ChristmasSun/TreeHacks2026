from manim import *
import numpy as np

class BatchVsSGD(Scene):
    def construct(self):
        self.camera.background_color = "#000000"

        # -----------------------------
        # Persistent UI: title + caption (only these + one center element at a time)
        # -----------------------------
        title = Text("Batch GD vs. Stochastic GD", font_size=44, weight=BOLD)
        title.set_color(WHITE).to_edge(UP, buff=0.5)

        caption = Text(" ", font_size=30)
        caption.set_color(GREY_A).to_edge(DOWN, buff=0.5)

        self.play(Write(title), run_time=1.0)
        self.play(Write(caption), run_time=0.4)
        self.wait(1.0)  # total so far: 2.4s

        # -----------------------------
        # Center Element 1: Batch idea (sum over all examples -> one gradient)
        # -----------------------------
        batch_group = VGroup()

        sum_tex = MathTex(
            r"g \;=\; \sum_{i=1}^{M} \nabla_\theta \ell_i(\theta)",
            font_size=54
        ).set_color(WHITE)

        update_tex = MathTex(
            r"\theta \leftarrow \theta - \eta\, g",
            font_size=54
        ).set_color(WHITE)

        batch_group = VGroup(sum_tex, update_tex).arrange(DOWN, buff=0.55).move_to(ORIGIN)

        new_caption = Text("Batch: one step uses every training example.", font_size=30).set_color(GREY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption
        self.play(Write(sum_tex), run_time=1.2)
        self.wait(1.2)  # up to 5.4s

        # Highlight the "adding up contributions" idea with a brief rectangle, then remove it
        rect = SurroundingRectangle(sum_tex, color=YELLOW, buff=0.2)
        self.play(Create(rect), run_time=0.3)
        self.wait(0.8)
        self.play(FadeOut(rect), run_time=0.4)  # keep highlights brief
        self.wait(0.6)  # up to 7.5s

        # Update parameters
        self.play(Write(update_tex), run_time=0.9)
        self.wait(0.7)  # up to 9.1s

        # Small datasets: "works nicely"
        new_caption = Text("Works nicely when M is small.", font_size=30).set_color(GREY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.5)
        caption = new_caption
        self.wait(1.4)  # up to 11.0s

        # Huge datasets: demand becomes heavy
        new_caption = Text("But when M is huge, each step becomes expensive.", font_size=30).set_color(GREY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption
        self.wait(1.6)  # up to 13.2s

        # Transition: Replace center element with "M is ..." scale-up numbers (center element only)
        self.play(FadeOut(batch_group), run_time=0.5)
        self.wait(0.6)  # up to 14.3s

        m_tex = MathTex(r"M \;=\; 1{,}000{,}000", font_size=72).set_color(WHITE).move_to(ORIGIN)
        self.play(Write(m_tex), run_time=0.5)
        self.wait(0.7)  # up to 15.5s

        m_tex2 = MathTex(r"M \;=\; 10{,}000{,}000", font_size=72).set_color(WHITE).move_to(ORIGIN)
        self.play(TransformMatchingTex(m_tex, m_tex2), run_time=0.6)
        m_tex = m_tex2
        self.wait(1.0)  # up to 17.1s

        m_tex3 = MathTex(r"M \;=\; 100{,}000{,}000", font_size=72).set_color(WHITE).move_to(ORIGIN)
        self.play(TransformMatchingTex(m_tex, m_tex3), run_time=0.7)
        m_tex = m_tex3
        self.wait(0.8)  # up to 18.6s

        # Scanning entire database to compute big sum: swap to a "scan -> sum" pictogram (single center element)
        self.play(FadeOut(m_tex), run_time=0.4)
        self.wait(0.2)  # up to 19.2s

        db = RoundedRectangle(width=4.8, height=2.0, corner_radius=0.25, stroke_width=3)
        db.set_stroke(BLUE, opacity=1.0)
        db.set_fill(BLUE_E, opacity=0.15)

        db_label = Text("dataset", font_size=34).set_color(BLUE_B).move_to(db.get_center())

        scan_arrow = Arrow(start=LEFT*3.4, end=LEFT*0.5, buff=0.0, stroke_width=6).set_color(WHITE)
        scan_text = Text("scan", font_size=32).set_color(WHITE).next_to(scan_arrow, UP, buff=0.25)

        sum_small = MathTex(r"\sum_{i=1}^{M}", font_size=64).set_color(YELLOW)

        scan_group = VGroup(scan_arrow, scan_text, db, db_label, sum_small)
        VGroup(scan_arrow, scan_text).move_to(LEFT*3.0)
        VGroup(db, db_label).move_to(ORIGIN)
        sum_small.move_to(RIGHT*3.2)

        scan_group = VGroup(scan_arrow, scan_text, db, db_label, sum_small)

        new_caption = Text("One update: scan the whole dataset to compute one big sum.", font_size=30).set_color(GREY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption

        self.play(Create(scan_arrow), Write(scan_text), run_time=0.8)
        self.play(Create(db), Write(db_label), run_time=0.8)
        self.play(Write(sum_small), run_time=0.8)
        self.wait(1.7)  # up to 24.5s

        # -----------------------------
        # Transition to SGD trade-off
        # -----------------------------
        self.play(FadeOut(scan_group), run_time=0.6)
        self.wait(0.1)  # up to 25.2s

        new_caption = Text("Stochastic GD trades accuracy per step for speed.", font_size=30).set_color(GREY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption
        self.wait(0.9)  # up to 26.7s

        # Center Element: single-example update rule
        sgd_tex = MathTex(
            r"g \;=\; \nabla_\theta \ell_{i}(\theta)",
            font_size=58
        ).set_color(WHITE).move_to(ORIGIN)

        sgd_update = MathTex(
            r"\theta \leftarrow \theta - \eta\, g",
            font_size=58
        ).set_color(WHITE)

        sgd_group = VGroup(sgd_tex, sgd_update).arrange(DOWN, buff=0.55).move_to(ORIGIN)

        self.play(Write(sgd_tex), run_time=0.8)
        self.wait(0.4)  # up to 27.9s

        new_caption = Text("Each step uses just one example.", font_size=30).set_color(GREY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.5)
        caption = new_caption

        self.play(Write(sgd_update), run_time=0.7)
        self.wait(0.5)  # up to 29.6s

        # -----------------------------
        # Switch to contour plot and noisy path
        # (Fade out equations first to respect no-overlap)
        # -----------------------------
        self.play(FadeOut(sgd_group), run_time=0.6)
        self.wait(0.2)  # up to 30.4s

        new_caption = Text("On a contour plot, the path looks noisy.", font_size=30).set_color(GREY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.4)
        caption = new_caption

        # Contour plot as a single center group
        plane = NumberPlane(
            x_range=[-4, 4, 1],
            y_range=[-3, 3, 1],
            x_length=9.5,
            y_length=5.5,
            background_line_style={"stroke_color": GREY_E, "stroke_width": 1, "stroke_opacity": 0.35},
            axis_config={"stroke_color": GREY_D, "stroke_width": 2, "include_ticks": False},
        )

        # Elliptical contour rings centered at (1, -0.5)
        center = np.array([1.0, -0.5, 0.0])
        rings = VGroup()
        for r in [0.6, 1.0, 1.5, 2.1, 2.8]:
            e = Ellipse(width=2.2*r, height=1.2*r)
            e.move_to(center)
            e.set_stroke(color=BLUE_B, width=3, opacity=0.75)
            rings.add(e)

        minimum_dot = Dot(point=center, radius=0.07, color=YELLOW)

        contour_group = VGroup(plane, rings, minimum_dot).move_to(ORIGIN)

        self.play(Create(plane), run_time=0.7)
        self.play(Create(rings), run_time=0.8)
        self.play(FadeIn(minimum_dot, scale=1.2), run_time=0.4)
        self.wait(0.2)  # up to 32.5s

        # Noisy path drifting toward the minimum (all contained in same center group)
        new_caption = Text("But steps are cheap, and the noise still drifts to the minimum.", font_size=30).set_color(GREY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption

        rng = np.random.default_rng(2)
        pts = [np.array([-3.2, 2.3, 0.0])]
        for k in range(10):
            cur = pts[-1]
            to_min = (center - cur)
            step = 0.28 * to_min
            jitter = np.array([0.35, 0.35, 0.0]) * rng.normal(size=3)
            jitter[2] = 0.0
            nxt = cur + step + 0.35 * jitter
            # keep within frame
            nxt[0] = np.clip(nxt[0], -3.8, 3.8)
            nxt[1] = np.clip(nxt[1], -2.8, 2.8)
            pts.append(nxt)

        path = VMobject()
        path.set_points_smoothly(pts)
        path.set_stroke(RED, width=5, opacity=0.9)

        traveler = Dot(point=pts[0], radius=0.08, color=RED)

        contour_group.add(path, traveler)

        self.play(Create(path), FadeIn(traveler), run_time=0.9)
        self.play(MoveAlongPath(traveler, path), run_time=2.2, rate_func=linear)
        self.wait(1.0)  # up to ~36.6s