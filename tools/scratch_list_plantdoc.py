import zipfile, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
zip_path = r"c:\Users\user pc\Desktop\Agrinovva_App\tools\datasets_raw\tomato\plantdoc.zip"
INVALID = set("?*:|<>")
seen = set()
with zipfile.ZipFile(zip_path) as z:
    for m in z.namelist():
        if any(c in INVALID for c in m):
            continue
        parts = Path(m).parts
        if len(parts) >= 3:
            folder = parts[2]
            if folder not in seen:
                seen.add(folder)
                print(folder)
