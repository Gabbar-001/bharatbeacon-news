import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from datetime import datetime

sys.path.append(str(Path(__file__).resolve().parent.parent))
import config

MASTER_LANDSCAPE_PATH = config.ASSETS_DIR / "templates" / "bharatbeacon_master_landscape.png"
MASTER_916_PATH = config.ASSETS_DIR / "templates" / "bharatbeacon_master_916.png"

def get_font(size: int, bold: bool = True, impact: bool = False, italic: bool = False):
    local_impact = config.FONTS_DIR / "impact.ttf"
    local_segoe_b = config.FONTS_DIR / "segoeuib.ttf"
    local_arial_b = config.FONTS_DIR / "arialbd.ttf"

    if impact:
        font_file = str(local_impact) if local_impact.exists() else "C:/Windows/Fonts/impact.ttf"
    elif bold and italic:
        font_file = "C:/Windows/Fonts/segoeuiz.ttf"
    elif bold:
        font_file = str(local_segoe_b) if local_segoe_b.exists() else "C:/Windows/Fonts/segoeuib.ttf"
    elif italic:
        font_file = "C:/Windows/Fonts/segoeuii.ttf"
    else:
        font_file = "C:/Windows/Fonts/segoeui.ttf"

    if not os.path.exists(font_file):
        if local_arial_b.exists():
            font_file = str(local_arial_b)
        else:
            font_file = "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"
    try:
        return ImageFont.truetype(font_file, size)
    except Exception:
        return ImageFont.load_default()

def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw):
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if (bbox[2] - bbox[0]) <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
    return lines

def create_gradient_bg(width: int, height: int, top_color, bottom_color):
    base = Image.new("RGBA", (width, height), top_color)
    top = Image.new("RGBA", (width, height), bottom_color)
    mask = Image.linear_gradient("L")
    mask = mask.resize((width, height))
    return Image.composite(top, base, mask)

def extract_topic_line(story: dict) -> tuple:
    """
    Extracts a high-impact, professional 2-tier broadcast pillar
    distinct from the headline to eliminate context overlap.
    """
    cat = story.get("category", "UPDATE").upper()
    
    top_line = "⚡ SPECIAL INVESTIGATION"
    
    cat_map = {
        "MYSTERY": "ARCHAEOLOGICAL MYSTERY",
        "DISCOVERY": "GLOBAL DISCOVERY",
        "SPACE": "DEEP SPACE & COSMOS",
        "TECH": "ADVANCED TECHNOLOGY",
        "EARTH": "EARTH & CLIMATE",
        "OCEAN": "DEEP OCEAN FRONTIER",
        "ASTRONOMY": "DEEP ASTRONOMY",
        "COSMOS": "PLANETARY DEFENCE",
        "PLANETARY": "PLANETARY SCIENCE",
        "TELESCOPE": "OBSERVATORY REPORT",
        "NATIONAL": "NATIONAL SPOTLIGHT",
        "WORLD": "WORLD AFFAIRS",
        "SCIENCE": "SCIENTIFIC BREAKTHROUGH"
    }
    bot_line = cat_map.get(cat, f"{cat} SPOTLIGHT")
    return top_line, bot_line

