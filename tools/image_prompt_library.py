"""
Image prompt library cho gpt-image-2.
Curated từ EvoLink AI's awesome-gpt-image-2-API-and-Prompts repo
(https://github.com/EvoLinkAI/awesome-gpt-image-2-API-and-Prompts).

Mục tiêu: cung cấp templates chất lượng cao cho các use case marketing phổ biến
ở thị trường Việt Nam. Bot match user context → template phù hợp → inject
business-specific details để build prompt cuối.

Structure:
    PROMPT_LIBRARY: dict[str, dict] — key = slug, value = {category, title, prompt, aspect_ratio_hint}
    pick_template(category, format_hint, copy_text) → tên template + prompt cuối

Khi user upload ảnh mẫu, vision API trả về style desc — append vào prompt cuối
để giữ visual consistency.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PromptTemplate:
    slug: str
    title: str
    category: str  # food-ad / fashion-ad / product-ecommerce / lifestyle-portrait / poster / minimalist-beverage / etc.
    aspect_ratio_hint: str  # vertical / square / horizontal
    base_prompt: str
    """Base prompt text. Use {product}, {offer}, {brand}, {style_note} placeholders
    để inject business context."""


# ─────────────────────────────────────────────────────────────────
# Library — 30+ curated templates
# (Original ~17 từ EvoLink + 13 patterns thêm cho VN market: F&B, beauty, fashion,
#  real estate, tech/SaaS, education)
# ─────────────────────────────────────────────────────────────────

PROMPT_LIBRARY: dict[str, PromptTemplate] = {
    # ===== FOOD & BEVERAGE ADS =====
    "fnb_lifestyle_cafe": PromptTemplate(
        slug="fnb_lifestyle_cafe",
        title="Lifestyle Food Ad — Cozy Cafe",
        category="food-ad",
        aspect_ratio_hint="vertical",
        base_prompt=(
            "Vibrant lifestyle food advertisement, smiling person enjoying {product} inside a colorful trendy café, "
            "branded \"{brand}\" packaging visible on wooden table, playful retro typography reading \"{brand}\" "
            "in large bubble letters, tropical café interior with hanging plants, warm natural sunlight, "
            "cheerful atmosphere, bold color palette, shallow depth of field, cinematic food photography, "
            "ultra realistic, high detail, commercial ad campaign style, 4k. {style_note}"
        ),
    ),
    "fnb_product_splash": PromptTemplate(
        slug="fnb_product_splash",
        title="Dynamic Product Splash Ad",
        category="food-ad",
        aspect_ratio_hint="vertical",
        base_prompt=(
            "Dynamic food product advertisement for \"{brand}\" {product}, dramatic ingredient splashes and "
            "floating fruits/elements mid air, branded packaging beside the product, vivid background color, "
            "large retro cream typography saying \"{offer}\", glossy lighting, hyper realistic food photography, "
            "energetic composition, vibrant colors, commercial product shoot, ultra detailed textures, "
            "splash effect, studio lighting, 4k, advertising poster style. {style_note}"
        ),
    ),
    "fnb_breakfast_flatlay": PromptTemplate(
        slug="fnb_breakfast_flatlay",
        title="Premium Breakfast Flat Lay",
        category="food-ad",
        aspect_ratio_hint="square",
        base_prompt=(
            "High-end commercial breakfast advertisement, pastel aesthetic with centered standing packaging "
            "labeled \"{brand} {product}\", surrounded by relevant ingredients (fruits, milk jug, granola, "
            "scattered ingredients), soft natural lighting, vibrant fresh mood, modern bold typography "
            "headline \"{offer}\", handwritten callout arrows and benefit text, realistic food textures, "
            "luxury packaging design, clean flat lay composition, soft shadows, premium branding, "
            "glossy vibrant colors, ultra-detailed food photography, Instagram/Facebook ad campaign style, "
            "8k realistic render. {style_note}"
        ),
    ),
    "fnb_close_up_cozy": PromptTemplate(
        slug="fnb_close_up_cozy",
        title="Cozy Close-up Aesthetic",
        category="food-ad",
        aspect_ratio_hint="square",
        base_prompt=(
            "Close-up aesthetic photo of {product} in transparent branded cup/holder, warm golden cafe ambience, "
            "cozy sunlight and soft bokeh background, cute white doodle overlays and handwritten text \"{offer}\", "
            "scrapbook aesthetic, soft warm color palette, dreamy lifestyle photography, "
            "playful sparkles and hearts around the product, warm cinematic tones, ultra realistic photography, "
            "cozy Instagram aesthetic, soft glow effect, highly detailed. {style_note}"
        ),
    ),
    "fnb_burger_hero": PromptTemplate(
        slug="fnb_burger_hero",
        title="Cinematic Food Hero Shot",
        category="food-ad",
        aspect_ratio_hint="horizontal",
        base_prompt=(
            "Cinematic hero image of {product} on a dark stone surface, glossy textures, appetizing details, "
            "fresh ingredients visible, realistic texture, appetizing steam, warm side light, "
            "shallow depth of field, premium food commercial style, no text/logos/watermark. {style_note}"
        ),
    ),

    # ===== FASHION / LIFESTYLE =====
    "fashion_editorial_collage": PromptTemplate(
        slug="fashion_editorial_collage",
        title="Editorial Fashion Collage",
        category="fashion-ad",
        aspect_ratio_hint="square",
        base_prompt=(
            "Premium 1:1 luxury fashion collage featuring the brand \"{brand}\" {product} in multiple cinematic "
            "portrait moments across one artistic composition. Blend ultra-realistic beauty with luxury editorial "
            "aesthetics. Include close-up shots, candid moments, stylish poses, playful expressions. Use "
            "asymmetrical overlapping photo layers, torn magazine textures, glossy reflections, handwritten "
            "fashion notes, dreamy gradients, cinematic bloom lighting, and tiny integrated typography "
            "like \"{offer}\". Ultra detailed, cinematic, premium social media advertisement style, 8K. {style_note}"
        ),
    ),
    "fashion_streetwear": PromptTemplate(
        slug="fashion_streetwear",
        title="Streetwear Editorial Shot",
        category="fashion-ad",
        aspect_ratio_hint="vertical",
        base_prompt=(
            "Editorial fashion advertisement of {product} from \"{brand}\", model styled in streetwear aesthetic, "
            "urban background (alley/rooftop/street), natural lighting with cinematic shadows, "
            "bold typography \"{offer}\" overlaid, premium magazine-style composition, "
            "9:16 vertical, photorealistic, 4k. {style_note}"
        ),
    ),

    # ===== BEAUTY / SKINCARE =====
    "beauty_minimal_product": PromptTemplate(
        slug="beauty_minimal_product",
        title="Minimal Skincare Product Shot",
        category="beauty-ad",
        aspect_ratio_hint="square",
        base_prompt=(
            "Minimalist premium skincare product photography, \"{brand} {product}\" bottle centered on clean "
            "background, soft natural morning lighting, dewy droplets, subtle floral or stone accents, "
            "pastel color palette, elegant typography \"{offer}\", commercial beauty ad aesthetic, "
            "high-end magazine quality, ultra realistic, 4k. {style_note}"
        ),
    ),
    "beauty_before_after": PromptTemplate(
        slug="beauty_before_after",
        title="Before/After Skin Comparison",
        category="beauty-ad",
        aspect_ratio_hint="vertical",
        base_prompt=(
            "Split-screen beauty advertisement showing dramatic before/after results of \"{brand} {product}\", "
            "left side shows pre-use skin condition, right side shows radiant glowing transformed result, "
            "clean white background, large bold typography \"{offer}\" between the two halves, "
            "commercial dermatology campaign style, ultra realistic skin texture, premium quality, 4k. {style_note}"
        ),
    ),

    # ===== ECOMMERCE / PRODUCT =====
    "ecommerce_hero": PromptTemplate(
        slug="ecommerce_hero",
        title="E-commerce Hero Product Shot",
        category="product-ecommerce",
        aspect_ratio_hint="square",
        base_prompt=(
            "Premium e-commerce product photography of \"{product}\" from \"{brand}\", centered composition, "
            "clean white or gradient background, professional studio lighting from 45 degrees, "
            "shallow depth of field, no shadows behind, sharp focus on product details, high-end retail catalog "
            "style, ultra realistic, 8k. Reserved space for text overlay: \"{offer}\". {style_note}"
        ),
    ),
    "ecommerce_storyboard_9cell": PromptTemplate(
        slug="ecommerce_storyboard_9cell",
        title="9-Cell Ad Storyboard",
        category="product-ecommerce",
        aspect_ratio_hint="square",
        base_prompt=(
            "9-cell hybrid keyframe-to-transition storyboard sheet for a 15-second {product} ad from \"{brand}\", "
            "moving from empty surface to ingredient assembly to final macro hero shot. Use large hero cells "
            "and smaller transition cells, motion arrows, ghosted positions, camera push-in icons. "
            "Style: premium commercial, warm lighting, rich texture, cinematic, minimal labels only. "
            "Bottom banner: \"{offer}\". No logos, no watermark. {style_note}"
        ),
    ),

    # ===== POSTER / BRANDING =====
    "poster_sports_editorial": PromptTemplate(
        slug="poster_sports_editorial",
        title="Sports Editorial Poster",
        category="poster",
        aspect_ratio_hint="vertical",
        base_prompt=(
            "Ultra-premium sports editorial poster of a powerful athlete using/wearing \"{brand} {product}\", "
            "cinematic Nike-style campaign aesthetic, glossy reflections, dramatic studio lighting, "
            "bold oversized typography in background saying \"{offer}\", clean luxury sports branding, "
            "intense confident poses, 9:16 vertical, 4k. {style_note}"
        ),
    ),
    "poster_minimal_luxe": PromptTemplate(
        slug="poster_minimal_luxe",
        title="Minimal Luxury Poster",
        category="poster",
        aspect_ratio_hint="vertical",
        base_prompt=(
            "Minimal luxury campaign poster for \"{brand}\", featuring {product} in clean isolated composition, "
            "premium materials and textures, soft monochromatic color palette (cream/beige/black), "
            "elegant serif typography \"{offer}\", lots of negative space, fine art photography aesthetic, "
            "9:16 vertical magazine style, ultra detailed, 4k. {style_note}"
        ),
    ),

    # ===== BEVERAGE / DRINKS =====
    "beverage_rooftop_golden": PromptTemplate(
        slug="beverage_rooftop_golden",
        title="Rooftop Golden Hour Beverage",
        category="beverage-ad",
        aspect_ratio_hint="vertical",
        base_prompt=(
            "Bold, scroll-stopping vertical beverage ad featuring \"{brand} {product}\" set on a rooftop "
            "during golden hour with vibrant citrus/tropical energy. Cinematic lighting, condensation droplets, "
            "premium glass photography, dynamic angles, bold typography \"{offer}\", aspirational lifestyle vibe, "
            "9:16 vertical, photorealistic, 4k. {style_note}"
        ),
    ),
    "beverage_minimal_clean": PromptTemplate(
        slug="beverage_minimal_clean",
        title="Minimal Premium Beverage Ad",
        category="beverage-ad",
        aspect_ratio_hint="square",
        base_prompt=(
            "Minimalist premium beverage ad of \"{brand} {product}\", sunlit indoor setting with extremely clean "
            "composition, single product centered, soft natural light, subtle color palette, "
            "elegant minimal typography \"{offer}\", architectural digest style, 4k. {style_note}"
        ),
    ),

    # ===== REAL ESTATE =====
    "realestate_luxury_interior": PromptTemplate(
        slug="realestate_luxury_interior",
        title="Luxury Real Estate Interior",
        category="real-estate-ad",
        aspect_ratio_hint="horizontal",
        base_prompt=(
            "Luxury real estate advertisement showing premium interior of \"{product}\" by \"{brand}\", "
            "sun-drenched living room with floor-to-ceiling windows, designer furniture, fresh flowers, "
            "warm wood tones and neutral palette, magazine-style staging, cinematic depth, "
            "discreet typography \"{offer}\" at bottom, ultra realistic 8k photography. {style_note}"
        ),
    ),
    "realestate_aerial_project": PromptTemplate(
        slug="realestate_aerial_project",
        title="Aerial Project Showcase",
        category="real-estate-ad",
        aspect_ratio_hint="horizontal",
        base_prompt=(
            "Aerial / drone-style premium real estate marketing visual of \"{brand} {product}\" development, "
            "modern architecture, landscaped gardens, sunset golden lighting, cinematic composition, "
            "tagline \"{offer}\" overlaid elegantly, commercial real estate campaign aesthetic, 4k. {style_note}"
        ),
    ),

    # ===== TECH / SAAS =====
    "tech_ui_mockup": PromptTemplate(
        slug="tech_ui_mockup",
        title="SaaS Product UI Mockup",
        category="tech-saas-ad",
        aspect_ratio_hint="horizontal",
        base_prompt=(
            "Modern tech product advertisement showing \"{brand} {product}\" interface on premium devices "
            "(laptop + phone), clean minimalist studio backdrop, gradient color scheme, soft shadows, "
            "bold typography \"{offer}\" headline, startup landing page hero style, 4k. {style_note}"
        ),
    ),
    "tech_isometric_3d": PromptTemplate(
        slug="tech_isometric_3d",
        title="Isometric 3D Tech Illustration",
        category="tech-saas-ad",
        aspect_ratio_hint="square",
        base_prompt=(
            "Isometric 3D illustration advertising \"{brand} {product}\", colorful gradient palette, "
            "floating UI elements, abstract data visualization, modern flat-shading style, "
            "central headline \"{offer}\", energetic tech startup vibe, ultra detailed, 4k. {style_note}"
        ),
    ),

    # ===== EDUCATION / COURSES =====
    "edu_course_hero": PromptTemplate(
        slug="edu_course_hero",
        title="Course Hero Ad",
        category="education-ad",
        aspect_ratio_hint="vertical",
        base_prompt=(
            "Online course advertisement for \"{brand} {product}\", smiling confident instructor portrait "
            "on left side, course title \"{offer}\" in bold typography on right, professional studio lighting, "
            "warm trustworthy palette, accent graphics (certificate badge / 5-star ratings / student count), "
            "modern e-learning brand aesthetic, 9:16, 4k. {style_note}"
        ),
    ),
    "edu_testimonial_card": PromptTemplate(
        slug="edu_testimonial_card",
        title="Student Testimonial Card",
        category="education-ad",
        aspect_ratio_hint="square",
        base_prompt=(
            "Authentic student testimonial card for \"{brand} {product}\", warm portrait of a Vietnamese "
            "young professional smiling, large quote text \"{offer}\" in cursive accent, "
            "education brand aesthetic, soft pastel background, magazine ad quality, 4k. {style_note}"
        ),
    ),

    # ===== PORTRAIT / LIFESTYLE =====
    "lifestyle_cozy_morning": PromptTemplate(
        slug="lifestyle_cozy_morning",
        title="Cozy Morning Lifestyle Shot",
        category="lifestyle-portrait",
        aspect_ratio_hint="square",
        base_prompt=(
            "Warm cozy morning aesthetic near a window, person enjoying \"{brand} {product}\", "
            "soft sunlight entering through window, baby's breath flowers in glass vase, beige and cream "
            "minimal decor, calming self-care atmosphere, soft fabric textures, neutral warm tones, "
            "peaceful hygge mood, cinematic lifestyle photography, Pinterest-inspired cozy setup, "
            "realistic details, shallow depth of field, handwritten notes with \"{offer}\". Cozy-core vibe, 4k. {style_note}"
        ),
    ),
    "lifestyle_doodle_collage": PromptTemplate(
        slug="lifestyle_doodle_collage",
        title="Doodle Collage Lifestyle",
        category="lifestyle-portrait",
        aspect_ratio_hint="square",
        base_prompt=(
            "Cute doodle collage lifestyle photo featuring \"{brand} {product}\", kawaii white hand-drawn "
            "illustrations and stickers around the main image, handwritten typography saying \"{offer}\", "
            "playful sparkles, hearts, cloud doodles, soft warm color palette, dreamy lifestyle photography, "
            "Instagram story aesthetic, scrapbook journal style, ultra detailed, wholesome happy vibe, 4k. {style_note}"
        ),
    ),

    # ===== EVENT / LAUNCH =====
    "event_launch_announcement": PromptTemplate(
        slug="event_launch_announcement",
        title="Product Launch Announcement",
        category="event-ad",
        aspect_ratio_hint="vertical",
        base_prompt=(
            "Premium product launch announcement poster for \"{brand}\" releasing \"{product}\", "
            "dramatic studio lighting on the product centerpiece, sparkles and ambient particles, "
            "huge bold headline \"{offer}\" with launch date prominently displayed, "
            "luxury brand teaser aesthetic, dark moody background with selective lighting, "
            "9:16 vertical for Story/Reels, ultra cinematic, 4k. {style_note}"
        ),
    ),
    "event_sale_promo": PromptTemplate(
        slug="event_sale_promo",
        title="Sale Promo Banner",
        category="event-ad",
        aspect_ratio_hint="square",
        base_prompt=(
            "Bold sale promo banner for \"{brand}\", oversized typography \"{offer}\" dominating the composition, "
            "{product} thumbnail placed prominently with discount badge, energetic vibrant background "
            "(red/yellow/sale palette), urgency cues like countdown timer or limited-time stamp, "
            "scroll-stopping social ad design, ultra detailed, 4k. {style_note}"
        ),
    ),
}


# ─────────────────────────────────────────────────────────────────
# Picker — match user context to best template
# ─────────────────────────────────────────────────────────────────

# Category keyword → templates
CATEGORY_KEYWORDS = {
    "food-ad": ["food", "thực phẩm", "đồ ăn", "ăn", "ẩm thực", "snack", "bánh", "kẹo", "fnb"],
    "beverage-ad": ["beverage", "drink", "đồ uống", "trà", "cafe", "coffee", "juice", "nước"],
    "fashion-ad": ["fashion", "thời trang", "quần áo", "giày", "túi", "phụ kiện"],
    "beauty-ad": ["beauty", "mỹ phẩm", "skincare", "spa", "thẩm mỹ", "salon", "nail", "tóc"],
    "real-estate-ad": ["real estate", "bất động sản", "căn hộ", "nhà", "chung cư", "villa"],
    "tech-saas-ad": ["saas", "phần mềm", "app", "platform", "tech", "software"],
    "education-ad": ["education", "khóa học", "course", "edu", "đào tạo", "training", "học"],
    "product-ecommerce": ["ecommerce", "shop", "store", "retail", "online store", "marketplace"],
    "event-ad": ["launch", "ra mắt", "sale", "khuyến mãi", "promo", "event", "sự kiện"],
    "lifestyle-portrait": ["lifestyle", "portrait", "personal", "founder", "cá nhân"],
    "poster": ["poster", "branding", "campaign", "billboard"],
}


def categorize(text: str) -> str:
    """Best-effort categorize business context → template category."""
    t = (text or "").lower()
    scores: dict[str, int] = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        scores[cat] = sum(1 for kw in keywords if kw in t)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "product-ecommerce"


def pick_template(
    category: Optional[str] = None,
    aspect_ratio: Optional[str] = None,
    context_text: Optional[str] = None,
) -> PromptTemplate:
    """Pick best-matching template.

    Args:
        category: e.g. "food-ad" / "fashion-ad" / "beverage-ad"
        aspect_ratio: "vertical" / "square" / "horizontal"
        context_text: free-form (vd: product description) → categorize

    Returns:
        PromptTemplate (with base_prompt placeholder format)
    """
    cat = category or (categorize(context_text) if context_text else "product-ecommerce")
    candidates = [t for t in PROMPT_LIBRARY.values() if t.category == cat]
    if not candidates:
        # Fallback to ecommerce hero
        return PROMPT_LIBRARY["ecommerce_hero"]

    if aspect_ratio:
        filtered = [t for t in candidates if t.aspect_ratio_hint == aspect_ratio]
        if filtered:
            candidates = filtered

    return candidates[0]  # pick first match (could randomize later)


def build_prompt(
    product: str = "sản phẩm",
    brand: str = "",
    offer: str = "",
    style_note: str = "",
    category: Optional[str] = None,
    aspect_ratio: Optional[str] = None,
) -> tuple[str, str]:
    """Build final image gen prompt by filling template placeholders.

    Returns: (final_prompt, template_slug)
    """
    tpl = pick_template(category=category, aspect_ratio=aspect_ratio, context_text=product)
    final = tpl.base_prompt.format(
        product=product or "sản phẩm",
        brand=brand or "Brand",
        offer=offer or "",
        style_note=style_note or "",
    ).strip()
    return final, tpl.slug


__all__ = [
    "PromptTemplate",
    "PROMPT_LIBRARY",
    "CATEGORY_KEYWORDS",
    "categorize",
    "pick_template",
    "build_prompt",
]
