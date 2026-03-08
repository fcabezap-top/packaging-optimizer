"""
Download AI-generated product images for all 20 seed products.

Usage (from repo root):
    python scripts/download_product_images.py

Images are saved to:
    frontend/public/products/<product_id>.jpg

Requirements:
    pip install requests

If Pollinations.ai fails or gives a bad result for a specific product,
replace the file manually with any 400x400 JPEG (e.g. from Leonardo.ai,
Unsplash, or your own photo).
"""

import os
import time
import urllib.request
from urllib.parse import quote

# Output directory (relative to repo root)
OUT_DIR = os.path.join(
    os.path.dirname(__file__), "..", "frontend", "public", "products"
)

# Seed products – same prompts as the frontend helper
PRODUCTS = [
    # id, family, subfamily, product name
    ("f7b2e8a6-7c9d-4d4a-e53d-600000000001", "Iluminación",  "Bombillas",              "Bombilla LED E27 9W"),
    ("f7b2e8a6-7c9d-4d4a-e53d-600000000002", "Iluminación",  "Bombillas",              "Bombilla LED E14 regulable"),
    ("f7b2e8a6-7c9d-4d4a-e53d-600000000003", "Iluminación",  "Lámparas de pie",        "Lámpara de pie trípode nogal"),
    ("f7b2e8a6-7c9d-4d4a-e53d-600000000004", "Iluminación",  "Focos empotrables",      "Foco empotrable LED redondo"),
    ("f7b2e8a6-7c9d-4d4a-e53d-600000000005", "Textil",       "Camisetas",              "Camiseta básica cuello redondo"),
    ("f7b2e8a6-7c9d-4d4a-e53d-600000000006", "Textil",       "Camisetas",              "Camiseta manga larga estampada"),
    ("f7b2e8a6-7c9d-4d4a-e53d-600000000007", "Textil",       "Pantalones",             "Pantalón chino slim fit"),
    ("f7b2e8a6-7c9d-4d4a-e53d-600000000008", "Textil",       "Ropa de cama",           "Juego de sábanas percal 200 hilos"),
    ("f7b2e8a6-7c9d-4d4a-e53d-600000000009", "Vidrio",       "Vasos",                  "Vaso agua cristal borosilicato"),
    ("f7b2e8a6-7c9d-4d4a-e53d-600000000010", "Vidrio",       "Botellas",               "Botella agua vidrio hermética"),
    ("f7b2e8a6-7c9d-4d4a-e53d-600000000011", "Mobiliario",   "Sillas",                 "Silla oficina ergonómica"),
    ("f7b2e8a6-7c9d-4d4a-e53d-600000000012", "Mobiliario",   "Mesas",                  "Mesa escritorio minimalista"),
    ("f7b2e8a6-7c9d-4d4a-e53d-600000000013", "Electrónica",  "Smartphones",            "Smartphone Android 6.5"),
    ("f7b2e8a6-7c9d-4d4a-e53d-600000000014", "Electrónica",  "Tablets",                "Tablet Android 10"),
    ("f7b2e8a6-7c9d-4d4a-e53d-600000000015", "Electrónica",  "Portátiles",             "Portátil ultrabook 15.6"),
    ("f7b2e8a6-7c9d-4d4a-e53d-600000000016", "Decoración",   "Cuadros",                "Cuadro abstracto moderno"),
    ("f7b2e8a6-7c9d-4d4a-e53d-600000000017", "Decoración",   "Plantas artificiales",   "Planta artificial bambú decorativo"),
    ("f7b2e8a6-7c9d-4d4a-e53d-600000000018", "Decoración",   "Velas y aromas",         "Vela aromática lavanda"),
    ("f7b2e8a6-7c9d-4d4a-e53d-600000000019", "Juguetería",   "Puzzles",                "Puzzle 1000 piezas ciudad"),
    ("f7b2e8a6-7c9d-4d4a-e53d-600000000020", "Juguetería",   "Sets de construcción",   "Set de construcción bloques"),
]

# Better prompts per subfamily for cleaner product shots
SUBFAMILY_PROMPT: dict[str, str] = {
    "Bombillas":           "LED light bulb, white background, product photography, clean studio",
    "Lámparas de pie":     "floor lamp, white background, product photography, Scandinavian design",
    "Focos empotrables":   "LED recessed spotlight, white background, product photography",
    "Camisetas":           "folded t-shirt, white background, product photography, flat lay",
    "Pantalones":          "chino trousers folded, white background, product photography, flat lay",
    "Ropa de cama":        "bed sheet set folded, white background, product photography",
    "Vasos":               "glass water cup, white background, product photography, transparent",
    "Botellas":            "glass water bottle with bamboo cap, white background, product photography",
    "Sillas":              "ergonomic office chair, white background, product photography",
    "Mesas":               "minimalist desk, white background, product photography",
    "Smartphones":         "Android smartphone, white background, product photography, clean",
    "Tablets":             "Android tablet, white background, product photography",
    "Portátiles":          "ultrabook laptop, white background, product photography",
    "Cuadros":             "abstract canvas painting, white background, product photography",
    "Plantas artificiales":"artificial bamboo plant in white pot, white background, product photography",
    "Velas y aromas":      "scented candle jar, white background, product photography, minimal",
    "Puzzles":             "jigsaw puzzle box, white background, product photography",
    "Sets de construcción":"building blocks toy set, white background, product photography",
}


def str_seed(s: str) -> int:
    return sum(ord(c) for c in s) % 9999


def build_url(product_id: str, subfamily: str) -> str:
    prompt_text = SUBFAMILY_PROMPT.get(
        subfamily,
        f"{subfamily} product, white background, product photography, clean studio",
    )
    seed = str_seed(product_id)
    encoded = quote(prompt_text)
    return (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=400&height=400&nologo=true&seed={seed}&model=flux"
    )


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)

    for idx, (pid, family, subfamily, name) in enumerate(PRODUCTS, 1):
        out_path = os.path.join(OUT_DIR, f"{pid}.jpg")

        if os.path.exists(out_path):
            print(f"[{idx:02d}/20] SKIP  {name} (already exists)")
            continue

        url = build_url(pid, subfamily)
        print(f"[{idx:02d}/20] DOWN  {name}")
        print(f"       {url[:90]}...")

        try:
            # Pollinations can be slow – give it 90 s, retry up to 3 times
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            data = None
            for attempt in range(1, 4):
                try:
                    with urllib.request.urlopen(req, timeout=90) as resp:
                        data = resp.read()
                    break
                except Exception as e:
                    if attempt < 3:
                        wait = 30 * attempt
                        print(f"       Attempt {attempt} failed ({e}), retrying in {wait}s...")
                        time.sleep(wait)
                    else:
                        raise
            if data:
                with open(out_path, "wb") as f:
                    f.write(data)
                print(f"       Saved {len(data) // 1024} KB → {out_path}")
        except Exception as exc:
            print(f"       ERROR: {exc}")

        # Be polite to the API – 15 s between requests
        if idx < len(PRODUCTS):
            time.sleep(15)

    print("\nDone. Check frontend/public/products/")
    print("Replace any bad images manually with a 400x400 JPEG of the same filename.")


if __name__ == "__main__":
    main()