def generate_shorts_slide(story: dict, index: int, total: int, output_path: Path):
    """
    Renders 9:16 (1080x1920) Shorts slide with the native BharatBeacon template:
    - Real news image inserted into golden frame (62, 706, 1018, 1180).
    - Broadcast pillar + Domain in place of BREAKING NEWS (zero headline redundancy).
    - Full headline wrapped cleanly inside yellow brush banner (y: 1210 to 1455).
    - Subtitle ticker bar left clean for live synchronized captions.
    """
    W, H = config.SHORTS_WIDTH, config.SHORTS_HEIGHT
    
    if not MASTER_916_PATH.exists():
        img = create_gradient_bg(W, H, (10, 15, 30, 255), (18, 24, 38, 255))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, "PNG")
        return str(output_path)

    master = Image.open(MASTER_916_PATH).convert("RGBA")
    if master.size != (W, H):
        master = master.resize((W, H), Image.Resampling.LANCZOS)
        
    canvas = Image.new("RGBA", (W, H), (10, 8, 22, 255))
    
    # 1. Golden Frame Image: (62, 706, 1018, 1180) -> width 956, height 474
    fx0, fy0, fx1, fy1 = 62, 706, 1018, 1180
    box_w = fx1 - fx0
    box_h = fy1 - fy0
    
    story_img = None
    if story.get("local_image") and os.path.exists(story["local_image"]):
        try:
            raw = Image.open(story["local_image"]).convert("RGBA")
            img_aspect = raw.width / raw.height
            box_aspect = box_w / box_h
            if img_aspect > box_aspect:
                nh = box_h
                nw = int(nh * img_aspect)
            else:
                nw = box_w
                nh = int(nw / img_aspect)
            resized = raw.resize((nw, nh), Image.Resampling.LANCZOS)
            cx = (nw - box_w) // 2
            cy = (nh - box_h) // 2
            story_img = resized.crop((cx, cy, cx + box_w, cy + box_h))
        except Exception as e:
            print(f"[!] Error loading story image for shorts 9:16: {e}")

    if not story_img:
        story_img = create_gradient_bg(box_w, box_h, (25, 45, 85, 255), (12, 18, 38, 255))
        d_sub = ImageDraw.Draw(story_img)
        f_cat = get_font(48, bold=True, impact=True)
        cat_str = f"⚡ {story.get('category', 'BREAKING')}"
        d_sub.text((box_w // 2, box_h // 2), cat_str, font=f_cat, fill=(255, 215, 0), anchor="mm")

    # Paste photo on base canvas
    canvas.paste(story_img, (fx0, fy0))
    
    # 2. Overlay Master 9:16 Broadcast Graphic
    canvas.paste(master, (0, 0), mask=master)
    
    draw = ImageDraw.Draw(canvas)
    
    # 3. Topic Line In Place of BREAKING NEWS (y: 400 to 665)
    top_line, bot_line = extract_topic_line(story)
    
    # Top 3D Block (Blue background, center ~ 455)
    f_topic_top = get_font(44, bold=True, impact=True)
    bbox_t = draw.textbbox((0, 0), top_line, font=f_topic_top)
    lw_t = bbox_t[2] - bbox_t[0]
    draw.text((540 - lw_t // 2, 432), top_line, fill=(255, 255, 255), font=f_topic_top)
    
    # Bottom 3D Block (Red background, center ~ 585)
    f_topic_bot = get_font(56, bold=True, impact=True)
    bbox_b = draw.textbbox((0, 0), bot_line, font=f_topic_bot)
    lw_b = bbox_b[2] - bbox_b[0]
    if lw_b > 740:
        f_topic_bot = get_font(46, bold=True, impact=True)
        bbox_b = draw.textbbox((0, 0), bot_line, font=f_topic_bot)
        lw_b = bbox_b[2] - bbox_b[0]
    draw.text((540 - lw_b // 2, 552), bot_line, fill=(255, 255, 255), font=f_topic_bot)

    # 4. Headline on Yellow Brush Banner (y: 1210 to 1455, height: 245)
    headline_text = story.get("title", "").strip().upper()
    f_head = get_font(40, bold=True, impact=True)
    wrapped = wrap_text(headline_text, f_head, 840, draw)
    if len(wrapped) > 3:
        f_head = get_font(34, bold=True, impact=True)
        wrapped = wrap_text(headline_text, f_head, 840, draw)
        
    line_h = 44 if f_head.size < 38 else 50
    total_h = len(wrapped[:4]) * line_h
    start_y = 1210 + (245 - total_h) // 2
    for i, line in enumerate(wrapped[:4]):
        bbox_l = draw.textbbox((0, 0), line, font=f_head)
        lw_l = bbox_l[2] - bbox_l[0]
        draw.text((540 - lw_l // 2, start_y + i * line_h), line, fill=(10, 10, 15), font=f_head)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, "PNG")
    return str(output_path)

def generate_longform_slide(story: dict, index: int, total: int, output_path: Path):
    """
    Renders 16:9 (1920x1080) Full Video slide using the BharatBeacon broadcast template:
    - Real news image inserted into right golden frame (848, 229, 1884, 733).
    - Dynamic 2-tier headline on Yellow (black text) and Red (white text) 3D banners.
    - Top right red badge with domain indicator (zero overlap on clock or video).
    - Subtitle ticker bar left clean for live audio-synced captions.
    """
    W, H = config.LONGFORM_WIDTH, config.LONGFORM_HEIGHT
    
    if not MASTER_LANDSCAPE_PATH.exists():
        img = create_gradient_bg(W, H, (10, 15, 30, 255), (18, 26, 45, 255))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, "PNG")
        return str(output_path)

    master = Image.open(MASTER_LANDSCAPE_PATH).convert("RGBA")
    if master.size != (W, H):
        master = master.resize((W, H), Image.Resampling.LANCZOS)
        
    canvas = Image.new("RGBA", (W, H), (10, 8, 22, 255))
    
    # 1. Right Golden Frame Image: (fx0, fy0, fx1, fy1) = (848, 229, 1884, 733)
    fx0, fy0, fx1, fy1 = 848, 229, 1884, 733
    box_w = fx1 - fx0
    box_h = fy1 - fy0
    
    story_img = None
    if story.get("local_image") and os.path.exists(story["local_image"]):
        try:
            raw = Image.open(story["local_image"]).convert("RGBA")
            img_aspect = raw.width / raw.height
            box_aspect = box_w / box_h
            if img_aspect > box_aspect:
                nh = box_h
                nw = int(nh * img_aspect)
            else:
                nw = box_w
                nh = int(nw / img_aspect)
            resized = raw.resize((nw, nh), Image.Resampling.LANCZOS)
            cx = (nw - box_w) // 2
            cy = (nh - box_h) // 2
            story_img = resized.crop((cx, cy, cx + box_w, cy + box_h))
        except Exception as e:
            print(f"[!] Error loading story image for longform: {e}")

    if not story_img:
        story_img = create_gradient_bg(box_w, box_h, (25, 45, 85, 255), (12, 18, 38, 255))
        d_sub = ImageDraw.Draw(story_img)
        f_cat = get_font(48, bold=True, impact=True)
        cat_str = f"⚡ {story.get('category', 'BREAKING')}"
        d_sub.text((box_w // 2, box_h // 2), cat_str, font=f_cat, fill=(255, 215, 0), anchor="mm")

    # Paste photo on base canvas
    canvas.paste(story_img, (fx0, fy0))
    
    # 2. Overlay Master Broadcast Graphic
    canvas.paste(master, (0, 0), mask=master)
    
    draw = ImageDraw.Draw(canvas)
    
    # 3. Dynamic Headline on Yellow & Red 3D Banners
    title = story.get("title", "").strip().upper()
    words = title.split()
    
    if len(words) <= 4:
        line1 = title
        line2 = f"STORY #{index} SPECIAL REPORT" if index > 0 else "LIVE HOURLY UPDATE"
    else:
        half = len(words) // 2
        line1 = " ".join(words[:half])
        line2 = " ".join(words[half:])
        
    f_impact = get_font(38, bold=True, impact=True)
    
    # Line 1: Yellow banner (y ~ 438, max width ~ 640)
    bbox1 = draw.textbbox((0, 0), line1, font=f_impact)
    lw1 = bbox1[2] - bbox1[0]
    if lw1 > 640:
        f_impact_sm = get_font(32, bold=True, impact=True)
        bbox1 = draw.textbbox((0, 0), line1, font=f_impact_sm)
        lw1 = bbox1[2] - bbox1[0]
        draw.text((410 - lw1 // 2, 442), line1, fill=(10, 10, 15), font=f_impact_sm)
    else:
        draw.text((410 - lw1 // 2, 438), line1, fill=(10, 10, 15), font=f_impact)

    # Line 2: Red banner (y ~ 608, max width ~ 640)
    bbox2 = draw.textbbox((0, 0), line2, font=f_impact)
    lw2 = bbox2[2] - bbox2[0]
    if lw2 > 640:
        f_impact_sm2 = get_font(32, bold=True, impact=True)
        bbox2 = draw.textbbox((0, 0), line2, font=f_impact_sm2)
        lw2 = bbox2[2] - bbox2[0]
        draw.text((410 - lw2 // 2, 612), line2, fill=(255, 255, 255), font=f_impact_sm2)
    else:
        draw.text((410 - lw2 // 2, 608), line2, fill=(255, 255, 255), font=f_impact)

    # 4. Top Right Red Badge (slanted box: x: 1040 to 1380, y: 70 to 160)
    _, bot_line = extract_topic_line(story)
    badge_tag = f"⚡ {bot_line}"
    f_badge = get_font(28, bold=True, impact=True)
    bbox_bg = draw.textbbox((0, 0), badge_tag, font=f_badge)
    lw_bg = bbox_bg[2] - bbox_bg[0]
    if lw_bg > 320:
        f_badge = get_font(24, bold=True, impact=True)
        bbox_bg = draw.textbbox((0, 0), badge_tag, font=f_badge)
        lw_bg = bbox_bg[2] - bbox_bg[0]
    # Draw cleanly inside the red badge with zero overlap on golden frame or clock
    draw.rounded_rectangle([1050, 78, 1050 + lw_bg + 40, 142], radius=10, fill=(195, 15, 25, 255), outline=(255, 255, 255, 200), width=2)
    draw.text((1070, 96), badge_tag, fill=(255, 255, 255), font=f_badge)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, "PNG")
    return str(output_path)

def generate_transition_slide(next_story: dict, next_index: int, total: int, output_path: Path, is_shorts: bool = False) -> str:
    """Generates high-energy BharatBeacon broadcast transition slide played when switching stories"""
    if is_shorts:
        W, H = config.SHORTS_WIDTH, config.SHORTS_HEIGHT
        img = create_gradient_bg(W, H, (190, 20, 35, 255), (10, 14, 30, 255))
        draw = ImageDraw.Draw(img)

        banner_top = H // 2 - 160
        banner_bot = H // 2 + 120
        draw.polygon([(0, banner_top), (W, banner_top + 80), (W, banner_bot + 80), (0, banner_bot)], fill=(12, 16, 38, 250))
        draw.line([(0, banner_top), (W, banner_top + 80)], fill=(255, 215, 0), width=8)
        draw.line([(0, banner_bot), (W, banner_bot + 80)], fill=(255, 215, 0), width=8)

        font_main = get_font(76, bold=True, impact=True)
        draw.text((W // 2, H // 2 - 25), "⚡ BHARAT BEACON", font=font_main, fill=(255, 255, 255), anchor="mm")

        font_sub = get_font(38, bold=True)
        cat = next_story.get("category", "BREAKING").upper()
        draw.text((W // 2, H // 2 + 55), f"UP NEXT: HEADLINE #{next_index} • {cat}", font=font_sub, fill=(255, 215, 0), anchor="mm")
    else:
        W, H = config.LONGFORM_WIDTH, config.LONGFORM_HEIGHT
        img = create_gradient_bg(W, H, (160, 18, 30, 255), (10, 14, 32, 255))
        draw = ImageDraw.Draw(img)

        draw.rectangle([(0, H // 2 - 120), (W, H // 2 + 120)], fill=(12, 16, 38, 250))
        draw.line([(0, H // 2 - 120), (W, H // 2 - 120)], fill=(255, 215, 0), width=6)
        draw.line([(0, H // 2 + 120), (W, H // 2 + 120)], fill=(255, 215, 0), width=6)

        font_main = get_font(68, bold=True, impact=True)
        draw.text((W // 2, H // 2 - 25), "🔴 BHARAT BEACON • SPECIAL REPORT", font=font_main, fill=(255, 255, 255), anchor="mm")

        font_sub = get_font(34, bold=True)
        cat = next_story.get("category", "NATIONAL").upper()
        draw.text((W // 2, H // 2 + 50), f"UP NEXT: STORY #{next_index} • {cat}", font=font_sub, fill=(255, 215, 0), anchor="mm")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    return str(output_path)
