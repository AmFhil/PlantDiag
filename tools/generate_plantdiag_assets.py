import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

MASTER_SIZE = 1024
SS = 2  # 2x supersampling for ultra smooth anti-aliased curves
DIM = MASTER_SIZE * SS

def create_master_emblem(is_round=False, transparent_bg=False):
    img = Image.new("RGBA", (DIM, DIM), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = DIM // 2, DIM // 2
    r = int(DIM * 0.44)

    # 1. Background Badge
    if not transparent_bg:
        if is_round:
            # Circle
            # Radial / vertical gradient simulation
            for i in range(r, 0, -2):
                ratio = i / r
                # Dark emerald #022c22 at edge to vibrant green #059669 at center
                cr = int(2 + (5 - 2) * (1 - ratio * 0.6))
                cg = int(44 + (150 - 44) * (1 - ratio * 0.7))
                cb = int(34 + (105 - 34) * (1 - ratio * 0.7))
                draw.ellipse([cx - i, cy - i, cx + i, cy + i], fill=(cr, cg, cb, 255))
        else:
            # Squircle / rounded rectangle
            corner_r = int(DIM * 0.22)
            box = [cx - r, cy - r, cx + r, cy + r]
            # Draw base dark emerald
            draw.rounded_rectangle(box, radius=corner_r, fill=(4, 60, 42, 255))
            # Inner gradient glow
            for step in range(20):
                inset = step * 6
                alpha = int(140 * (1 - step / 20.0))
                draw.rounded_rectangle(
                    [box[0] + inset, box[1] + inset, box[2] - inset, box[3] - inset],
                    radius=max(10, corner_r - inset),
                    fill=(6, 95, 70, alpha)
                )

        # Outer subtle ring
        draw.ellipse([cx - r + 8, cy - r + 8, cx + r - 8, cy + r - 8], outline=(16, 185, 129, 90), width=6 * SS)

    # 2. Diagnostic Scanner Radar Ring & Tech Crosshairs
    ring_r = int(r * 0.78)
    draw.ellipse([cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r], outline=(52, 211, 153, 110), width=3 * SS)
    
    # 4 Corner Target Reticles (AI Diagnosis crosshairs)
    ret_dist = int(r * 0.76)
    ret_len = int(28 * SS)
    ret_color = (251, 191, 36, 220) # Tech amber-gold
    w = 3 * SS
    # Top-left
    draw.line([cx - ret_dist, cy - ret_dist, cx - ret_dist + ret_len, cy - ret_dist], fill=ret_color, width=w)
    draw.line([cx - ret_dist, cy - ret_dist, cx - ret_dist, cy - ret_dist + ret_len], fill=ret_color, width=w)
    # Top-right
    draw.line([cx + ret_dist, cy - ret_dist, cx + ret_dist - ret_len, cy - ret_dist], fill=ret_color, width=w)
    draw.line([cx + ret_dist, cy - ret_dist, cx + ret_dist, cy - ret_dist + ret_len], fill=ret_color, width=w)
    # Bottom-left
    draw.line([cx - ret_dist, cy + ret_dist, cx - ret_dist + ret_len, cy + ret_dist], fill=ret_color, width=w)
    draw.line([cx - ret_dist, cy + ret_dist, cx - ret_dist, cy + ret_dist - ret_len], fill=ret_color, width=w)
    # Bottom-right
    draw.line([cx + ret_dist, cy + ret_dist, cx + ret_dist - ret_len, cy + ret_dist], fill=ret_color, width=w)
    draw.line([cx + ret_dist, cy + ret_dist, cx + ret_dist, cy + ret_dist - ret_len], fill=ret_color, width=w)

    # Scanner Pulse Arcs (Diagnosis Radar)
    draw.arc([cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r], start=-25, end=45, fill=(251, 191, 36, 240), width=5 * SS)
    draw.arc([cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r], start=155, end=225, fill=(16, 185, 129, 240), width=5 * SS)

    # 3. Organic Stylized Plant Leaf Emblem (Twin lobes with central diagnostic spine)
    # Left Lobe (Vibrant Emerald #10B981)
    pts_left = []
    top_y = cy - int(r * 0.58)
    bot_y = cy + int(r * 0.56)
    steps = 40
    for s in range(steps + 1):
        t = s / steps
        y = top_y + (bot_y - top_y) * t
        # Curve leftwards
        dx = -math.sin(t * math.pi) * (r * 0.52) * (1.0 - 0.2 * t)
        pts_left.append((cx + dx, y))
    # Return along the spine
    for s in range(steps, -1, -1):
        t = s / steps
        y = top_y + (bot_y - top_y) * t
        pts_left.append((cx - 2 * SS, y))
    draw.polygon(pts_left, fill=(16, 185, 129, 255))

    # Right Lobe (Fresh Lime-Green #34D399)
    pts_right = []
    for s in range(steps + 1):
        t = s / steps
        y = top_y + (bot_y - top_y) * t
        # Curve rightwards
        dx = math.sin(t * math.pi) * (r * 0.50) * (1.0 - 0.25 * t)
        pts_right.append((cx + dx, y))
    for s in range(steps, -1, -1):
        t = s / steps
        y = top_y + (bot_y - top_y) * t
        pts_right.append((cx + 2 * SS, y))
    draw.polygon(pts_right, fill=(52, 211, 153, 255))

    # Diagnostic Leaf Vein Arcs & Central Spine (Sleek White & Lime)
    spine_w = int(6 * SS)
    draw.line([cx, top_y + 10 * SS, cx, bot_y], fill=(255, 255, 255, 245), width=spine_w)

    # Veins radiating outward
    vein_color = (255, 255, 255, 190)
    for frac in [0.28, 0.45, 0.62, 0.78]:
        vy = top_y + int((bot_y - top_y) * frac)
        # Left vein angled up
        draw.line([cx, vy, cx - int(r * 0.30 * math.sin(frac * math.pi)), vy - int(r * 0.12)], fill=vein_color, width=3 * SS)
        # Right vein angled up
        draw.line([cx, vy, cx + int(r * 0.28 * math.sin(frac * math.pi)), vy - int(r * 0.11)], fill=vein_color, width=3 * SS)

    # 4. Central Diagnostic Pulse Dot (Glowing Heart of AI Diagnosis)
    pulse_y = cy + int(r * 0.05)
    draw.ellipse([cx - 16 * SS, pulse_y - 16 * SS, cx + 16 * SS, pulse_y + 16 * SS], fill=(251, 191, 36, 255))
    draw.ellipse([cx - 9 * SS, pulse_y - 9 * SS, cx + 9 * SS, pulse_y + 9 * SS], fill=(255, 255, 255, 255))

    # Downsample to MASTER_SIZE with high quality Lanczos filter
    final_img = img.resize((MASTER_SIZE, MASTER_SIZE), Image.Resampling.LANCZOS)
    return final_img

def generate_icons(master_square, master_round, master_fg, res_dir):
    icon_specs = {
        'mipmap-mdpi': (48, 108),
        'mipmap-hdpi': (72, 162),
        'mipmap-xhdpi': (96, 216),
        'mipmap-xxhdpi': (144, 324),
        'mipmap-xxxhdpi': (192, 432),
    }

    for folder, (icon_sz, fg_sz) in icon_specs.items():
        out_dir = os.path.join(res_dir, folder)
        os.makedirs(out_dir, exist_ok=True)

        # ic_launcher.png
        master_square.resize((icon_sz, icon_sz), Image.Resampling.LANCZOS).save(os.path.join(out_dir, "ic_launcher.png"))
        # ic_launcher_round.png
        master_round.resize((icon_sz, icon_sz), Image.Resampling.LANCZOS).save(os.path.join(out_dir, "ic_launcher_round.png"))
        # ic_launcher_foreground.png
        master_fg.resize((fg_sz, fg_sz), Image.Resampling.LANCZOS).save(os.path.join(out_dir, "ic_launcher_foreground.png"))
        print(f"Generated icons in {folder} ({icon_sz}x{icon_sz}, fg={fg_sz}x{fg_sz})")

def generate_splash_screen(w, h, master_logo):
    # Rich dark modern emerald gradient
    splash = Image.new("RGB", (w, h), (3, 44, 34))
    draw = ImageDraw.Draw(splash)

    # Vertical gradient from deep dark #011c15 to #064e3b in center back to #011c15
    for y in range(h):
        # Normalized distance from vertical center
        dy = abs(y - h / 2.0) / (h / 2.0)
        t = 1.0 - min(1.0, dy) # 1 at center, 0 at top/bottom
        r = int(1 + 5 * t)
        g = int(24 + 50 * t)
        b = int(18 + 36 * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # Center emblem
    # Target emblem size: ~28% of shortest dimension
    min_dim = min(w, h)
    logo_sz = max(110, int(min_dim * (0.34 if w < h else 0.40)))
    logo_resized = master_logo.resize((logo_sz, logo_sz), Image.Resampling.LANCZOS)
    
    # Position: slightly above center to accommodate text
    logo_x = (w - logo_sz) // 2
    logo_y = (h - logo_sz) // 2 - int(min_dim * 0.08)
    splash.paste(logo_resized, (logo_x, logo_y), logo_resized)

    # Typography
    font_bold_path = r"C:\Windows\Fonts\segoeuib.ttf"
    font_reg_path = r"C:\Windows\Fonts\segoeui.ttf"
    if not os.path.exists(font_bold_path):
        font_bold_path = r"C:\Windows\Fonts\arialbd.ttf"
        font_reg_path = r"C:\Windows\Fonts\arial.ttf"

    title_size = max(18, int(min_dim * 0.070))
    sub_size = max(10, int(min_dim * 0.026))
    foot_size = max(9, int(min_dim * 0.024))

    font_title = ImageFont.truetype(font_bold_path, title_size)
    font_sub = ImageFont.truetype(font_reg_path, sub_size)
    font_foot = ImageFont.truetype(font_reg_path, foot_size)
    font_tm = ImageFont.truetype(font_bold_path, max(7, int(foot_size * 0.65)))

    # Title: PlantDiag
    title_text = "PlantDiag"
    t_bbox = draw.textbbox((0, 0), title_text, font=font_title)
    tw = t_bbox[2] - t_bbox[0]
    th = t_bbox[3] - t_bbox[1]
    title_y = logo_y + logo_sz + int(min_dim * 0.035)
    title_x = (w - tw) // 2
    draw.text((title_x, title_y), title_text, font=font_title, fill=(255, 255, 255))

    # Subtitle: OFFLINE CROP DISEASE AI
    sub_text = "OFFLINE CROP DISEASE AI"
    s_bbox = draw.textbbox((0, 0), sub_text, font=font_sub)
    sw = s_bbox[2] - s_bbox[0]
    sub_y = title_y + th + int(min_dim * 0.02)
    draw.text(((w - sw) // 2, sub_y), sub_text, font=font_sub, fill=(110, 231, 183))

    # Bottom Credit: Built by Fhinovax TM
    foot_base = "Built by Fhinovax"
    tm_text = "TM"
    f_bbox = draw.textbbox((0, 0), foot_base, font=font_foot)
    fw = f_bbox[2] - f_bbox[0]
    tm_bbox = draw.textbbox((0, 0), tm_text, font=font_tm)
    tmw = tm_bbox[2] - tm_bbox[0]
    total_foot_w = fw + tmw + 2
    
    foot_x = (w - total_foot_w) // 2
    foot_y = h - int(min_dim * 0.065) - (f_bbox[3] - f_bbox[1])
    draw.text((foot_x, foot_y), foot_base, font=font_foot, fill=(156, 163, 175))
    draw.text((foot_x + fw + 2, foot_y - 2), tm_text, font=font_tm, fill=(209, 213, 219))

    return splash

def generate_all_splashes(master_logo, res_dir):
    splash_specs = {
        'drawable': (480, 320),
        'drawable-port-mdpi': (320, 480),
        'drawable-port-hdpi': (480, 800),
        'drawable-port-xhdpi': (720, 1280),
        'drawable-port-xxhdpi': (960, 1600),
        'drawable-port-xxxhdpi': (1280, 1920),
        'drawable-land-mdpi': (480, 320),
        'drawable-land-hdpi': (800, 480),
        'drawable-land-xhdpi': (1280, 720),
        'drawable-land-xxhdpi': (1600, 960),
        'drawable-land-xxxhdpi': (1920, 1280),
    }

    for folder, (w, h) in splash_specs.items():
        out_dir = os.path.join(res_dir, folder)
        os.makedirs(out_dir, exist_ok=True)
        splash_im = generate_splash_screen(w, h, master_logo)
        splash_path = os.path.join(out_dir, "splash.png")
        splash_im.save(splash_path, "PNG", optimize=True)
        print(f"Generated splash in {folder} ({w}x{h})")

def main():
    res_dir = r"Agrinovva mobile app/android/app/src/main/res"
    images_dir = r"Agrinovva mobile app/src/assets/images"
    public_images_dir = r"Agrinovva mobile app/android/app/src/main/assets/public/assets/images"
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(public_images_dir, exist_ok=True)

    print("Rendering master PlantDiag logo emblems...")
    master_square = create_master_emblem(is_round=False, transparent_bg=False)
    master_round = create_master_emblem(is_round=True, transparent_bg=False)
    master_fg = create_master_emblem(is_round=False, transparent_bg=True)

    # Save high-res master logos
    master_square.save(os.path.join(images_dir, "plantdiag_logo.png"))
    master_square.save(os.path.join(public_images_dir, "plantdiag_logo.png"))
    master_square.save(r"tools\output\plantdiag_master_logo.png") if os.path.exists(r"tools\output") else None

    print("Generating Android launcher icons...")
    generate_icons(master_square, master_round, master_fg, res_dir)

    print("Generating Android splash screens across all resolutions...")
    generate_all_splashes(master_round, res_dir)

    print("All PlantDiag visual assets generated successfully!")

if __name__ == "__main__":
    main()
