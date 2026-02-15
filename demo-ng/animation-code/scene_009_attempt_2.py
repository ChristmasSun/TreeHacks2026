from manim import *

class PartialDerivativeLinearRegression(Scene):
    def construct(self):
        self.camera.background_color = "#000000"

        title = Text(
            "Partial derivative of a squared error term",
            color=WHITE,
            font_size=40
        ).to_edge(UP, buff=0.5)

        caption = Text(" ", color=GRAY_A, font_size=30).to_edge(DOWN, buff=0.5)

        self.add(title)
        self.add(caption)

        # Use SVG output to avoid DVI->SVG conversion dependency (dvisvgm).
        tex_template = TexTemplate()
        tex_template.tex_compiler = "pdflatex"
        tex_template.output_format = ".pdf"

        # Helper for timed caption swaps
        def set_caption(new_text, run_time=0.6):
            nonlocal caption
            new_cap = Text(new_text, color=GRAY_A, font_size=30).to_edge(DOWN, buff=0.5)
            self.play(ReplacementTransform(caption, new_cap), run_time=run_time)
            caption = new_cap

        # Initial title reveal (part of total timing)
        self.play(Write(title), run_time=1.2)
        self.play(Write(caption), run_time=0.3)

        # 1) [0.0 - 5.8] partial derivative setup
        set_caption("Take the partial derivative with respect to  θ_j", run_time=0.6)

        center = MathTex(
            r"\frac{\partial}{\partial \theta_j}\left[\ \cdot\ \right]",
            color=WHITE,
            font_size=72,
            tex_template=tex_template,
        )
        self.play(Write(center), run_time=1.2)
        self.wait(2.5)

        # 2) [6.0 - 8.9] plug in the cost term
        set_caption("Cost term:  one-half times (h(θ,x) − y) squared", run_time=0.5)

        center2 = MathTex(
            r"\frac{\partial}{\partial \theta_j}\left[\ \frac{1}{2}\,\big(h(\theta,x)-y\big)^2\ \right]",
            color=WHITE,
            font_size=58,
            tex_template=tex_template,
        )
        self.play(ReplacementTransform(center, center2), run_time=1.1)
        center = center2
        self.wait(1.3)

        # 3) [9.1 - 11.3] bring down the 2 (keep MathTex short and safe)
        set_caption("Differentiate the square: the 2 drops down", run_time=0.5)

        center3 = MathTex(
            r"= \frac{1}{2}\cdot 2\big(h(\theta,x)-y\big)\cdot \frac{\partial}{\partial \theta_j}\big(h(\theta,x)-y\big)",
            color=WHITE,
            font_size=42,
            tex_template=tex_template,
        )
        self.play(ReplacementTransform(center, center3), run_time=1.2)
        center = center3
        self.wait(0.5)

        # 4) [11.8 - 15.6] cancel 2 and 1/2
        set_caption("The 2 cancels the 1/2, leaving (h − y)", run_time=0.5)

        center4 = MathTex(
            r"= \big(h(\theta,x)-y\big)\cdot \frac{\partial}{\partial \theta_j}\big(h(\theta,x)-y\big)",
            color=WHITE,
            font_size=48,
            tex_template=tex_template,
        )
        self.play(ReplacementTransform(center, center4), run_time=1.1)
        center = center4
        self.wait(2.2)

        # 5) [16.2 - 23.4] chain rule: derivative of h
        set_caption("Chain rule: multiply by  ∂h/∂θ_j  (since h depends on θ)", run_time=0.6)

        center5 = MathTex(
            r"= \big(h(\theta,x)-y\big)\cdot \frac{\partial h(\theta,x)}{\partial \theta_j}",
            color=WHITE,
            font_size=54,
            tex_template=tex_template,
        )
        self.play(ReplacementTransform(center, center5), run_time=1.2)
        center = center5
        self.wait(5.4)

        # 6) [23.4 - 27.9] show linear regression hypothesis
        set_caption("Linear regression hypothesis h is a weighted sum of x's", run_time=0.6)

        center_h = MathTex(
            r"h(\theta,x)=\theta_0 x_0+\theta_1 x_1+\cdots+\theta_j x_j+\cdots",
            color=WHITE,
            font_size=56,
            tex_template=tex_template,
        )
        self.play(ReplacementTransform(center, center_h), run_time=1.2)
        center = center_h
        self.wait(2.1)

        # 7) [27.9 - 31.3] changing theta_j affects only theta_j x_j (no extra rectangle to keep <=3 objects)
        set_caption("Changing θ_j only changes the term  θ_j x_j", run_time=0.6)
        self.wait(2.3)

        # 8) [31.3 - 35.2] derivative is x_j
        set_caption("So  ∂h/∂θ_j  =  x_j", run_time=0.6)

        center_dh = MathTex(
            r"\frac{\partial h(\theta,x)}{\partial \theta_j}=x_j",
            color=WHITE,
            font_size=72,
            tex_template=tex_template,
        )
        self.play(ReplacementTransform(center, center_dh), run_time=1.0)
        center = center_dh
        self.wait(1.9)

        # 9) [35.2 - 39.8] final gradient
        set_caption("Final gradient: (h − y) x_j", run_time=0.6)

        center_final = MathTex(
            r"\frac{\partial}{\partial \theta_j}\left[\ \frac{1}{2}\,\big(h(\theta,x)-y\big)^2\ \right]"
            r"= \big(h(\theta,x)-y\big)\,x_j",
            color=WHITE,
            font_size=56,
            tex_template=tex_template,
        )
        self.play(ReplacementTransform(center, center_final), run_time=1.2)
        center = center_final
        self.wait(2.3)