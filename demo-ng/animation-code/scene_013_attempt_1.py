from manim import *
import numpy as np

class CostCurveLearningRate(Scene):
    def construct(self):
        self.camera.background_color = "#000000"

        # ---------- Persistent layout elements (title + caption) ----------
        title = Text("Training Progress", font_size=44, color=WHITE).to_edge(UP, buff=0.5)
        caption = Text(" ", font_size=28, color=GRAY_A).to_edge(DOWN, buff=0.5)

        self.play(Write(title), run_time=1.0)
        self.play(Write(caption), run_time=0.2)
        self.wait(0.2)

        # ---------- Center element: chart (axes + curve + moving dot) ----------
        axes = Axes(
            x_range=[0, 60, 10],
            y_range=[0, 1.05, 0.25],
            x_length=10.5,
            y_length=5.3,
            tips=False,
            axis_config={"color": GRAY_B, "stroke_width": 2},
        )

        x_label = Text("iterations", font_size=26, color=GRAY_A)
        y_label = MathTex(r"J(\theta)", font_size=38, color=YELLOW)

        x_label.next_to(axes, DOWN, buff=0.45)
        y_label.next_to(axes, LEFT, buff=0.35)

        # Keep labels as part of the one center element by grouping
        chart_group = VGroup(axes, x_label, y_label).move_to(ORIGIN + 0.1 * UP)

        def cost_curve(x):
            # Fast early drop, then flatten
            return 0.12 + 0.88 * np.exp(-x / 12.0)

        curve = axes.plot(cost_curve, x_range=[0, 60], color=BLUE_C, stroke_width=5)
        dot = Dot(radius=0.07, color=YELLOW)

        dot.move_to(axes.c2p(0, cost_curve(0)))
        chart = VGroup(chart_group, curve, dot)

        # 0.0s - 3.3s: "Watch the cost function, J(θ), as training runs."
        cap1 = Text("Watch the cost function J(θ) as training runs.", font_size=28, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap1), run_time=0.4)
        caption = cap1

        self.play(Create(axes), run_time=1.2)
        self.play(Write(y_label), Write(x_label), run_time=0.9)
        self.wait(0.5)
        self.play(Create(curve), run_time=1.1)
        self.play(FadeIn(dot, scale=0.8), run_time=0.5)
        self.wait(0.3)

        # 3.7s - 6.0s: "This curve measures how wrong the model is,"
        cap2 = Text("The curve measures how wrong the model is.", font_size=28, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap2), run_time=0.5)
        caption = cap2
        self.play(Indicate(curve, color=BLUE_E), run_time=0.9)
        self.wait(0.9)

        # 6.1s - 9.6s: "so the goal is to push it down step by step with each iteration."
        cap3 = Text("Goal: push it down, step by step, each iteration.", font_size=28, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap3), run_time=0.5)
        caption = cap3

        # Animate dot moving along curve in stepped segments
        def move_dot_to_x(x):
            dot_target = axes.c2p(x, cost_curve(x))
            return dot.animate.move_to(dot_target)

        self.play(move_dot_to_x(10), run_time=0.8)
        self.wait(0.2)
        self.play(move_dot_to_x(18), run_time=0.8)
        self.wait(0.2)
        self.play(move_dot_to_x(26), run_time=0.8)
        self.wait(0.3)

        # 9.9s - 13.2s: "Early on, it usually drops quickly, but eventually it starts to flatten,"
        cap4 = Text("Early: drops quickly. Later: starts to flatten.", font_size=28, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap4), run_time=0.5)
        caption = cap4

        # Emphasize early steep region briefly, then later flat region
        early_seg = axes.plot(cost_curve, x_range=[0, 12], color=GREEN_C, stroke_width=7)
        late_seg = axes.plot(cost_curve, x_range=[35, 60], color=ORANGE, stroke_width=7)

        self.play(Create(early_seg), run_time=0.7)
        self.wait(0.4)
        self.play(FadeOut(early_seg), run_time=0.4)
        self.play(Create(late_seg), run_time=0.7)
        self.wait(0.4)
        self.play(FadeOut(late_seg), run_time=0.4)

        self.play(move_dot_to_x(40), run_time=1.0)
        self.wait(0.3)
        self.play(move_dot_to_x(55), run_time=0.8)
        self.wait(0.2)

        # 13.4s - 15.3s: "telling you the improvements are getting smaller."
        cap5 = Text("Improvements get smaller as it flattens.", font_size=28, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap5), run_time=0.5)
        caption = cap5
        self.play(dot.animate.scale(0.95), run_time=0.4)
        self.wait(1.0)

        # 15.7s - 20.5s: "One option is to stop training when the curve stops decreasing in a meaningful way."
        cap6 = Text("Option: stop when it no longer decreases meaningfully.", font_size=28, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap6), run_time=0.5)
        caption = cap6

        stop_line = DashedLine(
            axes.c2p(48, 0),
            axes.c2p(48, 1.02),
            dash_length=0.12,
            color=RED_C,
            stroke_width=2.5,
        )
        self.play(Create(stop_line), run_time=0.8)
        self.wait(0.8)
        self.play(FadeOut(stop_line), run_time=0.4)
        self.wait(1.3)

        # 20.9s - 24.9s: "More commonly, though, you keep going and slowly lower the learning rate, alpha,"
        cap7 = Text("More commonly: keep going, slowly lower learning rate α.", font_size=28, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap7), run_time=0.5)
        caption = cap7

        alpha_text = MathTex(r"\alpha", font_size=54, color=GREEN_C)
        alpha_value = MathTex(r"= 0.10", font_size=44, color=GREEN_C)
        alpha_group = VGroup(alpha_text, alpha_value).arrange(RIGHT, buff=0.25)
        alpha_group.next_to(chart_group, RIGHT, buff=0.6).shift(0.25 * UP)

        # Add α indicator as part of same center element: transform chart -> chart+alpha group
        chart_with_alpha = VGroup(chart, alpha_group)
        self.play(FadeIn(alpha_group, shift=0.2 * RIGHT), run_time=0.7)
        self.wait(0.6)

        # 24.9s - 27.0s: "which is the step size for each update."
        cap8 = Text("α is the step size for each update.", font_size=28, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap8), run_time=0.5)
        caption = cap8

        # Show a couple of noticeable oscillations around the minimum while α is larger
        # We'll draw a short oscillating path near the tail end and animate the dot along it.
        x0 = 52.0
        base = cost_curve(x0)

        def osc_point(t, amp):
            # t in [0, 1], advance in x while oscillating in y
            x = x0 + 8.0 * t
            y = cost_curve(x) + amp * np.sin(2 * np.pi * 3 * t)
            return axes.c2p(x, y)

        amp_big = 0.035
        osc_path_big = ParametricFunction(
            lambda t: osc_point(t, amp_big),
            t_range=[0, 1],
            color=YELLOW,
            stroke_width=3,
        )

        self.play(Create(osc_path_big), run_time=0.7)
        self.play(MoveAlongPath(dot, osc_path_big), run_time=1.2, rate_func=linear)
        self.wait(0.2)
        self.play(FadeOut(osc_path_big), run_time=0.4)
        self.wait(0.1)

        # 27.1s - 29.4s: "As alpha shrinks, the updates become gentler,"
        cap9 = Text("As α shrinks, updates become gentler.", font_size=28, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap9), run_time=0.5)
        caption = cap9

        new_alpha_value = MathTex(r"= 0.02", font_size=44, color=GREEN_C).move_to(alpha_value)
        self.play(Transform(alpha_value, new_alpha_value), run_time=0.8)
        self.wait(0.3)

        # Smaller oscillations now
        amp_small = 0.012
        osc_path_small = ParametricFunction(
            lambda t: axes.c2p(x0 + 8.0 * t, cost_curve(x0 + 8.0 * t) + amp_small * np.sin(2 * np.pi * 3 * t)),
            t_range=[0, 1],
            color=YELLOW,
            stroke_width=3,
        )
        self.play(Create(osc_path_small), run_time=0.6)
        self.play(MoveAlongPath(dot, osc_path_small), run_time=1.0, rate_func=linear)
        self.play(FadeOut(osc_path_small), run_time=0.3)
        self.wait(0.2)

        # 29.4s - 32.0s: "And those little oscillations around the minimum fade"
        cap10 = Text("Oscillations around the minimum start to fade.", font_size=28, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap10), run_time=0.5)
        caption = cap10

        # Fade the oscillation effect by reducing amplitude further while dot moves a bit
        amp_tiny = 0.004
        osc_path_tiny = ParametricFunction(
            lambda t: axes.c2p((x0 + 2.0) + 6.0 * t, cost_curve((x0 + 2.0) + 6.0 * t) + amp_tiny * np.sin(2 * np.pi * 3 * t)),
            t_range=[0, 1],
            color=YELLOW,
            stroke_width=2.5,
        )
        self.play(Create(osc_path_tiny), run_time=0.6)
        self.play(MoveAlongPath(dot, osc_path_tiny), run_time=1.1, rate_func=linear)
        self.play(FadeOut(osc_path_tiny), run_time=0.3)
        self.wait(0.1)

        # 32.0s - 33.8s: "into small careful adjustments."
        cap11 = Text("…into small, careful adjustments.", font_size=28, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap11), run_time=0.4)
        caption = cap11

        final_alpha_value = MathTex(r"= 0.005", font_size=44, color=GREEN_C).move_to(alpha_value)
        self.play(Transform(alpha_value, final_alpha_value), run_time=0.8)

        # Tiny final nudge along the curve (no visible oscillation)
        self.play(dot.animate.move_to(axes.c2p(60, cost_curve(60))), run_time=0.7)
        self.wait(0.9)