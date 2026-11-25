import glob
import numpy as np
from PIL import Image

val_images = glob.glob(r"tools/datasets/val/*/*.jpg")[:50]

green_ratios = []
for p in val_images:
    img = Image.open(p).convert('RGB').resize((224, 224))
    arr = np.array(img, dtype=np.int32)
    r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
    
    # Green or yellow-green (chlorophyll)
    is_green = (g > r + 10) & (g > b + 10) & (g > 35)
    is_yellow_green = (g > b + 15) & (r > b + 15) & (g >= r - 15) & (g > 40)
    
    plant_pixels = is_green | is_yellow_green
    ratio = np.mean(plant_pixels)
    green_ratios.append(ratio)

print(f"Dataset crop images (50 samples):")
print(f"  Min plant ratio: {min(green_ratios)*100:.1f}%")
print(f"  Median plant ratio: {np.median(green_ratios)*100:.1f}%")
print(f"  Max plant ratio: {max(green_ratios)*100:.1f}%")
print(f"  Images with < 3% plant pixels: {sum(r < 0.03 for r in green_ratios)} / {len(green_ratios)}")
