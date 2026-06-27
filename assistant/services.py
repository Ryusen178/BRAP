"""
Services: AI Fallback Chain (DeepSeek → Gemini → Groq) + Google Shopping (SerpApi)
"""

import json
import logging
import re
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Optional AI imports
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except (ImportError, Exception):
    GEMINI_AVAILABLE = False
    logger.debug("google-generativeai tidak tersedia di environment ini")

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logger.warning("groq tidak terinstall")


# ─────────────────────────────────────────
#  AI Fallback Chain (DeepSeek → Gemini → Groq)
# ─────────────────────────────────────────

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

QUERY_PARSE_SYSTEM_PROMPT = """Kamu adalah asisten belanja AI bernama BRAP.
Tugasmu adalah mengekstrak informasi pencarian produk dari pertanyaan pengguna.
Kembalikan HANYA JSON valid dengan struktur berikut (tanpa penjelasan apapun):
{
  "keywords": "kata kunci pencarian produk dalam bahasa Indonesia",
  "max_price": null atau angka (dalam Rupiah, tanpa titik/koma),
  "min_price": null atau angka (dalam Rupiah),
  "category": "kategori produk atau null",
  "sort_by": "price_asc" | "price_desc" | "rating" | "relevance",
  "num_results": 10,
  "insight_label": "label singkat 2-3 kata untuk rekomendasi ini",
  "headline": "judul menarik untuk halaman hasil pencarian (max 10 kata)"
}

Contoh input: "Rekomendasi sepatu merah di bawah 500 ribu"
Contoh output:
{
  "keywords": "sepatu merah",
  "max_price": 500000,
  "min_price": null,
  "category": "sepatu",
  "sort_by": "price_asc",
  "num_results": 10,
  "insight_label": "Budget Friendly",
  "headline": "10 Pilihan Terbaik BRAP: Sepatu Merah & Hemat!"
}"""


def _parse_query_deepseek(user_query: str) -> dict:
    """Try parsing query with DeepSeek API."""
    api_key = getattr(settings, "DEEPSEEK_API_KEY", "")
    if not api_key:
        logger.info("DeepSeek API key tidak tersedia")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": QUERY_PARSE_SYSTEM_PROMPT},
            {"role": "user", "content": user_query},
        ],
        "temperature": 0.1,
        "max_tokens": 300,
    }

    try:
        resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        # Strip potential markdown fences
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except Exception as e:
        logger.warning(f"DeepSeek parse_query error: {e}, trying Gemini...")
        return None


def _parse_query_gemini(user_query: str) -> dict:
    """Try parsing query with Google Gemini API."""
    if not GEMINI_AVAILABLE:
        logger.info("Gemini tidak tersedia, trying Groq...")
        return None
    
    api_key = getattr(settings, "GEMINI_API_KEY", "")
    if not api_key:
        logger.info("Gemini API key tidak tersedia, trying Groq...")
        return None

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(
            f"{QUERY_PARSE_SYSTEM_PROMPT}\n\nUser query: {user_query}",
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=1024,
            )
        )
        content = response.text.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except Exception as e:
        logger.warning(f"Gemini parse_query error: {e}, trying Groq...")
        return None


def _parse_query_groq(user_query: str) -> dict:
    """Try parsing query with Groq API (Fallback)."""
    if not GROQ_AVAILABLE:
        logger.info("Groq tidak tersedia")
        return None
    
    api_key = getattr(settings, "GROQ_API_KEY", "")
    if not api_key:
        logger.info("Groq API key tidak tersedia")
        return None

    try:
        client = Groq(api_key=api_key)
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": QUERY_PARSE_SYSTEM_PROMPT},
                {"role": "user", "content": user_query},
            ],
            model="openai/gpt-oss-20b",  # model gratis Groq (pengganti mixtral yang sudah deprecated)
            temperature=0.1,
            max_tokens=300,
        )
        content = chat_completion.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except Exception as e:
        logger.error(f"Groq parse_query error: {e}")
        return None


def parse_query_with_fallback(user_query: str) -> dict:
    """
    Parse query dengan fallback chain:
    1. DeepSeek (Primary)
    2. Gemini (Fallback)
    3. Groq (Fallback)
    4. Manual parsing (Fallback)
    """
    # Try DeepSeek first
    result = _parse_query_deepseek(user_query)
    if result:
        logger.info("Query parsed successfully with DeepSeek")
        return result
    
    # Try Gemini
    result = _parse_query_gemini(user_query)
    if result:
        logger.info("Query parsed successfully with Gemini")
        return result
    
    # Try Groq
    result = _parse_query_groq(user_query)
    if result:
        logger.info("Query parsed successfully with Groq")
        return result
    
    # Fallback to basic parsing
    logger.warning("All AI providers failed, using fallback parsing")
    return _fallback_parsed(user_query)


