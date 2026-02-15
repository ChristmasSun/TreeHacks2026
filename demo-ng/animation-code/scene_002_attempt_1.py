from manim import *

class SupervisedLearningPipeline(Scene):
    def construct(self):
        self.camera.background_color = "#000000"

        # ----------------------------
        # Persistent zones: title + caption
        # ----------------------------
        title = Text("Supervised Learning", font_size=44, color=WHITE).to_edge(UP, buff=0.5)
        caption = Text(" ", font_size=30, color=GREY_B).to_edge(DOWN, buff=0.5)

        self.play(Write(title), run_time=0.8)
        self.play(Write(caption), run_time=0.2)

        # Helper to update caption safely
        def set_caption(new_text, run_time=0.35):
            nonlocal caption
            new_caption = Text(new_text, font_size=30, color=GREY_B).to_edge(DOWN, buff=0.5)
            self.play(ReplacementTransform(caption, new_caption), run_time=run_time)
            caption = new_caption

        # ----------------------------
        # [0.0 - 2.5] Training set
        # ----------------------------
        set_caption("Start with a training set.", run_time=0.35)

        train_box = RoundedRectangle(corner_radius=0.25, width=4.6, height=2.6, color=BLUE_B, stroke_width=3)
        train_label = Text("Training set", font_size=34, color=WHITE)
        train_label.next_to(train_box, UP, buff=0.25)

        # Simple "table" with (x, y) examples (kept inside one center group)
        table = MobjectTable(
            [
                [MathTex("x", color=WHITE), MathTex("y", color=WHITE)],
                [MathTex("1200", color=YELLOW), MathTex("300", color=GREEN)],
                [MathTex("1500", color=YELLOW), MathTex("360", color=GREEN)],
                [MathTex("2000", color=YELLOW), MathTex("450", color=GREEN)],
            ],
            include_outer_lines=True,
            line_config={"stroke_color": GREY_A, "stroke_width": 2},
            element_alignment_corner=ORIGIN,
            h_buff=0.7,
            v_buff=0.35,
        ).scale(0.65)

        training_group = VGroup(train_box, train_label, table).arrange(DOWN, buff=0.25)
        training_group.move_to(ORIGIN)

        self.play(Create(train_box), run_time=0.55)
        self.play(Write(train_label), run_time=0.35)
        self.play(Create(table), run_time=0.7)
        self.wait(0.55)  # total ~2.5s including caption

        # ----------------------------
        # [2.6 - 5.3] Known right answers
        # ----------------------------
        set_caption("Examples where the right answers are known.", run_time=0.35)

        # Brief highlight on the y column without adding extra objects (use Indicate)
        y_header = table.get_entries((1, 2))
        y_vals = VGroup(table.get_entries((2, 2)), table.get_entries((3, 2)), table.get_entries((4, 2)))

        self.play(Indicate(y_header, color=GREEN, scale_factor=1.15), run_time=0.6)
        self.play(Indicate(y_vals, color=GREEN, scale_factor=1.07), run_time=1.1)
        self.wait(0.9)

        # ----------------------------
        # [5.7 - 7.7] Feed into learning algorithm (introduce algorithm block + arrow)
        # Pipeline is one center element (single VGroup) from here on.
        # ----------------------------
        set_caption("Feed that data into a learning algorithm.", run_time=0.35)

        algo_box = RoundedRectangle(corner_radius=0.25, width=4.6, height=2.6, color=ORANGE, stroke_width=3)
        algo_label = Text("Learning\nAlgorithm", font_size=34, color=WHITE, line_spacing=0.9)
        algo_label.move_to(algo_box.get_center())

        arrow1 = Arrow(LEFT, RIGHT, color=WHITE, stroke_width=4, max_tip_length_to_length_ratio=0.12)

        # Re-layout: training -> arrow -> algorithm
        training_group.generate_target()
        algo_group = VGroup(algo_box, algo_label)
        pipeline1 = VGroup(training_group.target, arrow1, algo_group).arrange(RIGHT, buff=0.6)
        pipeline1.move_to(ORIGIN)

        # Animate movement and creation without leaving old center elements around
        self.play(MoveToTarget(training_group), run_time=0.5)
        self.play(Create(arrow1), run_time=0.5)
        self.play(Create(algo_box), run_time=0.45)
        self.play(Write(algo_label), run_time=0.35)
        self.wait(0.45)

        # ----------------------------
        # [8.3 - 12.2] Study patterns -> produce function for predictions
        # ----------------------------
        set_caption("It studies patterns and produces a function for prediction.", run_time=0.35)

        # Gentle emphasis on algorithm block
        self.play(Circumscribe(algo_box, color=ORANGE, time_width=0.8), run_time=1.2)

        # Add hypothesis block with arrow from algorithm
        hyp_box = RoundedRectangle(corner_radius=0.25, width=4.6, height=2.6, color=PURPLE_B, stroke_width=3)
        hyp_label = Text("Hypothesis", font_size=34, color=WHITE)
        hyp_math = MathTex(r"h(x)", color=WHITE).scale(1.2)

        hyp_inner = VGroup(hyp_label, hyp_math).arrange(DOWN, buff=0.25)
        hyp_inner.move_to(hyp_box.get_center())

        arrow2 = Arrow(LEFT, RIGHT, color=WHITE, stroke_width=4, max_tip_length_to_length_ratio=0.12)

        full_group = VGroup(training_group, arrow1, algo_group, arrow2, VGroup(hyp_box, hyp_inner)).arrange(RIGHT, buff=0.6)
        full_group.move_to(ORIGIN)

        # Transform layout by moving existing pieces, then create new ones
        self.play(
            training_group.animate.shift(LEFT * 2.6),
            arrow1.animate.shift(LEFT * 1.8),
            algo_group.animate.shift(LEFT * 1.0),
            run_time=0.6
        )
        arrow2.next_to(algo_group, RIGHT, buff=0.6)
        VGroup(hyp_box, hyp_inner).next_to(arrow2, RIGHT, buff=0.6)

        # Ensure overall centered
        temp_all = VGroup(training_group, arrow1, algo_group, arrow2, hyp_box, hyp_inner)
        temp_all.move_to(ORIGIN)

        self.play(Create(arrow2), run_time=0.5)
        self.play(Create(hyp_box), run_time=0.45)
        self.play(Write(hyp_label), run_time=0.35)
        self.play(Write(hyp_math), run_time=0.35)
        self.wait(0.65)

        # ----------------------------
        # [12.6 - 16.4] Name it: hypothesis written as h(x)
        # ----------------------------
        set_caption("By convention, we call it a hypothesis:  h(x).", run_time=0.35)

        self.play(Indicate(hyp_math, color=PURPLE_B, scale_factor=1.12), run_time=0.8)
        self.play(Indicate(hyp_box, color=PURPLE_B, scale_factor=1.03), run_time=0.8)
        self.wait(1.05)

        # ----------------------------
        # [17.2 - 18.9] x is size of a house
        # ----------------------------
        set_caption("Here, x could be the size of a house.", run_time=0.35)

        newx_box = RoundedRectangle(corner_radius=0.25, width=4.6, height=2.6, color=TEAL, stroke_width=3)
        newx_title = Text("New input", font_size=34, color=WHITE)
        newx_math = MathTex(r"x = 1800", color=YELLOW).scale(1.1)
        newx_unit = Text("sq ft", font_size=28, color=GREY_B)

        newx_line = VGroup(newx_math, newx_unit).arrange(RIGHT, buff=0.25)
        newx_inner = VGroup(newx_title, newx_line).arrange(DOWN, buff=0.25)
        newx_inner.move_to(newx_box.get_center())

        arrow3 = Arrow(LEFT, RIGHT, color=WHITE, stroke_width=4, max_tip_length_to_length_ratio=0.12)

        # Place new input to the right of hypothesis (keeps pipeline feel)
        arrow3.next_to(hyp_box, RIGHT, buff=0.6)
        newx_group = VGroup(newx_box, newx_inner).next_to(arrow3, RIGHT, buff=0.6)

        # Recenter all
        all_now = VGroup(training_group, arrow1, algo_group, arrow2, hyp_box, hyp_inner, arrow3, newx_group)
        all_now.move_to(ORIGIN)

        self.play(Create(arrow3), run_time=0.4)
        self.play(Create(newx_box), run_time=0.45)
        self.play(Write(newx_title), run_time=0.35)
        self.play(Write(newx_math), run_time=0.35)
        self.play(Write(newx_unit), run_time=0.25)
        self.wait(0.05)

        # ----------------------------
        # [19.3 - 22.8] h(x) is predicted price
        # ----------------------------
        set_caption("And h(x) is the price the model predicts.", run_time=0.35)

        # Emphasize mapping: h(x) -> price (without extra lingering objects)
        self.play(Indicate(hyp_math, color=WHITE, scale_factor=1.08), run_time=0.6)

        # Add output box after new x with arrow
        out_box = RoundedRectangle(corner_radius=0.25, width=4.6, height=2.6, color=GREEN_B, stroke_width=3)
        out_title = Text("Predicted price", font_size=32, color=WHITE)
        out_math = MathTex(r"\$\,390\text{k}", color=GREEN).scale(1.15)
        out_inner = VGroup(out_title, out_math).arrange(DOWN, buff=0.25)
        out_inner.move_to(out_box.get_center())

        arrow4 = Arrow(LEFT, RIGHT, color=WHITE, stroke_width=4, max_tip_length_to_length_ratio=0.12)
        arrow4.next_to(newx_box, RIGHT, buff=0.6)
        out_group = VGroup(out_box, out_inner).next_to(arrow4, RIGHT, buff=0.6)

        all_with_out = VGroup(training_group, arrow1, algo_group, arrow2, hyp_box, hyp_inner, arrow3, newx_group, arrow4, out_group)
        all_with_out.move_to(ORIGIN)

        self.play(Create(arrow4), run_time=0.4)
        self.play(Create(out_box), run_time=0.45)
        self.play(Write(out_title), run_time=0.35)
        self.play(Write(out_math), run_time=0.35)
        self.wait(0.6)

        # ----------------------------
        # [23.3 - 27.7] Plug in size of brand-new house
        # ----------------------------
        set_caption("Plug in a brand-new house size you haven't seen before.", run_time=0.35)

        # Animate "new x" value changing to reinforce "brand-new"
        newx_math2 = MathTex(r"x = 2300", color=YELLOW).scale(1.1)
        newx_math2.move_to(newx_math.get_center())

        self.play(Transform(newx_math, newx_math2), run_time=0.8)

        # Update output to reflect new prediction (still strictly within same center pipeline)
        out_math2 = MathTex(r"\$\,470\text{k}", color=GREEN).scale(1.15)
        out_math2.move_to(out_math.get_center())

        self.play(Transform(out_math, out_math2), run_time=0.8)
        self.wait(2.0)

        # ----------------------------
        # [27.7 - 30.5] Estimated price out the other end
        # ----------------------------
        set_caption("An estimated price comes out the other end.", run_time=0.35)

        # Subtle emphasis on output
        self.play(Circumscribe(out_box, color=GREEN, time_width=0.8), run_time=1.2)
        self.play(Indicate(out_math, color=GREEN, scale_factor=1.12), run_time=0.8)
        self.wait(0.5)