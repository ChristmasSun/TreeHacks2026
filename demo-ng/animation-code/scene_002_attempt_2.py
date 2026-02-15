from manim import *

class SupervisedLearningPipeline(Scene):
    def construct(self):
        self.camera.background_color = "#000000"

        title = Text("Supervised Learning", font_size=44, color=WHITE).to_edge(UP, buff=0.5)
        caption = Text(" ", font_size=30, color=GREY_B).to_edge(DOWN, buff=0.5)

        self.play(Write(title), run_time=0.8)
        self.play(Write(caption), run_time=0.2)

        def set_caption(new_text, run_time=0.35):
            nonlocal caption
            new_caption = Text(new_text, font_size=30, color=GREY_B).to_edge(DOWN, buff=0.5)
            self.play(ReplacementTransform(caption, new_caption), run_time=run_time)
            caption = new_caption

        center = None

        # ----------------------------
        # [0.0 - 2.5] Training set
        # ----------------------------
        set_caption("Start with a training set.", run_time=0.35)

        train_box = RoundedRectangle(corner_radius=0.25, width=6.8, height=3.2, color=BLUE_B, stroke_width=3)
        train_label = Text("Training set", font_size=34, color=WHITE).to_edge(UP, buff=0.5)
        train_label.next_to(train_box, UP, buff=0.25)

        # Use Table (not MobjectTable) to avoid unsupported kwargs in v0.19.2
        train_table = Table(
            [["x", "y"], ["1200", "300"], ["1500", "360"], ["2000", "450"]],
            include_outer_lines=True,
            line_config={"stroke_color": GREY_A, "stroke_width": 2},
            h_buff=0.9,
            v_buff=0.45,
            element_to_mobject=lambda s: Text(str(s), font_size=28, color=WHITE),
        ).scale(0.8)
        # Color columns (x yellow, y green) safely
        for r in range(2, 5):
            train_table.get_entries((r, 1)).set_color(YELLOW)
            train_table.get_entries((r, 2)).set_color(GREEN)
        train_table.get_entries((1, 1)).set_color(WHITE)
        train_table.get_entries((1, 2)).set_color(WHITE)

        train_content = VGroup(train_label, train_box, train_table).arrange(DOWN, buff=0.25)
        train_content.move_to(ORIGIN)

        center = train_content
        self.play(FadeIn(center, shift=DOWN * 0.15), run_time=1.25)
        self.wait(0.9)

        # ----------------------------
        # [2.6 - 5.3] Known right answers
        # ----------------------------
        set_caption("Examples where the right answers are known.", run_time=0.35)

        y_header = train_table.get_entries((1, 2))
        y_vals = VGroup(
            train_table.get_entries((2, 2)),
            train_table.get_entries((3, 2)),
            train_table.get_entries((4, 2)),
        )
        self.play(Indicate(y_header, color=GREEN, scale_factor=1.15), run_time=0.6)
        self.play(Indicate(y_vals, color=GREEN, scale_factor=1.07), run_time=1.1)
        self.wait(0.9)

        # ----------------------------
        # [5.7 - 7.7] Feed into learning algorithm
        # ----------------------------
        set_caption("Feed that data into a learning algorithm.", run_time=0.35)

        algo_box = RoundedRectangle(corner_radius=0.25, width=7.6, height=3.0, color=ORANGE, stroke_width=3)
        algo_label = Text("Learning Algorithm", font_size=38, color=WHITE).move_to(algo_box.get_center())
        algo_group = VGroup(algo_box, algo_label).move_to(ORIGIN)

        self.play(FadeOut(center), run_time=0.35)
        center = algo_group
        self.play(FadeIn(center, shift=DOWN * 0.15), run_time=1.0)
        self.wait(0.65)

        # ----------------------------
        # [8.3 - 12.2] Study patterns -> produce function
        # ----------------------------
        set_caption("It studies patterns and produces a function for prediction.", run_time=0.35)

        self.play(Circumscribe(algo_box, color=ORANGE, time_width=0.8), run_time=1.2)
        self.wait(0.3)

        # ----------------------------
        # [12.6 - 16.4] Hypothesis h(x)
        # ----------------------------
        set_caption("By convention, we call it a hypothesis:  h(x).", run_time=0.35)

        hyp_box = RoundedRectangle(corner_radius=0.25, width=7.6, height=3.0, color=PURPLE_B, stroke_width=3)
        hyp_label = Text("Hypothesis", font_size=38, color=WHITE)
        hyp_math = MathTex(r"h(x)", color=WHITE).scale(1.4)
        hyp_inner = VGroup(hyp_label, hyp_math).arrange(DOWN, buff=0.25).move_to(hyp_box.get_center())
        hyp_group = VGroup(hyp_box, hyp_inner).move_to(ORIGIN)

        self.play(ReplacementTransform(center, hyp_group), run_time=0.6)
        center = hyp_group
        self.play(Indicate(hyp_math, color=PURPLE_B, scale_factor=1.12), run_time=0.8)
        self.play(Indicate(hyp_box, color=PURPLE_B, scale_factor=1.03), run_time=0.8)
        self.wait(0.9)

        # ----------------------------
        # [17.2 - 18.9] x is size of house
        # ----------------------------
        set_caption("Here, x could be the size of a house.", run_time=0.35)

        x_box = RoundedRectangle(corner_radius=0.25, width=7.6, height=3.0, color=TEAL, stroke_width=3)
        x_title = Text("New input", font_size=38, color=WHITE)
        x_math = MathTex(r"x = 1800", color=YELLOW).scale(1.2)
        x_unit = Text("sq ft", font_size=30, color=GREY_B)
        x_line = VGroup(x_math, x_unit).arrange(RIGHT, buff=0.25)
        x_inner = VGroup(x_title, x_line).arrange(DOWN, buff=0.25).move_to(x_box.get_center())
        x_group = VGroup(x_box, x_inner).move_to(ORIGIN)

        self.play(ReplacementTransform(center, x_group), run_time=0.6)
        center = x_group
        self.wait(1.1)

        # ----------------------------
        # [19.3 - 22.8] h(x) is predicted price
        # ----------------------------
        set_caption("And h(x) is the price the model predicts.", run_time=0.35)

        map_group = VGroup(
            MathTex(r"h(x)", color=WHITE).scale(1.3),
            Text("maps to", font_size=34, color=GREY_B),
            Text("price", font_size=40, color=GREEN),
        ).arrange(RIGHT, buff=0.35).move_to(ORIGIN)

        self.play(ReplacementTransform(center, map_group), run_time=0.55)
        center = map_group
        self.play(Indicate(map_group[0], scale_factor=1.08, color=WHITE), run_time=0.6)
        self.play(Indicate(map_group[2], scale_factor=1.08, color=GREEN), run_time=0.6)
        self.wait(0.75)

        # ----------------------------
        # [23.3 - 27.7] Plug in brand-new house size
        # ----------------------------
        set_caption("Plug in a brand-new house size you haven't seen before.", run_time=0.35)

        plug_box = RoundedRectangle(corner_radius=0.25, width=8.4, height=3.2, color=PURPLE_B, stroke_width=3)
        plug_title = Text("Use the hypothesis", font_size=36, color=WHITE)
        plug_line = VGroup(
            MathTex(r"x = 2300", color=YELLOW).scale(1.15),
            Text("→", font_size=40, color=WHITE),
            MathTex(r"h(x)", color=WHITE).scale(1.15),
        ).arrange(RIGHT, buff=0.35)
        plug_inner = VGroup(plug_title, plug_line).arrange(DOWN, buff=0.3).move_to(plug_box.get_center())
        plug_group = VGroup(plug_box, plug_inner).move_to(ORIGIN)

        self.play(ReplacementTransform(center, plug_group), run_time=0.6)
        center = plug_group
        self.play(Indicate(plug_line[0], scale_factor=1.08, color=YELLOW), run_time=0.7)
        self.play(Indicate(plug_line[2], scale_factor=1.08, color=WHITE), run_time=0.7)
        self.wait(1.65)

        # ----------------------------
        # [27.7 - 30.5] Estimated price out the other end
        # ----------------------------
        set_caption("An estimated price comes out the other end.", run_time=0.35)

        out_box = RoundedRectangle(corner_radius=0.25, width=8.4, height=3.2, color=GREEN_B, stroke_width=3)
        out_title = Text("Estimated price", font_size=38, color=WHITE)
        out_math = MathTex(r"\$\,470\text{k}", color=GREEN).scale(1.5)
        out_inner = VGroup(out_title, out_math).arrange(DOWN, buff=0.25).move_to(out_box.get_center())
        out_group = VGroup(out_box, out_inner).move_to(ORIGIN)

        self.play(ReplacementTransform(center, out_group), run_time=0.6)
        center = out_group
        self.play(Circumscribe(out_box, color=GREEN, time_width=0.8), run_time=1.2)
        self.play(Indicate(out_math, color=GREEN, scale_factor=1.12), run_time=0.8)
        self.wait(0.5)