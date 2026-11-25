import urllib.request, json

def check_zenodo(record_id):
    url = f"https://zenodo.org/api/records/{record_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"Zenodo {record_id} title:", data.get("metadata", {}).get("title"))
            files = data.get("files", [])
            print(f"Files count: {len(files)}")
            for f in files:
                key = f.get("key")
                sz = f.get("size", 0) // 1024 // 1024
                link = f.get("links", {}).get("self")
                print(f"  {key} ({sz} MB) -> {link}")
    except Exception as e:
        print(f"Zenodo {record_id} error: {e}")

def search_zenodo(query):
    url = f"https://zenodo.org/api/records?q={urllib.parse.quote(query)}&size=3"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            hits = data.get("hits", {}).get("hits", [])
            print(f"=== Zenodo Search: '{query}' (hits: {len(hits)}) ===")
            for h in hits:
                meta = h.get("metadata", {})
                rec_id = h.get("id")
                print(f"  [{rec_id}] {meta.get('title')} (files: {len(h.get('files', []))})")
    except Exception as e:
        print(f"Zenodo search error: {e}")

if __name__ == "__main__":
    check_zenodo("6470578")
    search_zenodo("fall armyworm maize")
    search_zenodo("yam disease leaf")
    search_zenodo("sorghum disease leaf")
