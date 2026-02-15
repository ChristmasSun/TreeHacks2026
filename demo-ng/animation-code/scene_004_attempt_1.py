from manim import *

class SummationHypothesis(Scene):
    def construct(self):
        self.camera.background_color = "#000000"

        # --- Persistent zones (title + caption are the only constant objects) ---
        title = Text("Summation notation for a linear hypothesis", font_size=42, color=WHITE).to_edge(UP, buff=0.5)
        caption = Text(" ", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)

        self.play(Write(title), run_time=1.2)
        self.play(Write(caption), run_time=0.2)

        # [0.0 - 5.4] "One tidy way to rewrite this hypothesis is to use summation notation."
        cap1 = Text("Rewrite the hypothesis using summation notation.", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap1), run_time=0.6)
        caption = cap1
        self.wait(4.6)

        # Center element 1: expanded expression
        # [5.4 - 10.5] "Instead of writing Theta 0 plus Theta 1 times x1 plus Theta 2 times x2,"
        cap2 = Text("Instead of writing it term-by-term...", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap2), run_time=0.5)
        caption = cap2

        expanded = MathTex(
            r"\theta_0 + \theta_1 x_1 + \theta_2 x_2",
            font_size=72,
            color=WHITE
        ).move_to(ORIGIN)

        self.play(Write(expanded), run_time=1.3)
        self.wait(3.3)

        # Transform to summation
        # [10.5 - 15.3] "we write a sum from j equals 0 to 2 Theta j times xj."
        cap3 = Text("...write a single sum.", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap3), run_time=0.5)
        caption = cap3

        summation = MathTex(
            r"\sum_{j=0}^{2} \theta_j x_j",
            font_size=78,
            color=WHITE
        ).move_to(ORIGIN)

        self.play(TransformMatchingTex(expanded, summation), run_time=1.6)
        self.wait(2.6)

        # [15.3 - 19.3] "To make that work, we introduce a helpful trick."
        cap4 = Text("A small trick makes the indexing uniform.", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap4), run_time=0.5)
        caption = cap4
        self.wait(3.0)

        # Replace summation with x0 definition (keep center single object)
        # [19.3 - 21.6] "Define x0 to be one,"
        cap5 = Text(r"Define $x_0$ to be 1.", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap5), run_time=0.4)
        caption = cap5

        x0_def = MathTex(r"x_0 = 1", font_size=86, color=YELLOW).move_to(ORIGIN)
        self.play(ReplacementTransform(summation, x0_def), run_time=0.9)
        self.wait(1.0)

        # [21.6 - 24.0] "a dummy feature that never changes."
        cap6 = Text("This is a dummy feature that never changes.", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap6), run_time=0.5)
        caption = cap6

        self.play(Indicate(x0_def, color=YELLOW), run_time=0.8)
        self.wait(1.1)

        # [24.0 - 29.1] "Then the Theta 0 term fits the same pattern as the others because it's just Theta 0 times x0."
        cap7 = Text(r"Then $\theta_0$ fits the pattern: $\theta_0 x_0$.", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap7), run_time=0.6)
        caption = cap7

        theta0x0 = MathTex(r"\theta_0 = \theta_0 x_0", font_size=78, color=WHITE).move_to(ORIGIN)
        # Color the key factor x_0 and the "1" idea via x_0 token only (safe token)
        theta0x0.set_color_by_tex(r"x_0", YELLOW)
        self.play(ReplacementTransform(x0_def, theta0x0), run_time=1.0)
        self.wait(3.5)

        # [29.1 - 31.4] "With this setup, the whole expression looks like"
        cap8 = Text("Now it packages neatly...", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap8), run_time=0.5)
        caption = cap8
        self.wait(1.8)

        # [31.4 - 35.1] "a clean dot product between two vectors, theta and x."
        cap9 = Text(r"...as a dot product of vectors $\theta$ and $x$.", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, cap9), run_time=0.5)
        caption = cap9

        dot = MathTex(r"\theta \cdot x", font_size=92, color=WHITE).move_to(ORIGIN)
        # Color vector symbols (whole tokens, safe)
        dot.set_color_by_tex(r"\theta", BLUE_B)
        dot.set_color_by_tex(r"x", GREEN_B)

        self.play(TransformMatchingTex(theta0x0, dot), run_time=1.2)
        self.wait(2.0)

        # Total timing targets ~35.1s achieved by run_time + waits above.