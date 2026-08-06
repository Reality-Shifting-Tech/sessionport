"""Generate README images for sessionport (docs/images/).

- architecture.png: dark-theme system diagram with the five agent logos.
- workflow.png: terminal window showing the export -> brief -> import loop.

Run: uv run python docs/make_images.py  (needs the dev extra: pillow)
"""

from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = os.path.join(os.path.dirname(__file__), "images")
AGENTS_DIR = os.path.join(OUT_DIR, "agents")
os.makedirs(OUT_DIR, exist_ok=True)

BG = (13, 17, 23)  # GitHub dark canvas
WIN_BG = (22, 27, 34)  # window background
BORDER = (48, 54, 61)  # subtle border
TEXT = (230, 237, 243)  # primary text
DIM = (139, 148, 158)  # secondary text
ACCENT = (6, 182, 212)  # RST signal cyan
ACID = (231, 255, 2)  # RST acid yellow
GREEN = (63, 185, 80)

AGENTS = [
    "claude-code",
    "codex",
    "opencode",
    "gemini",
    "hermes",
    "cursor",
    "aider",
    "windsurf",
    "openclaw",
    "cline",
    "goose",
    "kilo",
    "junie",
    "grok",
    "copilot",
    "vibe",
]
FONT_CANDIDATES = [
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Supplemental/Menlo.ttc",
    "/Library/Fonts/Menlo.ttc",
]


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, size, index=0)
    raise FileNotFoundError("no Menlo font found")


