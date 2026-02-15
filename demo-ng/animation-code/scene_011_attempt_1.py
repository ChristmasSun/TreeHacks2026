from manim import *
import numpy as np

class GradientDescentLearningRate(Scene):
    def construct(self):
        self.camera.background_color = "#000000"

        # ---------- Helpers ----------
        def make_title(text):
            return Text(text, font_size=40, weight=BOLD, color=WHITE).to_edge(UP, buff=0.5)

        def make_caption(text):
            return Text(text, font_size=28, color=GRAY_A).to_edge(DOWN, buff=0.5)

        def line_from_params(axes, m, b, color=YELLOW, stroke_width=6):
            x0, x1 = axes.x_range[0], axes.x_range[1]
            y0, y1 = m * x0 + b, m * x1 + b
            return Line(axes.c2p(x0, y0), axes.c2p(x1, y1), color=color, stroke_width=stroke_width)

        # ---------- Persistent title/caption (only 1 each at a time) ----------
        title = make_title("Gradient Descent: Learning Rate")
        caption = make_caption("")

        self.play(Write(title), run_time=1.2)
        self.play(Write(caption), run_time=0.6)

        # ---------- Beat 1 (0.0s - 9.0s): line updates, step downhill on error surface, lower cost J(θ) ----------
        new_caption = make_caption("Each update takes a step downhill, lowering the cost  J(θ).")
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption

        axes = Axes(
            x_range=(0, 8, 1),
            y_range=(0, 6, 1),
            x_length=10,
            y_length=5.2,
            axis_config={"color": GRAY_B, "stroke_width": 2},
            tips=False,
        )

        # deterministic scatter resembling a linear trend
        xs = np.array([0.8, 1.4, 2.1, 2.8, 3.3, 4.2, 4.9, 5.6, 6.2, 7.1])
        ys = np.array([1.0, 1.6, 2.0, 2.4, 2.9, 3.3, 3.6, 4.0, 4.4, 4.9])
        ys = ys + np.array([0.12, -0.10, 0.15, -0.05, 0.08, -0.12, 0.10, -0.08, 0.06, -0.04])

        dots = VGroup(*[
            Dot(point=axes.c2p(x, y), radius=0.06, color=BLUE_B)
            for x, y in zip(xs, ys)
        ])

        # Center element is a single VGroup to respect the 3-object rule
        main = VGroup(axes, dots)

        self.play(Create(axes), run_time=1.2)
        self.play(LaggedStart(*[FadeIn(d) for d in dots], lag_ratio=0.08), run_time=1.3)

        # "line updates" as iterative replacements (still one center element: main group)
        m0, b0 = 0.25, 0.7
        m_star, b_star = 0.55, 0.75

        line = line_from_params(axes, m0, b0, color=YELLOW)
        main.add(line)
        self.play(Create(line), run_time=0.7)

        # A few distinct updates to suggest iterative descent
        params = [
            (0.35, 0.72),
            (0.45, 0.75),
            (0.52, 0.76),
            (m_star, b_star),
        ]
        for (m, b) in params:
            new_line = line_from_params(axes, m, b, color=YELLOW)
            self.play(ReplacementTransform(line, new_line), run_time=0.65)
            line = new_line

        # Briefly show J(θ) (center element must remain one object -> transform main to equation, then back)
        self.play(FadeOut(main), run_time=0.5)
        j_tex = MathTex(r"J(\theta)", color=WHITE).scale(2.2)
        self.play(Write(j_tex), run_time=0.8)
        self.wait(0.6)

        # Return to the scatter+line
        self.play(FadeOut(j_tex), run_time=0.4)
        # rebuild main (same visual) to keep flow clean
        line = line_from_params(axes, m_star, b_star, color=YELLOW)
        main = VGroup(axes, dots, line)
        self.play(FadeIn(main), run_time=0.7)

        # Pad to reach ~9.0s segment end
        self.wait(0.6)

        # ---------- Beat 2 (9.5s - 12.6s): step size set by alpha ----------
        new_caption = make_caption("Step size is set by  α  (the learning rate).")
        self.play(ReplacementTransform(caption, new_caption), run_time=0.55)
        caption = new_caption

        # Highlight alpha without adding extra center objects: temporarily swap main to a single MathTex
        self.play(FadeOut(main), run_time=0.45)
        alpha_tex = MathTex(r"\alpha", color=YELLOW).scale(2.6)
        self.play(Write(alpha_tex), run_time=0.7)
        self.wait(0.65)

        # Back to plot
        self.play(FadeOut(alpha_tex), run_time=0.35)
        self.play(FadeIn(main), run_time=0.6)
        self.wait(0.35)

        # ---------- Beat 3 (13.0s - 20.6s): alpha too large overshoots/bounces ----------
        new_caption = make_caption("If α is too large, updates can overshoot and bounce.")
        self.play(ReplacementTransform(caption, new_caption), run_time=0.55)
        caption = new_caption

        # Transition from main plot to a single inset panel (one center element)
        self.play(FadeOut(main), run_time=0.6)

        # Inset: 1D cost curve + bouncing steps (alpha too large)
        inset_axes = Axes(
            x_range=(-3, 3, 1),
            y_range=(0, 5, 1),
            x_length=9.5,
            y_length=5.0,
            axis_config={"color": GRAY_B, "stroke_width": 2},
            tips=False,
        )
        parabola = inset_axes.plot(lambda x: 0.5 * (x**2) + 0.4, x_range=[-2.6, 2.6], color=BLUE_C, stroke_width=6)

        min_dot = Dot(inset_axes.c2p(0, 0.4), radius=0.07, color=GREEN_C)

        # Large alpha sequence: alternating sides with decreasing amplitude
        x_seq_large = [2.2, -1.8, 1.4, -1.05, 0.75, -0.5, 0.3]
        step_dots = VGroup(*[
            Dot(inset_axes.c2p(x, 0.5*(x**2)+0.4), radius=0.06, color=YELLOW)
            for x in x_seq_large
        ])

        step_lines = VGroup(*[
            Line(
                inset_axes.c2p(x_seq_large[i], 0.5*(x_seq_large[i]**2)+0.4),
                inset_axes.c2p(x_seq_large[i+1], 0.5*(x_seq_large[i+1]**2)+0.4),
                color=YELLOW,
                stroke_width=4,
            )
            for i in range(len(x_seq_large)-1)
        ])

        inset = VGroup(inset_axes, parabola, min_dot, step_lines, step_dots)

        self.play(Create(inset_axes), run_time=1.0)
        self.play(Create(parabola), run_time=1.0)
        self.play(FadeIn(min_dot), run_time=0.3)

        # Animate the bouncing steps sequentially
        self.play(FadeIn(step_dots[0]), run_time=0.25)
        for i in range(len(step_lines)):
            self.play(Create(step_lines[i]), run_time=0.45)
            self.play(FadeIn(step_dots[i+1]), run_time=0.2)
        self.wait(0.55)

        # ---------- Beat 4 (21.0s - 28.2s): alpha too small creeps slowly ----------
        new_caption = make_caption("If α is too small, progress is smooth but painfully slow.")
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption

        # Replace inset with a "small alpha" version (no overlap: transform whole center group)
        inset2_axes = Axes(
            x_range=(-3, 3, 1),
            y_range=(0, 5, 1),
            x_length=9.5,
            y_length=5.0,
            axis_config={"color": GRAY_B, "stroke_width": 2},
            tips=False,
        )
        parabola2 = inset2_axes.plot(lambda x: 0.5 * (x**2) + 0.4, x_range=[-2.6, 2.6], color=BLUE_C, stroke_width=6)
        min_dot2 = Dot(inset2_axes.c2p(0, 0.4), radius=0.07, color=GREEN_C)

        x_seq_small = [2.2, 1.95, 1.72, 1.50, 1.30, 1.12, 0.96, 0.82, 0.70, 0.60]
        step_dots2 = VGroup(*[
            Dot(inset2_axes.c2p(x, 0.5*(x**2)+0.4), radius=0.055, color=YELLOW)
            for x in x_seq_small
        ])
        step_lines2 = VGroup(*[
            Line(
                inset2_axes.c2p(x_seq_small[i], 0.5*(x_seq_small[i]**2)+0.4),
                inset2_axes.c2p(x_seq_small[i+1], 0.5*(x_seq_small[i+1]**2)+0.4),
                color=YELLOW,
                stroke_width=4,
            )
            for i in range(len(x_seq_small)-1)
        ])

        inset2 = VGroup(inset2_axes, parabola2, min_dot2, step_lines2, step_dots2)

        self.play(ReplacementTransform(inset, inset2), run_time=0.8)

        self.play(FadeIn(step_dots2[0]), run_time=0.2)
        for i in range(len(step_lines2)):
            self.play(Create(step_lines2[i]), run_time=0.35)
            self.play(FadeIn(step_dots2[i+1]), run_time=0.15)
        self.wait(0.4)

        # ---------- Beat 5 (28.2s - 34.1s): test a few learning rates; pick fast + smooth ----------
        new_caption = make_caption("In practice: try a few α’s, pick one that drops J quickly and smoothly.")
        self.play(ReplacementTransform(caption, new_caption), run_time=0.65)
        caption = new_caption

        # Replace with a simple comparison chart: J vs iteration for 3 alphas
        self.play(FadeOut(inset2), run_time=0.5)

        comp_axes = Axes(
            x_range=(0, 10, 2),
            y_range=(0, 5, 1),
            x_length=10.2,
            y_length=5.2,
            axis_config={"color": GRAY_B, "stroke_width": 2},
            tips=False,
        )

        # Curves: too large (oscillatory), too small (slow), good (fast+smooth)
        good_curve = comp_axes.plot(lambda t: 4.6*np.exp(-0.45*t) + 0.4, x_range=[0, 10], color=GREEN_C, stroke_width=6)
        slow_curve = comp_axes.plot(lambda t: 4.6*np.exp(-0.17*t) + 0.4, x_range=[0, 10], color=BLUE_B, stroke_width=6)
        # oscillatory: decaying cosine around a decreasing baseline
        large_curve = comp_axes.plot(
            lambda t: (3.0*np.exp(-0.18*t) + 0.6) + 1.2*np.exp(-0.25*t)*np.cos(2.3*t),
            x_range=[0, 10],
            color=RED_C,
            stroke_width=6
        )

        compare = VGroup(comp_axes, large_curve, slow_curve, good_curve)

        self.play(Create(comp_axes), run_time=0.9)
        self.play(Create(large_curve), run_time=0.75)
        self.play(Create(slow_curve), run_time=0.75)
        self.play(Create(good_curve), run_time=0.75)

        # Emphasize good curve briefly (no extra lingering highlights)
        self.play(Indicate(good_curve, scale_factor=1.03), run_time=0.6)
        self.wait(0.65)

        # End clean
        self.play(FadeOut(compare), run_time=0.6)
        self.play(FadeOut(caption), FadeOut(title), run_time=0.7)