from manim import *

class PartialDerivativeLinearRegression(Scene):
    def construct(self):
        self.camera.background_color = "#000000"

        # Consistent screen zones
        title = Text("Partial derivative of a squared error term", color=WHITE, font_size=40).to_edge(UP, buff=0.5)
        caption = Text(" ", color=GRAY_A, font_size=30).to_edge(DOWN, buff=0.5)

        self.play(Write(title), run_time=1.2)
        self.play(Write(caption), run_time=0.3)

        # -------------------------
        # [0.0s - 5.8s]
        # "we're taking the partial derivative with respect to parameter theta sub j of this cost term,"
        # -------------------------
        caption_1 = Text("Take the partial derivative with respect to  θ_j", color=GRAY_A, font_size=30).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, caption_1), run_time=0.6)
        caption = caption_1

        center_1 = MathTex(
            r"\frac{\partial}{\partial \theta_j}\left[\ \cdot\ \right]",
            color=WHITE,
            font_size=72
        )
        self.play(Write(center_1), run_time=1.2)
        self.wait(4.0)  # total block ~5.8s from start

        # -------------------------
        # [6.0s - 8.9s]
        # "one-half times h of theta of x minus y all squared."
        # -------------------------
        caption_2 = Text("Cost term:  one-half times (h(θ,x) − y) squared", color=GRAY_A, font_size=30).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, caption_2), run_time=0.5)
        caption = caption_2

        center_2 = MathTex(
            r"\frac{\partial}{\partial \theta_j}\left[\ \frac{1}{2}\,\big(h(\theta,x)-y\big)^2\ \right]",
            color=WHITE,
            font_size=58
        )
        self.play(TransformMatchingTex(center_1, center_2), run_time=1.1)
        center_1 = center_2
        self.wait(1.3)

        # -------------------------
        # [9.1s - 11.3s]
        # "When you differentiate a square, the two drops down,"
        # -------------------------
        caption_3 = Text("Differentiate the square: the 2 drops down", color=GRAY_A, font_size=30).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, caption_3), run_time=0.5)
        caption = caption_3

        center_3 = MathTex(
            r"\frac{\partial}{\partial \theta_j}\left[\ \frac{1}{2}\,\big(h(\theta,x)-y\big)^2\ \right]"
            r"= \frac{1}{2}\cdot 2\big(h(\theta,x)-y\big)\cdot \frac{\partial}{\partial \theta_j}\big(h(\theta,x)-y\big)",
            color=WHITE,
            font_size=42
        )
        self.play(ReplacementTransform(center_1, center_3), run_time=1.2)
        center_1 = center_3
        self.wait(0.5)

        # -------------------------
        # [11.8s - 15.6s]
        # "and it neatly cancels the one-half, leaving just h minus y."
        # -------------------------
        caption_4 = Text("The 2 cancels the 1/2, leaving (h − y)", color=GRAY_A, font_size=30).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, caption_4), run_time=0.5)
        caption = caption_4

        center_4 = MathTex(
            r"\frac{\partial}{\partial \theta_j}\left[\ \frac{1}{2}\,\big(h(\theta,x)-y\big)^2\ \right]"
            r"= \big(h(\theta,x)-y\big)\cdot \frac{\partial}{\partial \theta_j}\big(h(\theta,x)-y\big)",
            color=WHITE,
            font_size=48
        )
        self.play(TransformMatchingTex(center_1, center_4), run_time=1.1)
        center_1 = center_4
        self.wait(2.2)

        # -------------------------
        # [16.2s - 23.4s]
        # "But h depends on theta, so we multiply by the derivative of h with respect to theta sub j by the chain rule."
        # -------------------------
        caption_5 = Text("Chain rule: multiply by  ∂h/∂θ_j  (since h depends on θ)", color=GRAY_A, font_size=30).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, caption_5), run_time=0.6)
        caption = caption_5

        center_5 = MathTex(
            r"\frac{\partial}{\partial \theta_j}\left[\ \frac{1}{2}\,\big(h(\theta,x)-y\big)^2\ \right]"
            r"= \big(h(\theta,x)-y\big)\cdot \frac{\partial h(\theta,x)}{\partial \theta_j}",
            color=WHITE,
            font_size=54
        )
        self.play(TransformMatchingTex(center_1, center_5), run_time=1.2)
        center_1 = center_5
        self.wait(5.4)

        # -------------------------
        # [23.4s - 27.9s]
        # "In linear regression, h is theta 0 plus theta 1 x 1 and so on,"
        # -------------------------
        caption_6 = Text("Linear regression hypothesis h is a weighted sum of x's", color=GRAY_A, font_size=30).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, caption_6), run_time=0.6)
        caption = caption_6

        self.play(FadeOut(center_1), run_time=0.5)
        center_h = MathTex(
            r"h(\theta,x)=\theta_0 x_0+\theta_1 x_1+\cdots+\theta_j x_j+\cdots",
            color=WHITE,
            font_size=56
        )
        self.play(Write(center_h), run_time=1.2)
        self.wait(2.2)

        # -------------------------
        # [27.9s - 31.3s]
        # "So changing Theta sub j only affects the X sub j term."
        # -------------------------
        caption_7 = Text("Changing θ_j only changes the term  θ_j x_j", color=GRAY_A, font_size=30).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, caption_7), run_time=0.6)
        caption = caption_7

        highlight = SurroundingRectangle(center_h, color=YELLOW, buff=0.25)
        self.play(Create(highlight), run_time=0.5)
        self.play(FadeOut(highlight), run_time=0.5)
        self.wait(1.8)

        # -------------------------
        # [31.3s - 35.2s]
        # "That means the derivative of H is simply X sub j,"
        # -------------------------
        caption_8 = Text("So  ∂h/∂θ_j  =  x_j", color=GRAY_A, font_size=30).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, caption_8), run_time=0.6)
        caption = caption_8

        self.play(FadeOut(center_h), run_time=0.5)
        center_dh = MathTex(
            r"\frac{\partial h(\theta,x)}{\partial \theta_j}=x_j",
            color=WHITE,
            font_size=72
        )
        self.play(Write(center_dh), run_time=1.0)
        self.wait(1.9)

        # -------------------------
        # [35.2s - 39.8s]
        # "and the whole gradient becomes H minus y times X sub j."
        # -------------------------
        caption_9 = Text("Final gradient: (h − y) x_j", color=GRAY_A, font_size=30).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, caption_9), run_time=0.6)
        caption = caption_9

        self.play(FadeOut(center_dh), run_time=0.5)
        center_final = MathTex(
            r"\frac{\partial}{\partial \theta_j}\left[\ \frac{1}{2}\,\big(h(\theta,x)-y\big)^2\ \right]"
            r"= \big(h(\theta,x)-y\big)\,x_j",
            color=WHITE,
            font_size=56
        )
        self.play(Write(center_final), run_time=1.2)
        self.wait(2.3)