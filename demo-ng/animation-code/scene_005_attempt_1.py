from manim import *
import numpy as np

class DataTableScene(Scene):
    def construct(self):
        self.camera.background_color = "#000000"

        # ---------------------------
        # Persistent title + caption
        # ---------------------------
        title = Text("Training examples as a table", font_size=44, color=WHITE).to_edge(UP, buff=0.5)
        caption = Text(" ", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)

        self.play(Write(title), run_time=0.8)
        self.play(Write(caption), run_time=0.3)

        # ---------------------------
        # Center element: table (single center group)
        # ---------------------------
        # Make a small grid-like table
        rows = 5   # visualize "m"
        cols = 4   # visualize "n + y" with first col as index
        w = 7.2
        h = 3.6

        grid = Rectangle(width=w, height=h, color=GRAY_C, stroke_width=2)
        vlines = VGroup(*[
            Line(
                start=grid.get_top() + DOWN * (h) + RIGHT * (-w / 2 + k * (w / cols)),
                end=grid.get_top() + RIGHT * (-w / 2 + k * (w / cols)),
                color=GRAY_D,
                stroke_width=2
            )
            for k in range(1, cols)
        ])
        hlines = VGroup(*[
            Line(
                start=grid.get_left() + RIGHT * w + DOWN * (k * (h / rows)),
                end=grid.get_left() + DOWN * (k * (h / rows)),
                color=GRAY_D,
                stroke_width=2
            )
            for k in range(1, rows)
        ])

        table = VGroup(grid, vlines, hlines).move_to(ORIGIN)

        # Header labels inside the table (kept minimal)
        # Columns: i | x_1 ... | x_n | y
        header_y = grid.get_top()[1] - (h / rows) * 0.5
        col_centers = [
            grid.get_left() + RIGHT * (w / cols) * (0.5 + c) for c in range(cols)
        ]

        hdr_i = Text("i", font_size=30, color=YELLOW).move_to([col_centers[0][0], header_y, 0])
        hdr_x = Text("x (features)", font_size=28, color=BLUE_B).move_to([col_centers[1][0], header_y, 0])
        hdr_xn = Text("…", font_size=34, color=BLUE_B).move_to([col_centers[2][0], header_y, 0])
        hdr_y = Text("y", font_size=30, color=GREEN_B).move_to([col_centers[3][0], header_y, 0])

        headers = VGroup(hdr_i, hdr_x, hdr_xn, hdr_y)

        # Fill a few rows with minimal placeholders
        body = VGroup()
        for r in range(1, rows):
            cy = grid.get_top()[1] - (h / rows) * (r + 0.5)
            idx = Text(str(r), font_size=28, color=YELLOW).move_to([col_centers[0][0], cy, 0])
            x1 = MathTex(r"x_1^{(" + str(r) + r")}", font_size=30, color=BLUE_B).move_to([col_centers[1][0], cy, 0])
            xd = Text("…", font_size=34, color=BLUE_B).move_to([col_centers[2][0], cy, 0])
            yv = MathTex(r"y^{(" + str(r) + r")}", font_size=30, color=GREEN_B).move_to([col_centers[3][0], cy, 0])
            body.add(VGroup(idx, x1, xd, yv))

        center_group = VGroup(table, headers, body).scale(0.95)

        # Reveal the table gradually
        self.play(
            ReplacementTransform(caption, Text("In this little table, each row represents one training example,", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)),
            run_time=0.7
        )
        caption = self.mobjects[-1]

        self.play(Create(grid), run_time=0.9)
        self.play(LaggedStart(*[Create(m) for m in vlines], lag_ratio=0.12), run_time=0.8)
        self.play(LaggedStart(*[Create(m) for m in hlines], lag_ratio=0.12), run_time=0.8)
        self.play(Write(headers), run_time=0.8)

        # Let first beat sit until ~4.3s
        self.wait(0.3)

        # 4.3s - 6.2s: like a single house
        new_caption = Text("like a single house from our dataset.", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.5)
        caption = new_caption

        # Highlight one row briefly (a "single house")
        r_pick = body[2]  # third data row
        row_rect = SurroundingRectangle(r_pick, color=YELLOW, buff=0.15, stroke_width=3)
        self.play(Create(row_rect), run_time=0.5)
        self.wait(0.4)
        self.play(FadeOut(row_rect), run_time=0.3)
        self.wait(0.1)

        # 6.2s - 9.2s: total number of examples m
        new_caption = Text("We call the total number of examples m,", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.5)
        caption = new_caption

        # Show "m" as number of rows on the left side (annotation)
        # Keep annotation inside the same center group by adding it to the table group
        m_label = MathTex(r"m", font_size=44, color=YELLOW).next_to(grid, LEFT, buff=0.45)
        m_brace = Brace(grid, LEFT, color=YELLOW)
        m_group = VGroup(m_brace, m_label)

        self.play(Create(m_brace), run_time=0.5)
        self.play(Write(m_label), run_time=0.4)
        self.wait(0.6)

        # 9.2s - 12.2s: m is number of rows
        new_caption = Text("meaning m is just the number of rows you see here.", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption

        # Indicate the rows with a gentle emphasis
        self.play(Indicate(m_brace, color=YELLOW), run_time=0.8)
        self.wait(0.8)

        # 12.2s - 16.7s: i-th row, input features x^(i)
        new_caption = Text("For the i-th row, the input features are written as x superscript i,", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption

        # Focus on i column and feature entries for a chosen i
        i_val = 3
        row_i = body[i_val - 1]  # row index matches displayed numbers 1..4
        idx_cell = row_i[0]
        x_cell = row_i[1]

        idx_rect = SurroundingRectangle(idx_cell, color=YELLOW, buff=0.12, stroke_width=3)
        x_rect = SurroundingRectangle(x_cell, color=BLUE_B, buff=0.12, stroke_width=3)

        self.play(Create(idx_rect), run_time=0.4)
        self.play(Create(x_rect), run_time=0.4)

        # Show x^(i) as a compact symbol near the feature column
        x_sup = MathTex(r"x^{(i)}", font_size=44, color=BLUE_B).next_to(grid, DOWN, buff=0.5).shift(LEFT * 1.2)
        self.play(Write(x_sup), run_time=0.6)
        self.wait(0.5)
        self.play(FadeOut(idx_rect), FadeOut(x_rect), run_time=0.4)

        # 16.7s - 20.6s: corresponding output y^(i)
        new_caption = Text("and the corresponding output is y superscript i.", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption

        y_cell = row_i[3]
        y_rect = SurroundingRectangle(y_cell, color=GREEN_B, buff=0.12, stroke_width=3)
        self.play(Create(y_rect), run_time=0.4)

        y_sup = MathTex(r"y^{(i)}", font_size=44, color=GREEN_B).next_to(x_sup, RIGHT, buff=0.8)
        self.play(Write(y_sup), run_time=0.6)
        self.wait(0.5)
        self.play(FadeOut(y_rect), run_time=0.3)

        # 20.6s - 23.6s: y is the target variable
        new_caption = Text("That y value is the target variable,", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption

        y_header_rect = SurroundingRectangle(hdr_y, color=GREEN_B, buff=0.15, stroke_width=3)
        self.play(Create(y_header_rect), run_time=0.5)
        self.wait(0.6)
        self.play(FadeOut(y_header_rect), run_time=0.3)

        # 23.6s - 25.2s: thing we're trying to predict
        new_caption = Text("the thing we're trying to predict.", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.5)
        caption = new_caption
        self.play(Indicate(hdr_y, color=GREEN_B), run_time=0.7)
        self.wait(0.2)

        # 25.2s - 29.0s: (x, y) forms one complete example
        new_caption = Text("Put together, x comma y forms one complete example,", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption

        # Replace the x^(i), y^(i) pair with a single (x, y) example notation
        xy_example = MathTex(r"(x,\;y)", font_size=48, color=WHITE).move_to(VGroup(x_sup, y_sup).get_center())
        self.play(ReplacementTransform(VGroup(x_sup, y_sup), xy_example), run_time=0.8)
        self.wait(0.8)

        # 29.0s - 34.1s: x^(i), y^(i) pinpoints the i-th example
        new_caption = Text("and x superscript i with y superscript i pinpoints the i-th example precisely.", font_size=30, color=GRAY_A).to_edge(DOWN, buff=0.5)
        self.play(ReplacementTransform(caption, new_caption), run_time=0.6)
        caption = new_caption

        # Transform (x,y) into (x^(i), y^(i)) and re-highlight the selected row
        xy_i = MathTex(r"\left(x^{(i)},\;y^{(i)}\right)", font_size=48, color=WHITE).move_to(xy_example)
        self.play(TransformMatchingTex(xy_example, xy_i), run_time=0.9)

        row_focus = SurroundingRectangle(row_i, color=YELLOW, buff=0.15, stroke_width=3)
        self.play(Create(row_focus), run_time=0.6)
        self.wait(1.5)
        self.play(FadeOut(row_focus), run_time=0.4)

        # Add n (number of features) briefly near the feature columns, then remove (within 1-2 beats)
        n_brace = Brace(VGroup(hdr_x, hdr_xn), UP, color=BLUE_B)
        n_label = MathTex(r"n", font_size=40, color=BLUE_B).next_to(n_brace, UP, buff=0.25)
        self.play(Create(n_brace), Write(n_label), run_time=0.7)
        self.wait(0.6)
        self.play(FadeOut(n_brace), FadeOut(n_label), run_time=0.4)

        # End padding to land near 34.1s total
        self.wait(0.3)