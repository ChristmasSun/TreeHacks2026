from manim import *
import numpy as np

class GradientDescentBowl(Scene):
    def construct(self):
        self.camera.background_color = "#000000"

        # ---------------------------
        # Helpers (2D "fake-3D" bowl)
        # ---------------------------
        def proj(u, v, w):
            """
            Simple oblique projection from (u,v,w) to screen (x,y).
            """
            return np.array([
                0.95 * u + 0.65 * v,
                -0.25 * u + 0.85 * v + 0.95 * w,
                0.0
            ])

        def J(u, v):
            # Smooth convex bowl
            return 0.22 * (u**2 + 0.85 * v**2)

        # Title and caption zones (kept as single objects each)
        title = Text("Gradient descent on a cost surface", font_size=40, color=WHITE).to_edge(UP, buff=0.5)
        caption = Text(" ", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)

        self.play(Write(title), run_time=1.0)
        self.play(Write(caption), run_time=0.4)
        self.wait(0.2)

        # ---------------------------
        # [0.0s - 6.6s] Bowl surface reveal
        # ---------------------------
        cap1 = Text(
            "Imagine J(θ₀, θ₁) as a smooth bowl-shaped surface in 3D.",
            font_size=30,
            color=GRAY_A
        ).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap1), run_time=0.6)
        caption = cap1

        # Create a wireframe-like bowl (single center element: a VGroup)
        u_min, u_max = -3.2, 3.2
        v_min, v_max = -3.0, 3.0

        du = 0.4
        dv = 0.4

        u_vals = np.arange(u_min, u_max + 1e-9, du)
        v_vals = np.arange(v_min, v_max + 1e-9, dv)

        # Surface scale to fit screen nicely
        S = 0.85

        surface_lines = VGroup()

        # Lines of constant u
        for u in np.linspace(u_min, u_max, 13):
            pts = []
            for v in v_vals:
                w = J(u, v)
                pts.append(S * proj(u, v, w))
            line = VMobject()
            line.set_points_smoothly(pts)
            line.set_stroke(color=BLUE_E, width=2, opacity=0.75)
            surface_lines.add(line)

        # Lines of constant v
        for v in np.linspace(v_min, v_max, 11):
            pts = []
            for u in u_vals:
                w = J(u, v)
                pts.append(S * proj(u, v, w))
            line = VMobject()
            line.set_points_smoothly(pts)
            line.set_stroke(color=BLUE_D, width=2, opacity=0.55)
            surface_lines.add(line)

        # A subtle rim curve for silhouette
        rim_pts = []
        rim_u = np.linspace(u_min, u_max, 80)
        v_rim = v_max
        for u in rim_u:
            rim_pts.append(S * proj(u, v_rim, J(u, v_rim)))
        rim = VMobject().set_points_smoothly(rim_pts).set_stroke(color=BLUE_A, width=3, opacity=0.9)

        bowl = VGroup(surface_lines, rim).move_to(ORIGIN + 0.1 * UP)

        self.play(LaggedStart(*[Create(m) for m in bowl], lag_ratio=0.03), run_time=3.6)
        self.wait(1.9)  # brings segment to ~6.6s total from start of narration

        # ---------------------------
        # [6.6s - 13.2s] Axes and height meaning
        # ---------------------------
        cap2 = Text(
            "θ₀ and θ₁ are the horizontal axes; height is the value of J.",
            font_size=30,
            color=GRAY_A
        ).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap2), run_time=0.6)
        caption = cap2

        # Replace center element: swap bowl (no axes) -> bowl with axes group (single center element)
        self.play(FadeOut(bowl), run_time=0.5)

        # Build an axes triad anchored near bowl center (still 2D projected)
        origin_uv = np.array([0.0, 0.0])
        origin_w = J(origin_uv[0], origin_uv[1])
        origin_pt = S * proj(origin_uv[0], origin_uv[1], origin_w)

        # Axis directions (unit-ish in uv space; then project)
        theta0_end = S * proj(2.8, 0.0, J(2.8, 0.0))
        theta1_end = S * proj(0.0, 2.6, J(0.0, 2.6))
        height_end = origin_pt + np.array([0.0, 2.6, 0.0])

        axis_theta0 = Arrow(origin_pt, theta0_end, buff=0, stroke_width=5, color=YELLOW)
        axis_theta1 = Arrow(origin_pt, theta1_end, buff=0, stroke_width=5, color=YELLOW)
        axis_J = Arrow(origin_pt, height_end, buff=0, stroke_width=5, color=GREEN)

        lab_theta0 = MathTex(r"\theta_0", color=YELLOW).scale(0.9).next_to(axis_theta0.get_end(), RIGHT, buff=0.25)
        lab_theta1 = MathTex(r"\theta_1", color=YELLOW).scale(0.9).next_to(axis_theta1.get_end(), UP, buff=0.25)
        lab_J = MathTex(r"J", color=GREEN).scale(0.9).next_to(axis_J.get_end(), UP, buff=0.25)

        # Recreate bowl and add axes+labels as one center group
        bowl2 = VGroup(surface_lines.copy(), rim.copy()).move_to(ORIGIN + 0.1 * UP)
        axes_group = VGroup(axis_theta0, axis_theta1, axis_J, lab_theta0, lab_theta1, lab_J)
        center_group = VGroup(bowl2, axes_group)

        self.play(LaggedStart(*[Create(m) for m in bowl2], lag_ratio=0.03), run_time=1.8)
        self.play(LaggedStart(Create(axis_theta0), Create(axis_theta1), Create(axis_J), lag_ratio=0.12), run_time=1.4)
        self.play(Write(lab_theta0), Write(lab_theta1), Write(lab_J), run_time=1.0)
        self.wait(0.9)
        self.wait(0.5)  # pad to ~13.2s

        # ---------------------------
        # [13.2s - 18.4s] Goal: minimum of J
        # ---------------------------
        cap3 = Text(
            "Goal: find the lowest point — the minimum value of J.",
            font_size=30,
            color=GRAY_A
        ).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap3), run_time=0.6)
        caption = cap3

        # Highlight near the bottom with a dot and brief circle (kept inside one center group)
        bottom_uv = np.array([0.0, 0.0])
        bottom_pt = S * proj(bottom_uv[0], bottom_uv[1], J(bottom_uv[0], bottom_uv[1]))
        min_dot = Dot(bottom_pt, radius=0.07, color=RED)

        # Keep at most one center element: transform center_group -> center_group_with_min
        center_group_with_min = VGroup(bowl2, axes_group, min_dot)

        self.play(FadeIn(min_dot), run_time=0.5)
        self.play(Circumscribe(min_dot, color=RED, time_width=0.8, run_time=1.2))
        self.wait(1.5)
        self.wait(0.4)  # pad to ~18.4s

        # ---------------------------
        # [18.6s - 25.5s] Initial guess point
        # ---------------------------
        cap4 = Text(
            "Start from an initial guess for (θ₀, θ₁) — maybe random, maybe (0, 0).",
            font_size=30,
            color=GRAY_A
        ).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap4), run_time=0.6)
        caption = cap4

        # Create a starting point away from the bottom
        start_uv = np.array([2.6, 1.9])
        start_pt = S * proj(start_uv[0], start_uv[1], J(start_uv[0], start_uv[1]))
        start_dot = Dot(start_pt, radius=0.075, color=WHITE)

        # Small label "start" kept minimal and short-lived to avoid clutter
        start_label = Text("start", font_size=26, color=WHITE).next_to(start_dot, UP, buff=0.25)

        # Add to existing center group as one unit by rebuilding the center group reference
        center_group = VGroup(bowl2, axes_group, min_dot, start_dot, start_label)

        self.play(FadeIn(start_dot), run_time=0.5)
        self.play(Write(start_label), run_time=0.6)
        self.wait(1.0)
        self.play(FadeOut(start_label), run_time=0.4)
        center_group = VGroup(bowl2, axes_group, min_dot, start_dot)
        self.wait(3.9)  # sustain to ~25.5s

        # ---------------------------
        # [25.5s - 30.3s] Step downhill (steepest descent direction)
        # ---------------------------
        cap5 = Text(
            "Take a small step in the steepest downhill direction.",
            font_size=30,
            color=GRAY_A
        ).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap5), run_time=0.6)
        caption = cap5

        # Compute a descent step in (u,v) using gradient of J
        def grad_J(u, v):
            return np.array([0.44 * u, 0.22 * 2 * 0.85 * v])  # [dJ/du, dJ/dv] from J definition
        g = grad_J(start_uv[0], start_uv[1])
        step_uv = start_uv - 0.55 * g / (np.linalg.norm(g) + 1e-9)

        step_pt = S * proj(step_uv[0], step_uv[1], J(step_uv[0], step_uv[1]))

        # Arrow showing step direction (must be removed quickly)
        step_arrow = Arrow(start_dot.get_center(), step_pt, buff=0, stroke_width=6, color=ORANGE)

        self.play(Create(step_arrow), run_time=0.7)
        self.play(start_dot.animate.move_to(step_pt), run_time=1.4)
        self.wait(0.5)
        self.play(FadeOut(step_arrow), run_time=0.4)
        self.wait(0.9)  # pad to ~30.3s

        # ---------------------------
        # [30.3s - 33.8s] Repeat: slide down toward bottom
        # ---------------------------
        cap6 = Text(
            "Repeat, and you slide down the surface toward the bottom.",
            font_size=30,
            color=GRAY_A
        ).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap6), run_time=0.6)
        caption = cap6

        # Animate a few more descent steps without additional center objects
        curr_uv = step_uv.copy()
        positions = []
        for _ in range(4):
            g = grad_J(curr_uv[0], curr_uv[1])
            curr_uv = curr_uv - 0.65 * g / (np.linalg.norm(g) + 1e-9)
            positions.append(S * proj(curr_uv[0], curr_uv[1], J(curr_uv[0], curr_uv[1])))

        self.play(
            start_dot.animate.move_to(positions[0]),
            run_time=0.7,
            rate_func=smooth
        )
        self.play(
            start_dot.animate.move_to(positions[1]),
            run_time=0.7,
            rate_func=smooth
        )
        self.play(
            start_dot.animate.move_to(positions[2]),
            run_time=0.7,
            rate_func=smooth
        )
        self.play(
            start_dot.animate.move_to(positions[3]),
            run_time=0.6,
            rate_func=smooth
        )
        self.wait(0.2)

        # End with a subtle emphasis on the minimum point
        self.play(Indicate(min_dot, color=RED, scale_factor=1.3), run_time=0.7)
        self.wait(0.3)