from manim import *
import numpy as np

class QuadraticBowlSummedGradient(Scene):
    def construct(self):
        self.camera.background_color = "#000000"

        # ---------- Helpers ----------
        def make_title(text):
            return Text(text, font_size=42, weight=BOLD, color=WHITE).to_edge(UP, buff=0.5)

        def make_caption(text):
            return Text(text, font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)

        # ---------- Persistent top/bottom (counted as 2 objects max) ----------
        title = make_title("Quadratic cost surface (contours)")
        caption = make_caption("A smooth quadratic bowl with elliptical contour lines.")
        self.play(Write(title), run_time=1.0)
        self.play(Write(caption), run_time=0.8)

        # ---------- [0.0s - 6.4s] contours (ellipses) ----------
        # Center element: a single VGroup containing ALL ellipses (so it's one object)
        ellipses = VGroup()
        colors = [BLUE_E, BLUE_D, BLUE_C, BLUE_B, BLUE_A]
        widths = [7.0, 5.8, 4.6, 3.4, 2.2]
        heights = [4.2, 3.5, 2.8, 2.1, 1.4]
        for w, h, c in zip(widths, heights, colors):
            e = Ellipse(width=w, height=h, color=c, stroke_width=3, fill_opacity=0.0)
            ellipses.add(e)
        ellipses.move_to(ORIGIN)

        self.play(LaggedStart(*[Create(e) for e in ellipses], lag_ratio=0.15, run_time=2.4))
        # brief emphasis: "neat ellipses"
        self.play(Circumscribe(ellipses, color=WHITE, time_width=0.6, run_time=1.0))
        self.wait(1.2)  # reaches ~6.4s

        # ---------- [6.7s - 10.7s] cost based on one example ----------
        caption2 = make_caption("First, imagine the cost for a single training example.")
        self.play(ReplacementTransform(caption, caption2), run_time=0.5)
        caption = caption2

        # Center element swap: contours -> single-example equation
        eq_single = MathTex(r"J(\theta) = \ell^{(i)}(\theta)", font_size=64, color=WHITE).move_to(ORIGIN)
        self.play(FadeOut(ellipses), run_time=0.4)
        self.play(Write(eq_single), run_time=1.1)
        self.wait(2.0)  # lands near 10.7s

        # ---------- [11.0s - 13.3s] full sum over m examples ----------
        caption3 = make_caption("But the real cost is the full sum over all m examples.")
        self.play(ReplacementTransform(caption, caption3), run_time=0.5)
        caption = caption3

        eq_sum = MathTex(
            r"J(\theta) = \sum_{i=1}^{m} \ell^{(i)}(\theta)",
            font_size=62,
            color=WHITE
        ).move_to(ORIGIN)
        self.play(TransformMatchingTex(eq_single, eq_sum), run_time=1.1)
        eq_single = eq_sum
        self.wait(0.7)

        # ---------- [13.7s - 19.4s] derivative of a sum is sum of derivatives ----------
        caption4 = make_caption("Key rule: the derivative of a sum is the sum of the derivatives.")
        self.play(ReplacementTransform(caption, caption4), run_time=0.5)
        caption = caption4

        eq_rule = MathTex(
            r"\nabla_\theta \left(\sum_{i=1}^{m} \ell^{(i)}(\theta)\right)"
            r"="
            r"\sum_{i=1}^{m} \nabla_\theta \ell^{(i)}(\theta)",
            font_size=56,
            color=WHITE
        ).move_to(ORIGIN)

        self.play(TransformMatchingTex(eq_single, eq_rule), run_time=1.5)
        eq_single = eq_rule

        # Quick highlight of the "sum" structure, then remove highlight promptly
        rect = SurroundingRectangle(eq_single, color=YELLOW, buff=0.25)
        self.play(Create(rect), run_time=0.5)
        self.play(FadeOut(rect), run_time=0.4)
        self.wait(2.4)  # total segment timing

        # ---------- [19.8s - 23.2s] gradient becomes a big addition ----------
        caption5 = make_caption("So the gradient is a big addition across the dataset.")
        self.play(ReplacementTransform(caption, caption5), run_time=0.5)
        caption = caption5

        eq_grad_sum = MathTex(
            r"\nabla J(\theta) = \sum_{i=1}^{m} \nabla_\theta \ell^{(i)}(\theta)",
            font_size=62,
            color=WHITE
        ).move_to(ORIGIN)
        self.play(TransformMatchingTex(eq_single, eq_grad_sum), run_time=1.2)
        eq_single = eq_grad_sum
        self.wait(1.7)

        # ---------- [23.7s - 27.4s] from i=1 through m add each contribution ----------
        caption6 = make_caption("From i = 1 through m, you add each example’s contribution.")
        self.play(ReplacementTransform(caption, caption6), run_time=0.5)
        caption = caption6

        eq_explicit = MathTex(
            r"\nabla J(\theta) = \nabla \ell^{(1)}(\theta) + \nabla \ell^{(2)}(\theta) + \cdots + \nabla \ell^{(m)}(\theta)",
            font_size=44,
            color=WHITE
        ).move_to(ORIGIN)

        self.play(TransformMatchingTex(eq_single, eq_explicit), run_time=1.4)
        eq_single = eq_explicit
        self.wait(1.8)

        # ---------- [27.4s - 36.2s] follow summed gradient: arrowed path downhill to unique minimum ----------
        caption7 = make_caption("Following that summed gradient steps downhill to one unique minimum.")
        self.play(ReplacementTransform(caption, caption7), run_time=0.5)
        caption = caption7

        # Switch back to contours first (no overlap with equations)
        self.play(FadeOut(eq_single), run_time=0.4)

        # Recreate contours as one center object
        ellipses2 = VGroup()
        for w, h, c in zip(widths, heights, colors):
            e = Ellipse(width=w, height=h, color=c, stroke_width=3, fill_opacity=0.0)
            ellipses2.add(e)
        ellipses2.move_to(ORIGIN)

        self.play(LaggedStart(*[Create(e) for e in ellipses2], lag_ratio=0.12, run_time=1.6))

        # Arrowed descent path as part of the SAME center element (grouped together)
        # Build a polyline approaching the minimum at the center
        pts = [
            np.array([3.2, 1.7, 0]),
            np.array([2.2, 1.0, 0]),
            np.array([1.3, 0.5, 0]),
            np.array([0.7, 0.2, 0]),
            np.array([0.25, 0.05, 0]),
            np.array([0.0, 0.0, 0]),
        ]

        path_group = VGroup()
        for a, b in zip(pts[:-1], pts[1:]):
            seg = Arrow(
                start=a, end=b,
                buff=0.0,
                stroke_width=6,
                max_tip_length_to_length_ratio=0.18,
                color=YELLOW
            )
            path_group.add(seg)

        minimum_dot = Dot(point=ORIGIN, radius=0.08, color=GREEN)

        center_visual = VGroup(ellipses2, path_group, minimum_dot)

        # Animate arrows step-by-step ("stepping downhill")
        self.play(Create(path_group[0]), run_time=0.9)
        self.play(Create(path_group[1]), run_time=0.9)
        self.play(Create(path_group[2]), run_time=0.9)
        self.play(Create(path_group[3]), run_time=0.9)
        self.play(Create(path_group[4]), run_time=0.9)

        # Arrive at unique minimum
        self.play(FadeIn(minimum_dot), run_time=0.35)
        self.play(Indicate(minimum_dot, color=GREEN, scale_factor=1.5), run_time=0.7)
        self.wait(1.95)  # finishes ~36.2s