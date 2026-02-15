from manim import *

class PartialDerivativeLinearRegression(Scene):
    def construct(self):
        self.camera.background_color = "#000000"

        title = Text(
            "Partial derivative of a squared error term",
            color=WHITE,
            font_size=40
        ).to_edge(UP, buff=0.5)

        caption = Text("", color=GRAY_A, font_size=30).to_edge(DOWN, buff=0.5)

        self.add(title, caption)

        def set_caption(new_text, run_time=0.6):
            nonlocal caption
            new_cap = Text(new_text, color=GRAY_A, font_size=30).to_edge(DOWN, buff=0.5)
            self.play(ReplacementTransform(caption, new_cap), run_time=run_time)
            caption = new_cap

        # Title/caption settle (1.5s total)
        self.play(Write(title), run_time=1.2)
        self.play(Write(caption), run_time=0.3)

        center = None

        # [0.0 - 5.8] (sync: 5.8s)
        set_caption("Take the partial derivative with respect to  θ_j", run_time=0.6)
        center = MathTex(r"\frac{\partial}{\partial \theta_j}\left[\ \cdot\ \right]", color=WHITE, font_size=72)
        self.play(Write(center), run_time=1.2)
        self.wait(4.0)  # total for segment: 0.6+1.2+4.0 = 5.8

        # [6.0 - 8.9] (sync: 2.9s)
        set_caption("Cost term:  one-half times (h(θ,x) − y) squared", run_time=0.5)
        center2 = MathTex(
            r"\frac{\partial}{\partial \theta_j}\left[\frac{1}{2}\,(h(\theta,x)-y)^2\right]",
            color=WHITE,
            font_size=56,
        )
        self.play(ReplacementTransform(center, center2), run_time=1.1)
        center = center2
        self.wait(1.3)  # 0.5+1.1+1.3 = 2.9

        # [9.1 - 11.3] (sync: 2.2s)
        set_caption("Differentiate the square: the 2 drops down", run_time=0.5)
        center3 = MathTex(
            r"=\frac{1}{2}\cdot 2\,(h(\theta,x)-y)\cdot \frac{\partial}{\partial \theta_j}(h(\theta,x)-y)",
            color=WHITE,
            font_size=38,
        )
        self.play(ReplacementTransform(center, center3), run_time=1.2)
        center = center3
        self.wait(0.5)  # 0.5+1.2+0.5 = 2.2

        # [11.8 - 15.6] (sync: 3.8s)
        set_caption("The 2 cancels the 1/2, leaving (h − y)", run_time=0.5)
        center4 = MathTex(
            r"=(h(\theta,x)-y)\cdot \frac{\partial}{\partial \theta_j}(h(\theta,x)-y)",
            color=WHITE,
            font_size=48,
        )
        self.play(ReplacementTransform(center, center4), run_time=1.1)
        center = center4
        self.wait(2.2)  # 0.5+1.1+2.2 = 3.8

        # [16.2 - 23.4] (sync: 7.2s)
        set_caption("Chain rule: multiply by  ∂h/∂θ_j  (since h depends on θ)", run_time=0.6)
        center5 = MathTex(
            r"=(h(\theta,x)-y)\cdot \frac{\partial h(\theta,x)}{\partial \theta_j}",
            color=WHITE,
            font_size=54,
        )
        self.play(ReplacementTransform(center, center5), run_time=1.2)
        center = center5
        self.wait(5.4)  # 0.6+1.2+5.4 = 7.2

        # [23.4 - 27.9] (sync: 4.5s)
        set_caption("Linear regression hypothesis h is a weighted sum of x's", run_time=0.6)
        center_h = MathTex(
            r"h(\theta,x)=\theta_0 x_0+\theta_1 x_1+\cdots+\theta_j x_j+\cdots",
            color=WHITE,
            font_size=52,
        )
        self.play(ReplacementTransform(center, center_h), run_time=1.2)
        center = center_h
        self.wait(2.7)  # 0.6+1.2+2.7 = 4.5

        # [27.9 - 31.3] (sync: 3.4s)
        set_caption("Changing θ_j only changes the term  θ_j x_j", run_time=0.6)
        self.wait(2.8)  # 0.6+2.8 = 3.4

        # [31.3 - 35.2] (sync: 3.9s)
        set_caption("So  ∂h/∂θ_j  =  x_j", run_time=0.6)
        center_dh = MathTex(
            r"\frac{\partial h(\theta,x)}{\partial \theta_j}=x_j",
            color=WHITE,
            font_size=72,
        )
        self.play(ReplacementTransform(center, center_dh), run_time=1.0)
        center = center_dh
        self.wait(2.3)  # 0.6+1.0+2.3 = 3.9

        # [35.2 - 39.8] (sync: 4.6s)
        set_caption("Final gradient: (h − y) x_j", run_time=0.6)
        center_final = MathTex(
            r"\frac{\partial}{\partial \theta_j}\left[\frac{1}{2}\,(h(\theta,x)-y)^2\right]=(h(\theta,x)-y)\,x_j",
            color=WHITE,
            font_size=44,
        )
        self.play(ReplacementTransform(center, center_final), run_time=1.2)
        center = center_final
        self.wait(2.8)  # 0.6+1.2+2.8 = 4.6