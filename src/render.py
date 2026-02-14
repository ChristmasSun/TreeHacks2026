import os
import re
import sys
import shutil
import asyncio
import tempfile

LATEX_AVAILABLE = shutil.which("latex") is not None


def inject_math_shims(code: str) -> str:
    """Injects safe shims for MathTex and Tex that use Text under the hood."""
    shim_code = """\
# --- MATH SHIMS ---
class MathTex(VGroup):
    def __init__(self, *args, **kwargs):
        super().__init__()
        font_size = kwargs.get("font_size", 48)
        color = kwargs.get("color", WHITE)
        text_kwargs = {k:v for k,v in kwargs.items() if k in ['font', 'slant', 'weight', 'lsh', 'gradient', 't2c', 't2f', 't2g', 't2s', 't2w', 'disable_ligatures']}
        text_kwargs['font_size'] = font_size
        text_kwargs['color'] = color
        for arg in args:
            if isinstance(arg, str):
                self.add(Text(arg, **text_kwargs))
        self.arrange(RIGHT, buff=0.1)

class Tex(MathTex):
    pass
# ------------------
"""
    if "from manim import *" in code:
        return code.replace("from manim import *", "from manim import *\n" + shim_code)
    else:
        return "from manim import *\n" + shim_code + "\n" + code


def normalize_latex_markup(code: str) -> str:
    """Converts common LaTeX markup into unicode/plain text for Text() labels."""
    def strip_wrapper(pattern, text):
        return re.sub(pattern, lambda m: m.group(1), text)

    original_code = code
    wrappers = [
        r"\\textbf\{([^{}]+)\}",
        r"\\textit\{([^{}]+)\}",
        r"\\mathbf\{([^{}]+)\}",
        r"\\mathit\{([^{}]+)\}",
        r"\\text\{([^{}]+)\}",
    ]
    for pattern in wrappers:
        code = strip_wrapper(pattern, code)

    replacements = {
        r"\\alpha": "\u03b1", r"\\beta": "\u03b2", r"\\gamma": "\u03b3",
        r"\\delta": "\u03b4", r"\\theta": "\u03b8", r"\\lambda": "\u03bb",
        r"\\mu": "\u03bc", r"\\pi": "\u03c0", r"\\sigma": "\u03c3",
        r"\\phi": "\u03c6", r"\\psi": "\u03c8", r"\\omega": "\u03c9",
        r"\\cdot": "\u00b7", r"\\times": "\u00d7",
        r"\\rightarrow": "\u2192", r"\\leftarrow": "\u2190",
        r"\\approx": "\u2248", r"\\leq": "\u2264",
        r"\\geq": "\u2265", r"\\neq": "\u2260",
    }
    for needle, replacement in replacements.items():
        code = code.replace(needle, replacement)

    code = code.replace(r"\{", "{").replace(r"\}", "}")
    return code


def normalize_mobject_accessors(code: str) -> str:
    """Replaces deprecated geometric helper calls with supported get_corner usage."""
    replacements = {
        ".get_bottom_left()": ".get_corner(DL)",
        ".get_bottom_right()": ".get_corner(DR)",
        ".get_top_left()": ".get_corner(UL)",
        ".get_top_right()": ".get_corner(UR)",
        ".get_center_point()": ".get_center()",
    }
    for old, new in replacements.items():
        code = code.replace(old, new)
    return code


def ensure_rate_functions_usage(code: str) -> str:
    """Ensures custom easing functions use rate_functions namespace."""
    needs_import = False

    def replace_ease(match):
        nonlocal needs_import
        needs_import = True
        return f"rate_functions.{match.group(0)}"

    code = re.sub(r"(?<!rate_functions\.)\bease_[a-z0-9_]+\b", replace_ease, code)

    if needs_import and "from manim.utils import rate_functions" not in code:
        lines = code.splitlines()
        insert_idx = 0
        for idx, line in enumerate(lines):
            if line.strip().startswith("from manim import *"):
                insert_idx = idx + 1
                break
        lines.insert(insert_idx, "from manim.utils import rate_functions")
        code = "\n".join(lines)

    return code


def fix_spacing_issues(code: str) -> str:
    """Automatically fixes common spacing/overlap issues in generated code."""
    def ensure_buff(pattern, default_buff):
        def replacer(match):
            if "buff=" not in match.group(0):
                return match.group(0).rstrip(")") + f", buff={default_buff})"
            return match.group(0)
        return lambda c: re.sub(pattern, replacer, c)

    code = ensure_buff(r"\.next_to\([^)]+\)", 0.5)(code)
    code = ensure_buff(r"\.arrange\([^)]+\)", 0.4)(code)
    code = ensure_buff(r"\.to_edge\([^)]+\)", 0.5)(code)
    return code


def sanitize_code(code: str) -> str:
    """Aggressively sanitizes the AI's code output."""
    # Extract from markdown block if present
    match = re.search(r"```python\n(.*?)\n```", code, re.DOTALL)
    if match:
        code = match.group(1).strip()

    if "from manim import *" not in code:
        code = "from manim import *\n\n" + code

    if LATEX_AVAILABLE:
        pass  # preserve native MathTex
    else:
        code = normalize_latex_markup(code)
        code = inject_math_shims(code)

    code = normalize_mobject_accessors(code)
    code = ensure_rate_functions_usage(code)
    code = fix_spacing_issues(code)
    return code


async def render_manim_code(code: str, output_dir: str, file_name: str) -> tuple[str | None, str | None]:
    """Renders a single Manim scene. Returns (video_path, error_message)."""
    class_name = "Scene"
    for line in code.split("\n"):
        if line.strip().startswith("class ") and "Scene" in line:
            class_name = line.split("class ")[1].split("(")[0].strip()
            break

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as temp_file:
        temp_file.write(code)
        temp_file_path = temp_file.name

    try:
        cmd = [
            sys.executable, "-m", "manim",
            temp_file_path, class_name,
            "-o", file_name,
            "--media_dir", output_dir,
            "-v", "WARNING",
            "-ql",
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        stdout_text = stdout.decode("utf-8") if stdout else ""
        stderr_text = stderr.decode("utf-8") if stderr else ""

        if process.returncode != 0:
            return None, f"--- MANIM STDOUT ---\n{stdout_text}\n\n--- MANIM STDERR ---\n{stderr_text}"

        for root, dirs, files in os.walk(output_dir):
            if file_name in files and "partial_movie_files" not in root:
                return os.path.join(root, file_name), None

        return None, "Could not find the rendered video file after a successful render."
    finally:
        os.unlink(temp_file_path)
