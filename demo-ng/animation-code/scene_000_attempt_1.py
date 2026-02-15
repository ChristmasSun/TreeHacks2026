from manim import *

class SupervisedLearningMapping(Scene):
    def construct(self):
        self.camera.background_color = "#000000"

        # -----------------------------
        # Helpers (keep object count low)
        # -----------------------------
        def make_title(text):
            return Text(text, font_size=44, color=WHITE).to_edge(UP, buff=0.5)

        def make_caption(text):
            return Text(text, font_size=28, color=GRAY_B).to_edge(DOWN, buff=0.5)

        # Colors
        x_color = BLUE_B
        y_color = YELLOW_B
        rule_color = GREEN_B

        # -----------------------------
        # 0.0s - 6.5s
        # -----------------------------
        title = make_title("Supervised Learning")
        caption = make_caption("Paired examples: input X with desired output Y")

        self.play(Write(title), run_time=0.9)
        self.play(Write(caption), run_time=0.8)

        x_token = MathTex("X", color=x_color).scale(1.8)
        y_token = MathTex("Y", color=y_color).scale(1.8)

        arrow_xy = Arrow(LEFT, RIGHT, buff=0.3, color=WHITE, stroke_width=6).scale(2.0)
        mapping = VGroup(x_token, arrow_xy, y_token).arrange(RIGHT, buff=1.0).move_to(ORIGIN)

        self.play(Write(x_token), run_time=0.5)
        self.play(Create(arrow_xy), run_time=0.6)
        self.play(Write(y_token), run_time=0.5)

        self.wait(3.2)  # pacing to 6.5s total

        # -----------------------------
        # 6.5s - 8.5s
        # -----------------------------
        new_caption = make_caption("Example: a self-driving car")
        self.play(ReplacementTransform(caption, new_caption), run_time=0.5)
        caption = new_caption

        self.wait(1.5)

        # -----------------------------
        # 8.5s - 13.0s
        # Show X as road image, Y as steering angle
        # Keep as ONE center element (a grouped diagram)
        # -----------------------------
        new_caption = make_caption("X: road image   →   Y: steering direction")
        self.play(ReplacementTransform(caption, new_caption), run_time=0.5)
        caption = new_caption

        self.play(FadeOut(mapping), run_time=0.4)

        # Road "image" card (simple, non-overlapping)
        card = RoundedRectangle(width=4.4, height=2.8, corner_radius=0.25, stroke_color=x_color, stroke_width=5)
        sky = Rectangle(width=4.0, height=1.1, fill_color=BLUE_E, fill_opacity=0.55, stroke_width=0).move_to(card.get_center() + 0.65 * UP)
        road = Polygon(
            card.get_bottom() + 1.0 * LEFT,
            card.get_bottom() + 1.0 * RIGHT,
            card.get_bottom() + 0.35 * RIGHT + 1.4 * UP,
            card.get_bottom() + 0.35 * LEFT + 1.4 * UP,
            fill_color=GRAY_D,
            fill_opacity=0.9,
            stroke_width=0,
        )
        lane = DashedLine(
            start=road.get_bottom() + 0.0 * LEFT + 0.15 * UP,
            end=road.get_top() + 0.0 * LEFT + 0.15 * DOWN,
            dash_length=0.12,
            dashed_ratio=0.55,
            color=YELLOW_E,
            stroke_width=4,
        )
        x_label = MathTex("X", color=x_color).scale(1.3).next_to(card, UP, buff=0.25)

        x_card = VGroup(card, sky, road, lane, x_label)

        # Steering wheel / angle indicator
        wheel = Circle(radius=0.95, color=y_color, stroke_width=6)
        spoke1 = Line(ORIGIN, 0.75 * UP, color=y_color, stroke_width=5)
        spoke2 = Line(ORIGIN, 0.65 * LEFT + 0.15 * DOWN, color=y_color, stroke_width=5)
        spoke3 = Line(ORIGIN, 0.65 * RIGHT + 0.15 * DOWN, color=y_color, stroke_width=5)
        hub = Dot(radius=0.06, color=y_color)
        wheel_group = VGroup(wheel, spoke1, spoke2, spoke3, hub)

        angle_arc = Arc(radius=1.15, start_angle=-0.2, angle=0.8, color=WHITE, stroke_width=5)
        angle_arrow = Arrow(
            start=angle_arc.point_from_proportion(0.85),
            end=angle_arc.point_from_proportion(1.0),
            buff=0.0,
            color=WHITE,
            stroke_width=5,
            max_tip_length_to_length_ratio=0.25,
        )
        y_label = MathTex("Y", color=y_color).scale(1.3).next_to(wheel_group, UP, buff=0.25)

        y_angle = VGroup(wheel_group, angle_arc, angle_arrow, y_label)

        right_arrow = Arrow(LEFT, RIGHT, buff=0.3, color=WHITE, stroke_width=6).scale(1.4)

        car_mapping = VGroup(x_card, right_arrow, y_angle).arrange(RIGHT, buff=0.9).move_to(ORIGIN)

        self.play(Create(card), run_time=0.5)
        self.play(FadeIn(sky, road, lane, run_time=0.6), run_time=0.6)
        self.play(Write(x_label), run_time=0.3)
        self.play(Create(right_arrow), run_time=0.5)
        self.play(Create(wheel), run_time=0.5)
        self.play(Create(VGroup(spoke1, spoke2, spoke3)), run_time=0.5)
        self.play(Create(angle_arc), Create(angle_arrow), run_time=0.6)
        self.play(Write(y_label), run_time=0.3)

        self.wait(2.3)

        # -----------------------------
        # 13.0s - 16.5s
        # Learn a rule mapping inputs to outputs: f : X -> Y
        # -----------------------------
        new_caption = make_caption("Learn a rule that maps inputs to outputs")
        self.play(ReplacementTransform(caption, new_caption), run_time=0.5)
        caption = new_caption

        self.play(FadeOut(car_mapping), run_time=0.5)

        fx = MathTex("f", color=rule_color).scale(1.8)
        x2 = MathTex("X", color=x_color).scale(1.8)
        y2 = MathTex("Y", color=y_color).scale(1.8)

        arrow1 = Arrow(LEFT, RIGHT, buff=0.25, color=WHITE, stroke_width=6).scale(1.25)
        arrow2 = Arrow(LEFT, RIGHT, buff=0.25, color=WHITE, stroke_width=6).scale(1.25)

        rule_map = VGroup(x2, arrow1, fx, arrow2, y2).arrange(RIGHT, buff=0.55).move_to(ORIGIN)

        self.play(Write(x2), run_time=0.4)
        self.play(Create(arrow1), run_time=0.35)
        self.play(Write(fx), run_time=0.35)
        self.play(Create(arrow2), run_time=0.35)
        self.play(Write(y2), run_time=0.4)

        self.wait(1.8)

        # -----------------------------
        # 16.5s - 20.5s
        # New image -> predict steering angle
        # -----------------------------
        new_caption = make_caption("New X comes in → predict Y (steering angle)")
        self.play(ReplacementTransform(caption, new_caption), run_time=0.5)
        caption = new_caption

        # Evolve to f(X) = Y
        fx_eq1 = MathTex("f(X)", "=", "Y").scale(1.6)
        fx_eq1[0].set_color(rule_color)
        fx_eq1[2].set_color(y_color)

        # Color X inside f(X) by building separate token (avoid tex_to_color_map single-letter hazards)
        fx_eq1_x = fx_eq1[0].get_part_by_tex("X")
        if fx_eq1_x:
            fx_eq1_x.set_color(x_color)

        self.play(TransformMatchingTex(rule_map, fx_eq1), run_time=0.9)
        self.wait(2.6)

        # -----------------------------
        # 20.5s - 25.5s
        # Regression: continuous output
        # -----------------------------
        new_caption = make_caption("Continuous output → regression")
        self.play(ReplacementTransform(caption, new_caption), run_time=0.5)
        caption = new_caption

        self.play(FadeOut(fx_eq1), run_time=0.4)

        reg = MathTex(r"Y \in \mathbb{R}", color=WHITE).scale(1.7)
        y_part = reg.get_part_by_tex("Y")
        if y_part:
            y_part.set_color(y_color)

        self.play(Write(reg), run_time=0.8)

        # Brief emphasis (highlight removed quickly)
        box = SurroundingRectangle(reg, color=GREEN_B, buff=0.25, stroke_width=4)
        self.play(Create(box), run_time=0.35)
        self.wait(0.6)
        self.play(FadeOut(box), run_time=0.3)

        self.wait(2.55)

        # -----------------------------
        # 25.5s - 27.8s
        # Transition to classification
        # -----------------------------
        new_caption = make_caption("Or Y must be one of a few options…")
        self.play(ReplacementTransform(caption, new_caption), run_time=0.5)
        caption = new_caption

        self.wait(1.8)

        # -----------------------------
        # 27.8s - 30.4s
        # Few distinct categories: stop vs go
        # -----------------------------
        new_caption = make_caption("…distinct categories, like stop vs go")
        self.play(ReplacementTransform(caption, new_caption), run_time=0.5)
        caption = new_caption

        self.play(FadeOut(reg), run_time=0.4)

        # Single center element: Y ∈ {STOP, GO}
        cls = MathTex(r"Y \in \{\text{STOP},\ \text{GO}\}", color=WHITE).scale(1.45)
        y_part2 = cls.get_part_by_tex("Y")
        if y_part2:
            y_part2.set_color(y_color)

        self.play(Write(cls), run_time=0.8)
        self.wait(1.4)

        # -----------------------------
        # 30.4s - 31.8s
        # Classification label
        # -----------------------------
        new_caption = make_caption("Discrete output → classification")
        self.play(ReplacementTransform(caption, new_caption), run_time=0.5)
        caption = new_caption

        # quick emphasis, then end
        box2 = SurroundingRectangle(cls, color=RED_B, buff=0.25, stroke_width=4)
        self.play(Create(box2), run_time=0.35)
        self.wait(0.55)
        self.play(FadeOut(box2), run_time=0.3)
        self.wait(0.25)