from manim import *

class NormalEquationScene(Scene):
    def construct(self):
        self.camera.background_color = "#000000"

        title = Text("Normal Equation (Linear Regression)", font_size=44, weight=BOLD)
        title.set_color(WHITE).to_edge(UP, buff=0.5)

        caption = Text("To find the best parameters θ for linear regression,", font_size=28)
        caption.set_color(GRAY_A).to_edge(DOWN, buff=0.5)

        self.play(Write(title), run_time=1.0)
        self.play(Write(caption), run_time=1.0)
        self.wait(1.2)  # ~0.0 - 3.2

        # [3.7s - 8.1s] gradient and set to zero
        new_caption = Text("Take the gradient ∇θJ(θ) and ask when it becomes 0.", font_size=28)
        new_caption.set_color(GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.7)
        caption = new_caption

        eq_grad0 = MathTex(r"\nabla_{\theta} J(\theta) = 0", font_size=72).set_color(WHITE)
        self.play(Write(eq_grad0), run_time=1.4)
        self.wait(2.3)

        # [8.4s - 12.6s] simplifies into a clean matrix equation
        new_caption = Text("Setting that derivative to 0 simplifies into a clean matrix equation.", font_size=28)
        new_caption.set_color(GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption

        self.play(FadeOut(eq_grad0), run_time=0.6)
        self.wait(0.2)
        self.wait(3.4)

        # [13.3s - 17.4s] X^T X θ − X^T y
        new_caption = Text("XᵀX multiplied by θ, minus Xᵀy.", font_size=28)
        new_caption.set_color(GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption

        eq_leftover = MathTex(r"X^{T}X\,\theta - X^{T}y", font_size=72)
        eq_leftover.set_color(WHITE)
        self.play(Write(eq_leftover), run_time=1.6)
        self.wait(1.9)

        # [17.4s - 20.4s] leftover must vanish
        new_caption = Text("When the gradient is 0, that leftover term must vanish.", font_size=28)
        new_caption.set_color(GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption

        highlight = SurroundingRectangle(eq_leftover, color=YELLOW, buff=0.25)
        self.play(Create(highlight), run_time=0.6)
        self.play(FadeOut(highlight), run_time=0.6)
        self.wait(1.2)

        # [20.7s - 23.7s] X^T X θ = X^T y
        new_caption = Text("So we get XᵀXθ equals Xᵀy.", font_size=28)
        new_caption.set_color(GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption

        eq_normal = MathTex(r"X^{T}X\,\theta = X^{T}y", font_size=72).set_color(WHITE)
        self.play(TransformMatchingTex(eq_leftover, eq_normal), run_time=1.2)
        self.wait(1.2)

        # [24.5s - 26.5s] called the normal equation
        new_caption = Text("This relationship is called the normal equation.", font_size=28)
        new_caption.set_color(GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption

        self.play(Circumscribe(eq_normal, color=BLUE, time_width=0.8), run_time=1.4)
        self.wait(0.0)

        # [26.8s - 29.6s] packages all training examples into one solve
        new_caption = Text("It packages all the training examples into one solve.", font_size=28)
        new_caption.set_color(GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption
        self.wait(2.2)

        # [30.0s - 32.2s] if invertible
        new_caption = Text("If XᵀX is invertible,", font_size=28)
        new_caption.set_color(GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption

        inv_box = SurroundingRectangle(eq_normal, color=GREEN, buff=0.25)
        self.play(Create(inv_box), run_time=0.6)
        self.play(FadeOut(inv_box), run_time=0.6)
        self.wait(0.4)

        # [32.2s - 34.5s] multiply both sides by inverse
        new_caption = Text("Multiply both sides by (XᵀX)⁻¹.", font_size=28)
        new_caption.set_color(GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption
        self.wait(1.7)

        # [34.5s - 39.1s] theta = (X^T X)^-1 X^T y
        new_caption = Text("Giving θ = (XᵀX)⁻¹ Xᵀy.", font_size=28)
        new_caption.set_color(GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption

        eq_solution = MathTex(r"\theta = (X^{T}X)^{-1}X^{T}y", font_size=72).set_color(WHITE)
        self.play(TransformMatchingTex(eq_normal, eq_solution), run_time=1.4)
        self.wait(1.6)

        # [39.1s - 42.8s] X is design matrix
        new_caption = Text("Here, X is the design matrix of inputs,", font_size=28)
        new_caption.set_color(GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption

        x_brief = SurroundingRectangle(eq_solution, color=BLUE, buff=0.25)
        self.play(Create(x_brief), run_time=0.5)
        self.play(FadeOut(x_brief), run_time=0.5)
        self.wait(1.1)

        # [42.8s - 45.2s] y is vector of targets
        new_caption = Text("and y is the vector of target outputs.", font_size=28)
        new_caption.set_color(GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption

        y_brief = SurroundingRectangle(eq_solution, color=YELLOW, buff=0.25)
        self.play(Create(y_brief), run_time=0.5)
        self.play(FadeOut(y_brief), run_time=0.5)
        self.wait(0.8)