# Keep DeepSeek function for backward compatibility
def parse_query_with_deepseek(user_query: str) -> dict:
    """Deprecated: Use parse_query_with_fallback instead."""
    return parse_query_with_fallback(user_query)


def _fallback_parsed(user_query: str) -> dict:
    return {
        "keywords": user_query,
        "max_price": None,
        "min_price": None,
        "category": None,
        "sort_by": "relevance",
        "num_results": 10,
        "insight_label": "Pilihan BRAP",
        "headline": f"Hasil Pencarian untuk: {user_query}",
    }


def generate_brap_insight(product_name: str, price: int, user_query: str) -> str:
    """
    Generate short BRAP Insight tag for a product.
    Uses fallback chain: DeepSeek → Gemini → Groq
    """
    system_prompt = """Kamu adalah BRAP, shopping assistant AI. 
Buat insight singkat (max 5 kata) tentang produk ini relevan dengan kebutuhan pengguna.
Format: "Kategori: Deskripsi singkat"
Contoh: "Best Value: Awet & Murah" atau "Budget Pick: Terjangkau banget"
Kembalikan HANYA teks insight tanpa tanda petik."""

    user_content = f"Produk: {product_name}\nHarga: Rp {price:,}\nKebutuhan user: {user_query}"

    # Try DeepSeek
    try:
        api_key = getattr(settings, "DEEPSEEK_API_KEY", "")
        if api_key:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                "temperature": 0.7,
                "max_tokens": 30,
            }
            resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=10)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.debug(f"DeepSeek insight failed: {e}, trying Gemini...")

    # Try Gemini
    if GEMINI_AVAILABLE:
        try:
            api_key = getattr(settings, "GEMINI_API_KEY", "")
            if api_key:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content(
                    f"{system_prompt}\n\n{user_content}",
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.7,
                        max_output_tokens=512,
                    )
                )
                return response.text.strip()
        except Exception as e:
            logger.debug(f"Gemini insight failed: {e}, trying Groq...")

    # Try Groq
    if GROQ_AVAILABLE:
        try:
            api_key = getattr(settings, "GROQ_API_KEY", "")
            if api_key:
                client = Groq(api_key=api_key)
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    model="openai/gpt-oss-20b",
                    temperature=0.7,
                    max_tokens=30,
                )
                return chat_completion.choices[0].message.content.strip()
        except Exception as e:
            logger.debug(f"Groq insight failed: {e}")

    return "Pilihan BRAP"


def generate_product_description(product: dict, user_query: str) -> str:
    """
    Generate short product description for detail page.
    Uses fallback chain: DeepSeek → Gemini → Groq
    """
    system_prompt = """Kamu adalah BRAP, shopping assistant AI.
Buat deskripsi singkat produk (2-3 kalimat, bahasa Indonesia) yang informatif dan membantu pembeli.
Fokus pada keunggulan utama dan kesesuaian dengan kebutuhan pengguna.
Kembalikan HANYA teks deskripsi tanpa format apapun."""

    user_content = (
        f"Produk: {product.get('title', '')}\n"
        f"Brand: {product.get('brand', '')}\n"
        f"Harga: {product.get('price_display', '')}\n"
        f"Rating: {product.get('rating', 0)}\n"
        f"Kebutuhan user: {user_query}"
    )
    
    default_desc = f"{product.get('title', 'Produk ini')} adalah pilihan yang tepat untuk kebutuhanmu."

    # Try DeepSeek
    try:
        api_key = getattr(settings, "DEEPSEEK_API_KEY", "")
        if api_key:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                "temperature": 0.6,
                "max_tokens": 120,
            }
            resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=10)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.debug(f"DeepSeek description failed: {e}, trying Gemini...")

    # Try Gemini
    if GEMINI_AVAILABLE:
        try:
            api_key = getattr(settings, "GEMINI_API_KEY", "")
            if api_key:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content(
                    f"{system_prompt}\n\n{user_content}",
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.6,
                        max_output_tokens=512,
                    )
                )
                return response.text.strip()
        except Exception as e:
            logger.debug(f"Gemini description failed: {e}, trying Groq...")

    # Try Groq
    if GROQ_AVAILABLE:
        try:
            api_key = getattr(settings, "GROQ_API_KEY", "")
            if api_key:
                client = Groq(api_key=api_key)
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    model="openai/gpt-oss-20b",
                    temperature=0.6,
                    max_tokens=120,
                )
                return chat_completion.choices[0].message.content.strip()
        except Exception as e:
            logger.debug(f"Groq description failed: {e}")

    return default_desc


