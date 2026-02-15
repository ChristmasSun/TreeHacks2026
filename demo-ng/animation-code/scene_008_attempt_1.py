from manim import *

class GradientDescentUpdate(Scene):
    def construct(self):
        self.camera.background_color = "#000000"

        # ---------- Title (top zone) ----------
        title = Text("Gradient Descent Update", font_size=44, color=WHITE).to_edge(UP, buff=0.5)
        self.play(Write(title), run_time=0.9)

        # ---------- Caption (bottom zone) ----------
        caption = Text("Each step updates every parameter, one by one.", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(Write(caption), run_time=0.7)

        # [0.0s - 4.3s]
        # Center element: parameter list to suggest "one by one"
        theta_list = MathTex(
            r"\Theta_0,\ \Theta_1,\ \Theta_2,\ \ldots,\ \Theta_n",
            font_size=56,
            color=WHITE
        )
        theta_list.move_to(ORIGIN)
        self.play(Write(theta_list), run_time=1.1)
        self.play(Indicate(theta_list, color=YELLOW), run_time=1.0)
        self.wait(0.6)

        # [4.3s - 6.9s] "You'll often see it written like this,"
        new_caption = Text("You'll often see it written like this:", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.5)
        caption = new_caption

        self.play(FadeOut(theta_list), run_time=0.4)
        self.wait(0.1)

        # Build equation progressively (single center element throughout)
        # [6.9s - 11.3s] "Theta sub j colon equals Theta sub j minus alpha"
        eq_step1 = MathTex(
            r"\Theta_j",
            r"\ :=\ ",
            r"\Theta_j - \alpha",
            font_size=64
        )
        eq_step1.set_color(WHITE)
        eq_step1.move_to(ORIGIN)

        self.play(Write(eq_step1[0]), run_time=0.35)  # Theta_j
        self.play(Write(eq_step1[1]), run_time=0.55)  # := 
        self.play(Write(eq_step1[2]), run_time=0.9)   # Theta_j - alpha
        self.wait(0.3)

        # [11.3s - 15.0s] "times the partial derivative of J with respect to Theta sub j."
        eq_step2 = MathTex(
            r"\Theta_j",
            r"\ :=\ ",
            r"\Theta_j - \alpha",
            r"\,\frac{\partial J}{\partial \Theta_j}",
            font_size=64
        ).move_to(ORIGIN)

        self.play(TransformMatchingTex(eq_step1, eq_step2), run_time=1.1)
        eq = eq_step2
        self.wait(0.6)

        # [15.0s - 17.4s] "That colon equals symbol is important."
        new_caption = Text("The ':=' symbol is important.", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.5)
        caption = new_caption

        assign_highlight = SurroundingRectangle(eq[1], color=YELLOW, buff=0.12)
        self.play(Create(assign_highlight), run_time=0.45)
        self.play(Indicate(eq[1], color=YELLOW), run_time=0.6)
        self.wait(0.25)

        # [17.4s - 20.1s] "It means assignment as in take the value on the right"
        new_caption = Text("Assignment: take the value on the right...", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.55)
        caption = new_caption

        rhs_highlight = SurroundingRectangle(VGroup(eq[2], eq[3]), color=BLUE, buff=0.18)
        self.play(FadeOut(assign_highlight), run_time=0.25)
        self.play(Create(rhs_highlight), run_time=0.5)
        self.wait(0.65)

        # [20.1s - 22.8s] "and store it back into Theta sub j on the left."
        new_caption = Text("...and store it back into the left-hand parameter.", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.55)
        caption = new_caption

        lhs_highlight = SurroundingRectangle(eq[0], color=GREEN, buff=0.18)
        self.play(ReplacementTransform(rhs_highlight, lhs_highlight), run_time=0.5)
        self.wait(0.55)
        self.play(FadeOut(lhs_highlight), run_time=0.3)

        # [22.8s - 27.3s] "Alpha is the learning rate..."
        new_caption = Text("α is the learning rate (step size).", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.55)
        caption = new_caption

        alpha_highlight = SurroundingRectangle(eq[2], color=RED, buff=0.15)
        self.play(Create(alpha_highlight), run_time=0.45)

        # Briefly focus on α itself without risky tex parsing: highlight the whole term then indicate
        self.play(Indicate(eq[2], color=RED), run_time=0.7)
        self.wait(0.55)
        self.play(FadeOut(alpha_highlight), run_time=0.3)

        # [27.3s - 32.0s] "repeat this for every j from j = 0 through j = n"
        new_caption = Text("Repeat for every j: from j = 0 through j = n.", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.55)
        caption = new_caption

        j_range = MathTex(r"j = 0, 1, 2, \ldots, n", font_size=56, color=WHITE).move_to(ORIGIN)
        self.play(FadeOut(eq), run_time=0.4)
        self.play(Write(j_range), run_time=0.9)
        self.wait(0.9)

        # [32.0s - 33.8s] "where n is the number of features."
        new_caption = Text("Here, n is the number of features.", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.55)
        caption = new_caption

        n_highlight = SurroundingRectangle(j_range, color=YELLOW, buff=0.18)
        self.play(Create(n_highlight), run_time=0.4)
        self.wait(0.55)

        # Clean end
        self.play(FadeOut(n_highlight), run_time=0.2)
        self.play(FadeOut(j_range), run_time=0.3)
        self.play(FadeOut(title), FadeOut(caption), run_time=0.5)
        self.wait(0.1)