def agent_logo(name: str, size: int) -> Image.Image:
    """The official agent logo in a circular crop (full fit for wide logos)."""
    path = os.path.join(AGENTS_DIR, f"{name}.png")
    img = Image.open(path).convert("RGBA")
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    aspect = img.width / img.height
    if aspect < 0.6:
        # Wide logo (wordmark/banner): scale to fit inside, no circular mask.
        img.thumbnail((size, size), Image.LANCZOS)
        canvas.paste(img, ((size - img.width) // 2, (size - img.height) // 2), img)
        return canvas
    img.thumbnail((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, size, size), fill=255)
    canvas.paste(img, ((size - img.width) // 2, (size - img.height) // 2), img)
    canvas.putalpha(mask)
    return canvas


def rrect(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int, **kw) -> None:
    draw.rounded_rectangle(box, radius=radius, **kw)


def rounded_box(d: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], r: int = 10) -> None:
    rrect(d, xy, r, fill=WIN_BG, outline=BORDER, width=1)


def arrow(
    d: ImageDraw.ImageDraw,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    color=ACCENT,
    width=3,
) -> None:
    import math

    d.line([(x1, y1), (x2, y2)], fill=color, width=width)
    ang = math.atan2(y2 - y1, x2 - x1)
    length = 12
    for off in (0.35, -0.35):
        d.line(
            [(x2, y2), (x2 - length * math.cos(ang - off), y2 - length * math.sin(ang - off))],
            fill=color,
            width=width,
        )


def draw_text_center(d: ImageDraw.ImageDraw, cx: int, cy: int, text: str, font, fill=TEXT) -> None:
    bbox = d.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    d.text((cx - w / 2, cy - h / 2), text, font=font, fill=fill)


def make_architecture() -> str:
    """Dark diagram: agents -> sess export -> brief -> sess import -> agents."""
    W, H = 1600, 1060
    canvas = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(canvas)
    bold = load_font(30)
    small = load_font(18)
    tiny = load_font(14)

    d.text((60, 40), "sessionport architecture", font=bold, fill=TEXT)
    d.text((60, 84), "portable agent sessions · open format · one command", font=small, fill=DIM)

    logo_size = 72
    gap = 34
    start_x = 70
    per_row = 8
    row_step = 118

    def draw_agents(d, y: int, label: str) -> None:
        d.text((start_x, y - 40), label, font=small, fill=DIM)
        for i, name in enumerate(AGENTS[:per_row]):
            x = start_x + i * (logo_size + gap)
            canvas.paste(agent_logo(name, logo_size), (x, y), agent_logo(name, logo_size))
            d.text((x, y + logo_size + 8), name, font=tiny, fill=DIM)
        for i, name in enumerate(AGENTS[per_row:]):
            x = start_x + i * (logo_size + gap)
            y2 = y + row_step
            canvas.paste(agent_logo(name, logo_size), (x, y2), agent_logo(name, logo_size))
            d.text((x, y2 + logo_size + 8), name, font=tiny, fill=DIM)

    draw_agents(d, 190, "sources")

    # export box
    bw, bh = 320, 140
    box1 = (700, 170, 700 + bw, 170 + bh)
    rounded_box(d, box1, 16)
    draw_text_center(d, box1[0] + bw // 2, box1[1] + 45, "sessionport export", bold, TEXT)
    draw_text_center(d, box1[0] + bw // 2, box1[1] + 85, "extract durable state", small, DIM)
    draw_text_center(d, box1[0] + bw // 2, box1[1] + 108, "offline · deterministic", small, GREEN)

    # brief box
    box2 = (1120, 170, 1120 + bw, 170 + bh)
    rounded_box(d, box2, 16)
    draw_text_center(d, box2[0] + bw // 2, box2[1] + 40, "brief.md", bold, ACID)
    draw_text_center(d, box2[0] + bw // 2, box2[1] + 76, "sessionport-brief/v1", small, DIM)
    draw_text_center(d, box2[0] + bw // 2, box2[1] + 100, "markdown · human-readable", small, DIM)

    last_x = start_x + (per_row - 1) * (logo_size + gap)
    last_y = 190 + row_step + logo_size // 2
    arrow(d, last_x, last_y, box1[0], box1[1] + 60)
    arrow(d, box1[0] + bw, box1[1] + 70, box2[0], box2[1] + 70)

    # import row
    y2 = 560
    box3 = (700, y2, 700 + bw, y2 + bh)
    rounded_box(d, box3, 16)
    draw_text_center(d, box3[0] + bw // 2, box3[1] + 45, "sessionport import", bold, TEXT)
    draw_text_center(d, box3[0] + bw // 2, box3[1] + 85, "resume prompt", small, DIM)
    draw_text_center(d, box3[0] + bw // 2, box3[1] + 108, "any target agent", small, GREEN)

    draw_agents(d, 580, "targets")

    arrow(d, box2[0] + 40, box2[1] + bh - 10, box3[0] + 60, box3[1])
    arrow(d, box3[0] + bw, box3[1] + 70, last_x, 580 + row_step + logo_size // 2)

    # fidelity scorer (optional)
    box4 = (1120, 560, 1120 + 440, 560 + 100)
    rounded_box(d, box4, 14)
    draw_text_center(d, box4[0] + 220, box4[1] + 35, "sessionport score (optional)", bold, TEXT)
    draw_text_center(
        d, box4[0] + 220, box4[1] + 70, "LLM fidelity check: what did the brief lose?", small, DIM
    )
    arrow(d, box2[0] + 80, box2[1] + bh - 10, box4[0] + 220, box4[1])

    d.text(
        (60, 1000),
        "Default path is fully offline. The judge runs only when you call "
        "sessionport score with a key.",
        font=small,
        fill=DIM,
    )

    path = os.path.join(OUT_DIR, "architecture.png")
    canvas.save(path)
    return path


def make_workflow() -> str:
    """Terminal window showing the full export -> brief -> import loop."""
    lines = [
        ("$", "relay list"),
        ("o", "claude-code  9f9f9f9f-1111-2222-3  4 msgs  Fix the auth bug in login.py"),
        ("o", "codex        session-xyz           3 msgs  Add a health endpoint to the API"),
        ("$", "relay export claude-code:9f9f9f9f"),
        ("o", "wrote brief-claude-code-9f9f9f9f.md (4 messages, ~121 tokens)"),
        ("$", "cat brief-claude-code-9f9f9f9f.md"),
        ("o", "---"),
        ("o", "format: sessionport-brief/v1"),
        ("o", "## Decisions"),
        ("o", "- switch to httpOnly secure cookies"),
        ("o", "## State: files"),
        ("o", "- login.py, tests/test_session.py"),
        ("$", "relay import brief-claude-code-9f9f9f9f.md --into codex"),
        ("o", "Resume from a relay brief."),
        ("o", "Continue the work: do not re-litigate settled decisions."),
    ]
    font = load_font(22)
    bold = load_font(22)
    small = load_font(13)

    pad_x, pad_y = 48, 44
    line_h = 32
    title_h = 56
    body_h = len(lines) * line_h + pad_y * 2
    win_w = 1180
    win_h = title_h + body_h
    canvas = Image.new("RGB", (win_w + 2 * pad_x, win_h + 2 * pad_y), BG)
    d = ImageDraw.Draw(canvas)
    x0, y0 = pad_x, pad_y
    rrect(d, (x0, y0, x0 + win_w, y0 + win_h), 14, fill=WIN_BG, outline=BORDER, width=1)

    lx = x0 + 24
    ly = y0 + 24
    for col in ((255, 95, 87), (254, 188, 46), GREEN):
        d.ellipse((lx, ly, lx + 14, ly + 14), fill=col)
        lx += 22
    d.text((lx + 14, ly - 3), "zsh — relay", font=small, fill=DIM)

    ty = y0 + title_h
    for kind, text in lines:
        if kind == "$":
            d.text((x0 + 28, ty), "$ ", font=bold, fill=GREEN)
            d.text((x0 + 28 + 44, ty), text, font=font, fill=TEXT)
        else:
            d.text((x0 + 28 + 44, ty), text, font=font, fill=TEXT)
        ty += line_h

    path = os.path.join(OUT_DIR, "workflow.png")
    canvas.save(path)
    return path


if __name__ == "__main__":
    print("wrote", make_architecture())
    print("wrote", make_workflow())