# ─────────────────────────────────────────
#  Google Shopping via SerpApi
# ─────────────────────────────────────────

SERPAPI_URL = "https://serpapi.com/search.json"

MARKETPLACE_DOMAINS = {
    "tokopedia.com": "Tokopedia",
    "shopee.co.id": "Shopee",
    "tiktok.com": "TikTokShop",
    "lazada.co.id": "Lazada",
    "blibli.com": "Blibli",
    "bukalapak.com": "Bukalapak",
    "orami.co.id": "Orami",
    "zalora.co.id": "Zalora",
    "jd.id": "JD.id",
}

# Marketplace yang diizinkan untuk BRAP
ALLOWED_MARKETPLACES = ["Tokopedia", "Shopee", "TikTokShop"]


def _detect_marketplace(link: str) -> str:
    for domain, name in MARKETPLACE_DOMAINS.items():
        if domain in link:
            return name
    return "Lihat di Toko"


def _generate_marketplace_link_from_source(source: str, product_title: str) -> dict:
    """
    Generate marketplace link dari source field SerpApi response.
    Returns {"marketplace": str, "url": str}
    """
    import urllib.parse
    
    # Clean source name dan map ke marketplace
    source_clean = str(source).strip().lower() if source else ""
    product_query = urllib.parse.quote(product_title[:50].strip())
    
    # Map source ke marketplace official name
    source_map = {
        "shopee": ("Shopee", f"https://shopee.co.id/search?keyword={product_query}"),
        "shopee.co.id": ("Shopee", f"https://shopee.co.id/search?keyword={product_query}"),
        "tokopedia": ("Tokopedia", f"https://www.tokopedia.com/search?q={product_query}"),
        "tokopedia.com": ("Tokopedia", f"https://www.tokopedia.com/search?q={product_query}"),
        "tiktok": ("TikTokShop", f"https://www.tiktok.com/search/item?q={product_query}"),
        "tiktokshop": ("TikTokShop", f"https://www.tiktok.com/search/item?q={product_query}"),
        "lazada": ("Lazada", f"https://www.lazada.co.id/catalog/?q={product_query}"),
        "lazada.co.id": ("Lazada", f"https://www.lazada.co.id/catalog/?q={product_query}"),
        "blibli": ("Blibli", f"https://www.blibli.com/search?q={product_query}"),
        "blibli.com": ("Blibli", f"https://www.blibli.com/search?q={product_query}"),
        "bukalapak": ("Bukalapak", f"https://www.bukalapak.com/?search_source=products&search={product_query}"),
        "bukalapak.com": ("Bukalapak", f"https://www.bukalapak.com/?search_source=products&search={product_query}"),
    }
    
    # Check exact match first
    if source_clean in source_map:
        marketplace, url = source_map[source_clean]
        return {"marketplace": marketplace, "url": url}
    
    # Check if source contains any known marketplace name
    for key, (marketplace, url) in source_map.items():
        if key in source_clean or source_clean in key:
            return {"marketplace": marketplace, "url": url}
    
    # Fallback: return unknown marketplace dengan generic search link
    return {"marketplace": "Lihat di Toko", "url": f"https://www.tokopedia.com/search?q={product_query}"}


