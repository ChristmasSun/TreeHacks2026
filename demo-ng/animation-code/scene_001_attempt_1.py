from manim import *
import numpy as np

class HousePriceScatter(Scene):
    def construct(self):
        self.camera.background_color = "#000000"

        # ----------------------------
        # Helpers (titles/captions)
        # ----------------------------
        title = Text("House price vs. size", font_size=44, weight=BOLD).to_edge(UP, buff=0.5)
        caption = Text("Predict price from size", font_size=30).to_edge(DOWN, buff=0.5)

        # [0.0 - 4.2] Intro idea
        self.play(Write(title), run_time=1.1)
        self.play(Write(caption), run_time=1.0)
        self.wait(2.1)  # total ~4.2

        # ----------------------------
        # Center element: Axes + dots + line (single VGroup)
        # ----------------------------
        axes = Axes(
            x_range=[500, 3500, 500],
            y_range=[100, 550, 100],
            x_length=10.2,
            y_length=5.6,
            tips=False,
            axis_config={"color": GREY_B, "stroke_width": 2},
        )

        x_label = Text("Size (sq ft)", font_size=28, color=GREY_A)
        y_label = Text("Price (thousands $)", font_size=28, color=GREY_A).rotate(PI / 2)

        x_label.next_to(axes, DOWN, buff=0.45)
        y_label.next_to(axes, LEFT, buff=0.6)

        # Portland-like sample points (size, price in $1000s)
        data = np.array([
            [650, 150], [820, 175], [900, 190], [1050, 205], [1150, 210],
            [1250, 235], [1300, 225], [1400, 250], [1500, 260], [1600, 275],
            [1700, 265], [1800, 290], [1900, 310], [2000, 295], [2100, 335],
            [2200, 325], [2350, 355], [2450, 360], [2600, 390], [2750, 410],
            [2900, 405], [3100, 455], [3300, 480],
        ], dtype=float)

        dots = VGroup(*[
            Dot(
                point=axes.c2p(x, y),
                radius=0.055,
                color=YELLOW
            )
            for x, y in data
        ])

        # Placeholder model line (empty straight line "sitting on top")
        # Start with a reasonable guess: y = 80 + 0.12 x (in these units)
        def model_y(x):
            return 80 + 0.12 * x

        x0, x1 = 600, 3400
        model_line = Line(
            axes.c2p(x0, model_y(x0)),
            axes.c2p(x1, model_y(x1)),
            color=BLUE_B,
            stroke_width=6,
        ).set_opacity(0.55)

        center_group = VGroup(axes, x_label, y_label, dots, model_line).move_to(ORIGIN)

        # [4.2 - 8.7] Collect dataset
        new_caption = Text("Collect real sales data", font_size=30).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption

        self.play(Create(axes), run_time=1.2)
        self.play(Write(x_label), run_time=0.7)
        self.play(Write(y_label), run_time=0.7)
        self.wait(1.3)  # brings us to ~8.7

        # [8.7 - 10.8] Portland examples
        new_caption = Text("Examples from Portland, Oregon", font_size=30).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption
        self.wait(1.5)  # to ~10.8

        # [11.4 - 14.0] Each dot is one house
        self.wait(0.6)  # gap from 10.8 to 11.4
        new_caption = Text("Each dot is one house", font_size=30).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.5)
        caption = new_caption

        self.play(LaggedStart(*[Create(d) for d in dots], lag_ratio=0.06, run_time=2.0))
        self.wait(0.1)  # to ~14.0

        # [14.7 - 18.0] Horizontal = size
        self.wait(0.7)
        new_caption = Text("Horizontal axis: size (square feet)", font_size=30).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.5)
        caption = new_caption

        x_axis_highlight = axes.get_x_axis().copy().set_color(WHITE).set_stroke(width=5)
        self.play(Create(x_axis_highlight), run_time=0.6)
        self.wait(1.2)
        self.play(FadeOut(x_axis_highlight), run_time=0.3)
        self.wait(0.5)  # to ~18.0

        # [18.0 - 21.8] Vertical = price
        new_caption = Text("Vertical axis: price (thousands of dollars)", font_size=30).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption

        y_axis_highlight = axes.get_y_axis().copy().set_color(WHITE).set_stroke(width=5)
        self.play(Create(y_axis_highlight), run_time=0.6)
        self.wait(1.6)
        self.play(FadeOut(y_axis_highlight), run_time=0.3)
        self.wait(0.1)  # to ~21.8

        # [21.8 - 25.0] Trend rises
        new_caption = Text("Bigger houses tend to cost more", font_size=30).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption

        rising_arrow = Arrow(
            start=axes.c2p(900, 170),
            end=axes.c2p(3000, 440),
            buff=0,
            color=GREEN,
            stroke_width=6,
            max_tip_length_to_length_ratio=0.15
        )
        self.play(Create(rising_arrow), run_time=0.8)
        self.wait(1.3)
        self.play(FadeOut(rising_arrow), run_time=0.5)  # to 25.0 total for this beat

        # [25.0 - 28.4] Not perfect (variation)
        new_caption = Text("...but not perfectly", font_size=30).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption

        # Briefly indicate a couple of off-trend points
        idx_hi = 12  # (1900, 310)
        idx_lo = 10  # (1700, 265)
        self.play(Indicate(dots[idx_hi], color=RED, scale_factor=1.4), run_time=0.7)
        self.play(Indicate(dots[idx_lo], color=RED, scale_factor=1.4), run_time=0.7)
        self.wait(0.4)  # to ~28.4

        # [30.0 - 33.8] Model-in-waiting line appears
        self.wait(1.6)  # gap 28.4 -> 30.0
        new_caption = Text("A straight-line model (not fit yet)", font_size=30).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption

        self.play(Create(model_line), run_time=1.1)
        self.wait(1.0)  # to ~33.8

        # [33.8 - 37.2] Linear trend guess
        new_caption = Text("Guess: price grows roughly linearly with size", font_size=30).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption
        self.wait(2.8)  # to ~37.2

        # [37.2 - 41.9] Slide and tilt to match
        new_caption = Text("Slide and tilt the line to best match the dots", font_size=30).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption

        # Animate: shift + rotate slightly, then settle
        pivot = model_line.get_center()
        self.play(
            model_line.animate.shift(0.35 * UP + 0.25 * RIGHT).rotate(-6 * DEGREES, about_point=pivot),
            run_time=1.4
        )
        self.play(
            model_line.animate.shift(0.25 * DOWN + 0.15 * LEFT).rotate(9 * DEGREES, about_point=pivot),
            run_time=1.4
        )
        self.play(
            model_line.animate.shift(0.08 * UP).rotate(-3 * DEGREES, about_point=pivot),
            run_time=0.9
        )
        self.wait(0.4)  # total to ~41.9