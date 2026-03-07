"""
===========================================
Promotional Image Generator V5 (Configurable)
===========================================
All layout parameters can be overridden via a config dict.
The editor UI saves config via config_store (Supabase o archivo).
"""

import io
import json
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import config_store

BASE_DIR = Path(__file__).resolve().parent
LOGOS_DIR = BASE_DIR / "static" / "img" / "nba_logos"
FONTS_DIR = BASE_DIR / "static" / "fonts"
TEMPLATE_PATH = BASE_DIR / "static" / "img" / "promo_v3_template.png"
CONFIG_KEY = "promo_config"

# Montserrat font family
FONT_EXTRABOLD = FONTS_DIR / "Montserrat-ExtraBold.ttf"
FONT_BOLD = FONTS_DIR / "Montserrat-Bold.ttf"
FONT_SEMIBOLD = FONTS_DIR / "Montserrat-SemiBold.ttf"
FONT_MEDIUM = FONTS_DIR / "Montserrat-Medium.ttf"

# Default layout config
DEFAULTS = {
    "logo_cy": 240,
    "logo_left_cx": 88,
    "logo_right_offset": 88,
    "logo_max": 68,
    "names_y": 308,
    "names_font_size": 11,
    "names_max_w": 120,
    "names_color": "#373737",
    "box_y0": 405,
    "box_y1": 590,
    "box_pad_x": 28,
    "box_radius": 14,
    "box_border_w": 2,
    "box_border_color": "#beb9aa",
    "label_offset_y": 18,
    "label_font_size": 11,
    "label_color": "#9b968c",
    "winner_offset_y": 50,
    "winner_font_size": 20,
    "winner_color": "#0069e1",
    "prob_offset_y": 100,
    "prob_font_size": 52,
    "prob_color": "#1e1e1e",
    "footer_y": 642,
    "footer_font_size": 10,
    "footer_color": "#b9b4aa",
    # Visibility toggles
    "show_logos": True,
    "show_names": True,
    "show_box_border": True,
    "show_label": True,
    "show_winner": True,
    "show_prob": True,
    "show_footer": True,
}


def load_config() -> dict:
    """Load saved config (Supabase o archivo), falling back to defaults."""
    cfg = dict(DEFAULTS)
    saved = config_store.get(CONFIG_KEY, {})
    if saved:
        cfg.update(saved)
    return cfg


def save_config(cfg: dict):
    """Persist config (Supabase o archivo)."""
    config_store.set(CONFIG_KEY, cfg)


def _hex_to_rgba(hex_color: str) -> tuple:
    """Convert hex color string to RGBA tuple."""
    h = hex_color.lstrip("#")
    if len(h) == 6:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)
    return (0, 0, 0, 255)