def search_google_shopping(params: dict, marketplace_filter: list = None) -> list:
    """
    Search Google Shopping using SerpApi.
    params keys: keywords, max_price, min_price, sort_by, num_results
    marketplace_filter: list of marketplace names to prioritize (e.g., ["Tokopedia", "Shopee"])
    Returns list of product dicts.
    """
    # FIX: use getattr with default None to avoid AttributeError
    api_key = getattr(settings, "SERPAPI_KEY", None) or getattr(settings, "GOOGLE_SHOPPING_API_KEY", None)

    if not api_key:
        logger.info("Tidak ada SerpApi key — menggunakan mode demo (mock products).")
        return _mock_products(params)

    query = params.get("keywords", "")
    num_results = params.get("num_results", 10)
    
    # Request lebih banyak dari SerpApi untuk memastikan kita punya cukup hasil
    serpapi_params = {
        "engine": "google_shopping",
        "q": query,
        "gl": "id",
        "hl": "id",
        "api_key": api_key,
        "num": min(num_results * 2, 40),  # Request 2x lipat untuk filter
    }

    if params.get("max_price"):
        serpapi_params["price_max"] = int(params["max_price"])
    if params.get("min_price"):
        serpapi_params["price_min"] = int(params["min_price"])

    sort_map = {
        "price_asc": "p_ord:p",
        "price_desc": "p_ord:pd",
        "rating": "p_ord:rv",
    }
    if params.get("sort_by") in sort_map:
        serpapi_params["tbs"] = sort_map[params["sort_by"]]

    try:
        resp = requests.get(SERPAPI_URL, params=serpapi_params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        shopping_results = data.get("shopping_results", [])

        products = []
        for item in shopping_results:
            price_raw = item.get("price", "0")
            price_int = _parse_price(price_raw)
            rating = item.get("rating", 0)
            reviews = item.get("reviews", 0)
            
            # Try to get marketplace from source field (from SerpApi)
            source = item.get("source", "")
            
            # Map source ke marketplace name dan buat direct link
            marketplace_link = _generate_marketplace_link_from_source(source, item.get("title", ""))
            
            product = {
                "title": item.get("title", "Produk"),
                "brand": item.get("source", ""),
                "price": price_int,
                "price_display": _format_price(price_int),
                "rating": float(rating) if rating else 4.5,
                "reviews": int(reviews) if reviews else 0,
                "image": item.get("thumbnail", ""),
                "link": marketplace_link["url"],
                "marketplace": marketplace_link["marketplace"],
                "marketplace_list": [marketplace_link["marketplace"]],
                "insight": "",
                "description": "",
            }
            
            # Filter marketplace: hanya tampilkan yang diizinkan
            if marketplace_filter and marketplace_link["marketplace"] not in marketplace_filter:
                logger.debug(f"Skipping product from {marketplace_link['marketplace']} (not in allowed list)")
                continue

            # Prioritaskan urutan marketplace
            if marketplace_filter:
                priority = marketplace_filter.index(marketplace_link["marketplace"]) if marketplace_link["marketplace"] in marketplace_filter else 999
                products.append((priority, product))
            else:
                products.append((999, product))

        # Sort by priority, then ambil num_results yang diminta
        products = sorted(products, key=lambda x: x[0])
        products = [p[1] for p in products[:num_results]]

        if not products:
            logger.info("SerpApi tidak mengembalikan hasil — fallback ke mock.")
            return _mock_products(params)

        return products

    except Exception as e:
        logger.error(f"SerpApi error: {e}")
        return _mock_products(params)


def _parse_price(price_str: str) -> int:
    """Convert 'Rp1.299.000' or '$12.99' to integer."""
    digits = re.sub(r"[^\d]", "", str(price_str))
    return int(digits) if digits else 0


def _format_price(price: int) -> str:
    """Format integer price to Indonesian Rupiah string."""
    return f"Rp {price:,}".replace(",", ".")


def _mock_products(params: dict) -> list:
    """Return placeholder products when no API key is configured."""
    keyword = params.get("keywords", "produk")
    max_p = params.get("max_price") or 1_000_000

    # Helper function untuk generate marketplace links
    def get_marketplace_link(marketplace: str, product_keyword: str) -> str:
        """Generate search link ke marketplace berdasarkan keyword."""
        import urllib.parse
        query = urllib.parse.quote(product_keyword)
        
        links = {
            "Tokopedia": f"https://www.tokopedia.com/search?q={query}",
            "Shopee": f"https://shopee.co.id/search?keyword={query}",
            "TikTokShop": f"https://www.tiktok.com/search/item?q={query}",
            "Lazada": f"https://www.lazada.co.id/catalog/?q={query}",
            "Blibli": f"https://www.blibli.com/search?q={query}",
            "Bukalapak": f"https://www.bukalapak.com/?search_source=products&search={query}",
        }
        return links.get(marketplace, f"https://www.tokopedia.com/search?q={query}")

    products = [
        {
            "title": f"{keyword.title()} Premium Edition",
            "brand": "Brand A Official",
            "price": min(int(max_p * 0.9), 899_000),
            "price_display": _format_price(min(int(max_p * 0.9), 899_000)),
            "rating": 4.8,
            "reviews": 2451,
            "image": "",
            "link": get_marketplace_link("Tokopedia", keyword),
            "marketplace": "Tokopedia",
            "marketplace_list": ["Tokopedia"],
            "insight": "Best Value: Awet & Berkualitas",
            "description": "",
        },
        {
            "title": f"{keyword.title()} Original Series",
            "brand": "Brand B Store",
            "price": min(int(max_p * 0.7), 699_000),
            "price_display": _format_price(min(int(max_p * 0.7), 699_000)),
            "rating": 4.7,
            "reviews": 1823,
            "image": "",
            "link": get_marketplace_link("Shopee", keyword),
            "marketplace": "Shopee",
            "marketplace_list": ["Shopee"],
            "insight": "Most Popular: Sering Dibeli",
            "description": "",
        },
        {
            "title": f"{keyword.title()} Budget Series",
            "brand": "Brand C Shop",
            "price": min(int(max_p * 0.5), 499_000),
            "price_display": _format_price(min(int(max_p * 0.5), 499_000)),
            "rating": 4.6,
            "reviews": 3102,
            "image": "",
            "link": get_marketplace_link("Tokopedia", keyword),
            "marketplace": "Tokopedia",
            "marketplace_list": ["Tokopedia"],
            "insight": "Budget Friendly: Terjangkau",
            "description": "",
        },
        {
            "title": f"{keyword.title()} Deluxe Plus",
            "brand": "Brand D Premium",
            "price": min(int(max_p * 0.8), 799_000),
            "price_display": _format_price(min(int(max_p * 0.8), 799_000)),
            "rating": 4.7,
            "reviews": 1956,
            "image": "",
            "link": get_marketplace_link("Shopee", keyword),
            "marketplace": "Shopee",
            "marketplace_list": ["Shopee"],
            "insight": "Premium Choice: Recommended",
            "description": "",
        },
        {
            "title": f"{keyword.title()} TikTok Exclusive",
            "brand": "Brand E TikTokShop",
            "price": min(int(max_p * 0.6), 599_000),
            "price_display": _format_price(min(int(max_p * 0.6), 599_000)),
            "rating": 4.5,
            "reviews": 1234,
            "image": "",
            "link": get_marketplace_link("TikTokShop", keyword),
            "marketplace": "TikTokShop",
            "marketplace_list": ["TikTokShop"],
            "insight": "Exclusive: Live Shop",
            "description": "",
        },
        {
            "title": f"{keyword.title()} Pro Max",
            "brand": "Brand F Ltd",
            "price": min(int(max_p * 0.95), 949_000),
            "price_display": _format_price(min(int(max_p * 0.95), 949_000)),
            "rating": 4.9,
            "reviews": 3567,
            "image": "",
            "link": get_marketplace_link("Shopee", keyword),
            "marketplace": "Shopee",
            "marketplace_list": ["Shopee"],
            "insight": "Top Rated: Pilihan Terbaik",
            "description": "",
        },
    ]
    return products[: params.get("num_results", 10)]


def search_marketplace_priority(params: dict) -> list:
    """
    Search dengan filter marketplace: hanya Shopee, Tokopedia, dan TikTokShop.
    """
    logger.info(f"Searching products dari allowed marketplaces: {ALLOWED_MARKETPLACES}")
    products = search_google_shopping(params, marketplace_filter=ALLOWED_MARKETPLACES)
    
    return products


# ─────────────────────────────────────────
#  Main orchestrator
# ─────────────────────────────────────────

def search_products(user_query: str) -> dict:
    """
    Full pipeline:
    1. Parse query with DeepSeek (with fallback chain)
    2. Search dengan prioritas Marketplace (Shopee & Tokopedia) + Google Shopping
    3. Generate BRAP Insight + Description for each product
    Returns { headline, products, parsed_params, original_query }
    """
    parsed = parse_query_with_fallback(user_query)
    
    # Set default num_results jika tidak ada (fallback parsing)
    if parsed.get("num_results", 0) < 10:
        parsed["num_results"] = 10
    
    # Search dari marketplace dengan prioritas
    products = search_marketplace_priority(parsed)

    for product in products:
        # Generate BRAP Insight jika belum ada
        if not product.get("insight"):
            product["insight"] = generate_brap_insight(
                product["title"], product["price"], user_query
            )
        # Generate deskripsi untuk halaman detail
        if not product.get("description"):
            product["description"] = generate_product_description(product, user_query)

    return {
        "headline": parsed.get("headline", f"Hasil untuk: {user_query}"),
        "products": products,
        "parsed_params": parsed,
        "original_query": user_query,
    }