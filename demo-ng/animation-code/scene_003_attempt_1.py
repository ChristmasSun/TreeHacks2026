from manim import *

class HypothesisRepresentation(Scene):
    def construct(self):
        self.camera.background_color = "#000000"

        title = Text("Linear regression hypothesis", font_size=44, color=WHITE).to_edge(UP, buff=0.5)
        caption = Text(" ", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)

        self.play(Write(title), run_time=1.0)
        self.play(Write(caption), run_time=0.3)
        self.wait(0.6)  # ~1.9s

        # 1.9s - 5.5s
        new_caption = Text("Choose a hypothesis: a function that makes predictions.", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.8)
        caption = new_caption
        self.wait(2.0)

        # 5.5s - 8.1s
        new_caption = Text("It maps inputs to an output.", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption
        self.wait(1.9)

        # 8.1s - 11.6s
        new_caption = Text("In linear regression, we keep it simple.", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption
        self.wait(2.3)

        # 11.6s - 15.2s
        new_caption = Text("Predict as a linear function of the inputs.", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption
        self.wait(2.4)

        # 15.2s - 23.0s: show single-feature hypothesis
        eq1 = MathTex(r"h(x)=\theta_0+\theta_1 x", font_size=72, color=WHITE)
        self.play(Write(eq1), run_time=1.2)
        self.wait(6.6)

        # 23.0s - 27.8s: highlight theta0 and theta1 meaning, briefly (no extra lingering objects)
        new_caption = Text(r"θ0 is the offset; θ1 controls the slope.", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption

        box0 = SurroundingRectangle(eq1[0][5:8], color=YELLOW, buff=0.12)  # \theta_0
        box1 = SurroundingRectangle(eq1[0][9:12], color=BLUE, buff=0.12)   # \theta_1
        self.play(Create(box0), run_time=0.4)
        self.wait(0.7)
        self.play(ReplacementTransform(box0, box1), run_time=0.5)
        self.wait(0.7)
        self.play(FadeOut(box1), run_time=0.4)
        self.wait(1.9)

        # 27.8s - 32.1s
        new_caption = Text("Real problems often have more than one measurement.", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption
        self.wait(3.1)

        # 32.1s - 35.6s
        new_caption = Text("Example: house prices use size and bedrooms.", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption
        self.wait(2.9)

        # 35.6s - 38.0s: label features (replace center equation with a simple labeled pair)
        self.play(FadeOut(eq1), run_time=0.6)

        feats = VGroup(
            MathTex(r"x_1", font_size=80, color=YELLOW),
            Text("size", font_size=34, color=GRAY_C),
            MathTex(r"x_2", font_size=80, color=GREEN),
            Text("bedrooms", font_size=34, color=GRAY_C),
        )
        # Arrange as two columns: (x1 over size) and (x2 over bedrooms)
        col1 = VGroup(feats[0], feats[1]).arrange(DOWN, buff=0.25)
        col2 = VGroup(feats[2], feats[3]).arrange(DOWN, buff=0.25)
        feat_group = VGroup(col1, col2).arrange(RIGHT, buff=1.2).move_to(ORIGIN)

        new_caption = Text("Label them x1 and x2.", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.5)
        caption = new_caption

        self.play(Write(feat_group), run_time=1.0)
        self.wait(0.9)

        # 38.0s - 46.2s: extend to multi-feature hypothesis
        self.play(FadeOut(feat_group), run_time=0.5)

        eq2 = MathTex(r"h(x)=\theta_0+\theta_1 x_1+\theta_2 x_2", font_size=66, color=WHITE)
        self.play(Write(eq2), run_time=1.2)

        new_caption = Text("Extend the hypothesis by adding weighted features.", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption

        self.wait(5.9)

        # 46.2s - 49.0s: each theta weights its feature’s influence (brief highlights)
        new_caption = Text("Each θ weights its feature’s influence.", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.5)
        caption = new_caption

        box_theta1 = SurroundingRectangle(eq2[0][9:12], color=BLUE, buff=0.12)   # \theta_1
        box_x1 = SurroundingRectangle(eq2[0][13:16], color=YELLOW, buff=0.12)    # x_1
        box_theta2 = SurroundingRectangle(eq2[0][17:20], color=TEAL, buff=0.12)  # \theta_2
        box_x2 = SurroundingRectangle(eq2[0][21:24], color=GREEN, buff=0.12)     # x_2

        self.play(Create(box_theta1), run_time=0.35)
        self.play(ReplacementTransform(box_theta1, box_x1), run_time=0.35)
        self.play(ReplacementTransform(box_x1, box_theta2), run_time=0.35)
        self.play(ReplacementTransform(box_theta2, box_x2), run_time=0.35)
        self.play(FadeOut(box_x2), run_time=0.3)
        self.wait(0.5)