def _bool(val) -> bool:
    """Convert value to bool, handling strings from query params."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes", "on")
    return bool(val)


def _font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    """Load font with fallback chain."""
    for candidate in [path, FONT_BOLD, FONT_SEMIBOLD, FONT_MEDIUM]:
        if candidate and candidate.exists():
            try:
                return ImageFont.truetype(str(candidate), size)
            except Exception:
                continue
    for sf in ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"]:
        if os.path.exists(sf):
            try:
                return ImageFont.truetype(sf, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _get_logo(team_name: str) -> Path:
    """Find team logo by name."""
    aliases = {
        "la clippers": "los angeles clippers",
        "clipper": "los angeles clippers",
        "la lakers": "los angeles lakers",
    }
    name = aliases.get(team_name.lower().strip(), team_name.lower().strip())
    path = LOGOS_DIR / f"{name.replace(' ', '_')}.png"
    if path.exists():
        return path
    for f in LOGOS_DIR.iterdir():
        if f.suffix.lower() == ".png":
            stem = f.stem.lower().replace("_", " ")
            if name in stem or stem in name:
                return f
    return None


def _text_center(draw, text, cx, y, font, color, max_w):
    """Draw centered text with word wrap. Returns end y."""
    words = text.split()
    lines, cur = [], ""
    for w in words:
        t = f"{cur} {w}".strip()
        tw = draw.textbbox((0, 0), t, font=font)[2] - draw.textbbox((0, 0), t, font=font)[0]
        if tw <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)

    lh = draw.textbbox((0, 0), "Ag", font=font)[3] - draw.textbbox((0, 0), "Ag", font=font)[1]
    cy = y
    for ln in lines:
        tw = draw.textbbox((0, 0), ln, font=font)[2] - draw.textbbox((0, 0), ln, font=font)[0]
        x = max(4, cx - tw // 2)
        draw.text((x, cy), ln, font=font, fill=color)
        cy += lh + 3
    return cy


def _paste_logo(img, logo_path, cx, cy, max_size):
    """Paste a logo centered at (cx, cy)."""
    if not logo_path:
        return
    logo = Image.open(logo_path).convert("RGBA")
    logo.thumbnail((max_size, max_size), Image.LANCZOS)
    px = max(0, min(cx - logo.width // 2, img.width - logo.width))
    py = max(0, min(cy - logo.height // 2, img.height - logo.height))
    img.alpha_composite(logo, (px, py))


def generate_promo_image(
    home_team: str,
    away_team: str,
    winner: str,
    probability: float,
    status: str = None,
    config_override: dict = None,
) -> bytes:
    """
    Generate a promotional card image.
    Uses saved config (promo_config.json) merged with any overrides.
    """
    # Merge config: defaults < saved file < runtime overrides
    cfg = load_config()
    if config_override:
        cfg.update(config_override)

    # Load template
    try:
        img = Image.open(TEMPLATE_PATH).convert("RGBA")
    except Exception:
        img = Image.new("RGBA", (371, 673), (255, 255, 255, 255))

    W, H = img.size
    CX = W // 2

    # ── LOGOS ─────────────────────────────────
    logo_cy = int(cfg["logo_cy"])
    logo_max = int(cfg["logo_max"])
    home_cx = int(cfg["logo_left_cx"])
    away_cx = W - int(cfg["logo_right_offset"])

    if _bool(cfg.get("show_logos", True)):
        _paste_logo(img, _get_logo(home_team), home_cx, logo_cy, logo_max)
        _paste_logo(img, _get_logo(away_team), away_cx, logo_cy, logo_max)

    d = ImageDraw.Draw(img)

    # ── TEAM NAMES ───────────────────────────
    if _bool(cfg.get("show_names", True)):
        names_color = _hex_to_rgba(cfg["names_color"])
        fn_name = _font(FONT_SEMIBOLD, int(cfg["names_font_size"]))
        names_max_w = int(cfg["names_max_w"])
        names_y = int(cfg["names_y"])
        _text_center(d, home_team, home_cx, names_y, fn_name, names_color, names_max_w)
        _text_center(d, away_team, away_cx, names_y, fn_name, names_color, names_max_w)

    # ── PREDICTION BOX ───────────────────────
    by0 = int(cfg["box_y0"])
    by1 = int(cfg["box_y1"])

    if _bool(cfg.get("show_box_border", True)):
        bx0 = int(cfg["box_pad_x"])
        bx1_x = W - bx0
        b_rad = int(cfg["box_radius"])
        b_w = int(cfg["box_border_w"])
        b_color = _hex_to_rgba(cfg["box_border_color"])
        d.rounded_rectangle([(bx0, by0), (bx1_x, by1)], radius=b_rad, outline=b_color, width=b_w)

    # Label
    if _bool(cfg.get("show_label", True)):
        label_color = _hex_to_rgba(cfg["label_color"])
        fn_label = _font(FONT_MEDIUM, int(cfg["label_font_size"]))
        _text_center(d, "A GANAR EL PARTIDO", CX, by0 + int(cfg["label_offset_y"]), fn_label, label_color, 280)

    # Winner
    if _bool(cfg.get("show_winner", True)):
        winner_color = _hex_to_rgba(cfg["winner_color"])
        fn_winner = _font(FONT_BOLD, int(cfg["winner_font_size"]))
        _text_center(d, winner, CX, by0 + int(cfg["winner_offset_y"]), fn_winner, winner_color, 280)

    # Probability
    if _bool(cfg.get("show_prob", True)):
        prob_color = _hex_to_rgba(cfg["prob_color"])
        fn_prob = _font(FONT_EXTRABOLD, int(cfg["prob_font_size"]))
        _text_center(d, f"{probability:.1f}%", CX, by0 + int(cfg["prob_offset_y"]), fn_prob, prob_color, 280)

    # ── FOOTER ───────────────────────────────
    if _bool(cfg.get("show_footer", True)):
        footer_color = _hex_to_rgba(cfg["footer_color"])
        fn_footer = _font(FONT_MEDIUM, int(cfg["footer_font_size"]))
        _text_center(d, "lafija.com", CX, int(cfg["footer_y"]), fn_footer, footer_color, W)

    # ── STATUS BADGE ─────────────────────────
    if status and status.upper() in ["GANADA", "PERDIDA"]:
        is_win = status.upper() == "GANADA"
        badge_color = (48, 209, 88) if is_win else (255, 69, 58)
        badge_text = "✅ ACERTADA" if is_win else "❌ FALLADA"
        bw_, bh_ = 170, 28
        bx0_ = CX - bw_ // 2
        by0_ = 6
        shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle(
            [(bx0_, by0_ + 3), (bx0_ + bw_, by0_ + bh_ + 3)], radius=8, fill=(0, 0, 0, 60)
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(4))
        img.alpha_composite(shadow)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle(
            [(bx0_, by0_), (bx0_ + bw_, by0_ + bh_)], radius=8, fill=badge_color
        )
        fn_badge = _font(FONT_BOLD, 11)
        _text_center(d, badge_text, CX, by0_ + 7, fn_badge, (255, 255, 255, 255), bw_ - 10)

    # ── OUTPUT ───────────────────────────────
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


if __name__ == "__main__":
    print("Generating test promo images...")
    data = generate_promo_image("Charlotte Hornets", "Dallas Mavericks", "Charlotte Hornets", 58.1)
    with open("static/img/test_promo_user_pending.png", "wb") as f:
        f.write(data)
    print("  ✓ test_promo_user_pending.png")

    data = generate_promo_image("Los Angeles Lakers", "Golden State Warriors", "Golden State Warriors", 64.2, "Ganada")
    with open("static/img/test_promo_user_won.png", "wb") as f:
        f.write(data)
    print("  ✓ test_promo_user_won.png")
    print("Done!")
