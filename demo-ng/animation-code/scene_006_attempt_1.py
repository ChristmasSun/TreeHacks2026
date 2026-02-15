from manim import *
import numpy as np

class LinearRegressionCost(Scene):
    def construct(self):
        self.camera.background_color = "#000000"

        # ----------------------------
        # Persistent title + caption
        # ----------------------------
        title = Text("Linear Regression: Cost Function", weight=BOLD, color=WHITE).scale(0.75)
        title.to_edge(UP, buff=0.5)

        caption = Text("Goal: choose parameters θ so predictions match the data.", color=GRAY_B).scale(0.55)
        caption.to_edge(DOWN, buff=0.5)

        self.play(Write(title), run_time=1.2)
        self.play(Write(caption), run_time=1.2)
        self.wait(0.6)

        # [0.0 - 7.0] Show idea: choose theta -> best-fitting line on data (scatter + line)
        axes = Axes(
            x_range=[0, 6, 1],
            y_range=[0, 6, 1],
            x_length=8.0,
            y_length=4.6,
            tips=False,
            axis_config={"color": GRAY_A, "stroke_width": 2},
        )
        axes_labels = axes.get_axis_labels(
            x_label=Text("x", color=GRAY_B).scale(0.5),
            y_label=Text("y", color=GRAY_B).scale(0.5),
        )

        # Bundle as single center object (axes + labels + points + line)
        rng_points = [(0.7, 1.0), (1.3, 1.7), (2.0, 2.2), (2.7, 2.9), (3.4, 3.1), (4.2, 4.1), (5.0, 4.7)]
        dots = VGroup(*[
            Dot(axes.c2p(x, y), radius=0.06, color=YELLOW)
            for (x, y) in rng_points
        ])

        # Hypothesis line: y = 0.75x + 0.7
        def h(x):
            return 0.75 * x + 0.7

        line = axes.plot(lambda x: h(x), x_range=[0.3, 5.6], color=BLUE_C, stroke_width=4)

        center_plot = VGroup(axes, axes_labels, dots, line)
        center_plot.move_to(ORIGIN)

        self.play(Create(axes), run_time=1.2)
        self.play(Write(axes_labels), run_time=0.8)
        self.play(LaggedStart(*[Create(d) for d in dots], lag_ratio=0.12), run_time=1.3)
        self.play(Create(line), run_time=1.0)

        cap2 = Text("Pick θ so the line’s predictions land close to the real points.", color=GRAY_B).scale(0.55)
        cap2.to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap2), run_time=0.7)
        caption = cap2

        self.wait(0.8)  # should land near ~7s

        # [7.0 - 16.1] Switch to equation: J(theta) definition
        self.play(FadeOut(center_plot), run_time=0.7)

        cap3 = Text("We measure “closeness” with a cost function.", color=GRAY_B).scale(0.55)
        cap3.to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap3), run_time=0.6)
        caption = cap3

        eq = MathTex(
            r"J(\theta)=\frac{1}{2}\sum_{i=1}^{m}\left(h_{\theta}\!\left(x^{(i)}\right)-y^{(i)}\right)^{2}",
            color=WHITE
        ).scale(0.95)
        eq.set_color_by_gradient(WHITE, WHITE)
        eq.move_to(ORIGIN)

        # Subtle color guidance with safe token matching (no single letters)
        eq_colored = MathTex(
            r"J(\theta)=\frac{1}{2}\sum_{i=1}^{m}\left(h_{\theta}\!\left(x^{(i)}\right)-y^{(i)}\right)^{2}",
            tex_to_color_map={
                r"J(\theta)": GREEN_C,
                r"h_{\theta}": BLUE_C,
                r"y^{(i)}": YELLOW,
                r"\left(\cdot\right)^{2}": WHITE,  # token may not match; harmless if ignored
            }
        ).scale(0.95).move_to(ORIGIN)

        # Write equation in steps: first plain, then transform to colored version
        self.play(Write(eq), run_time=2.0)
        self.wait(0.3)
        self.play(TransformMatchingTex(eq, eq_colored), run_time=1.0)
        eq = eq_colored

        cap4 = Text("J(θ) = ½ · sum over all examples of (prediction − truth)².", color=GRAY_B).scale(0.55)
        cap4.to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap4), run_time=0.7)
        caption = cap4

        self.wait(4.4)  # fill to ~16.1s

        # [16.4 - 21.6] Back to scatter: show vertical gaps
        self.play(FadeOut(eq), run_time=0.6)

        cap5 = Text("On the plot: each point has a vertical gap to the line.", color=GRAY_B).scale(0.55)
        cap5.to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap5), run_time=0.6)
        caption = cap5

        # Recreate plot, but now with residual segments (keep as ONE center object)
        axes2 = axes.copy()
        axes_labels2 = axes_labels.copy()
        dots2 = dots.copy()
        line2 = line.copy()

        # Residual segments for a subset to keep it clean
        pick_indices = [1, 3, 5]  # three residuals
        residuals = VGroup()
        for idx in pick_indices:
            x, y = rng_points[idx]
            yhat = h(x)
            seg = Line(
                axes2.c2p(x, yhat),
                axes2.c2p(x, y),
                color=RED_C,
                stroke_width=5
            )
            residuals.add(seg)

        center_plot2 = VGroup(axes2, axes_labels2, dots2, line2)
        center_plot2.move_to(ORIGIN)

        self.play(Create(axes2), run_time=0.8)
        self.play(Write(axes_labels2), run_time=0.5)
        self.play(LaggedStart(*[Create(d) for d in dots2], lag_ratio=0.10), run_time=0.9)
        self.play(Create(line2), run_time=0.7)
        self.play(LaggedStart(*[Create(r) for r in residuals], lag_ratio=0.18), run_time=1.2)

        center_plot2.add(residuals)

        self.wait(0.9)  # land near ~21.6s

        # [22.1 - 23.4] Name it: residual
        cap6 = Text("That vertical gap is the residual.", color=GRAY_B).scale(0.55)
        cap6.to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap6), run_time=0.5)
        caption = cap6

        # Quick highlight (must disappear soon)
        highlight = SurroundingRectangle(residuals[1], color=WHITE, buff=0.08, stroke_width=3)
        self.play(Create(highlight), run_time=0.4)
        self.wait(0.4)
        self.play(FadeOut(highlight), run_time=0.4)

        self.wait(0.3)

        # [24.0 - 29.9] Squaring: make positive + penalize big misses
        cap7 = Text("Squaring makes errors positive, and big misses count much more.", color=GRAY_B).scale(0.55)
        cap7.to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap7), run_time=0.6)
        caption = cap7

        # Indicate larger residual more strongly
        self.play(residuals[2].animate.set_color(RED_E), run_time=0.4)
        self.play(Indicate(residuals[2], color=RED_E, scale_factor=1.08), run_time=0.8)
        self.play(residuals[0].animate.set_color(RED_C), run_time=0.3)
        self.play(Indicate(residuals[0], color=RED_C, scale_factor=1.04), run_time=0.7)

        self.wait(2.4)  # finish this beat to ~29.9

        # [30.0 - 33.1] Add up squared vertical distances
        cap8 = Text("Add up the squared vertical distances across all points…", color=GRAY_B).scale(0.55)
        cap8.to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap8), run_time=0.6)
        caption = cap8

        self.play(Circumscribe(residuals, color=WHITE, time_width=0.7), run_time=1.1)
        self.wait(1.0)

        # [33.1 - 37.0] Back to J(theta); minimizing = best-fitting line
        self.play(FadeOut(center_plot2), run_time=0.8)

        eq2 = MathTex(
            r"J(\theta)=\frac{1}{2}\sum_{i=1}^{m}\left(h_{\theta}\!\left(x^{(i)}\right)-y^{(i)}\right)^{2}",
            tex_to_color_map={
                r"J(\theta)": GREEN_C,
                r"h_{\theta}": BLUE_C,
                r"y^{(i)}": YELLOW,
            }
        ).scale(0.95).move_to(ORIGIN)

        self.play(Write(eq2), run_time=1.3)

        cap9 = Text("Minimizing J(θ) means finding the best-fitting line.", color=GRAY_B).scale(0.55)
        cap9.to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap9), run_time=0.6)
        caption = cap9

        self.wait(1.2)