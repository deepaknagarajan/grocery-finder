"""
Grocery Finder — upload a grocery store aisle photo, scan once with Claude Vision,
then search for any product instantly without additional API calls.
"""

import os
import json
import base64
import re
from io import BytesIO

import streamlit as st
from PIL import Image, ImageDraw, ImageOps, ImageFont
import anthropic
from streamlit_mic_recorder import speech_to_text


MAX_IMAGE_SIZE = 1568
CIRCLE_COLORS = ["#FF3333", "#33CC33", "#3399FF", "#FF9900", "#CC33FF"]
CIRCLE_WIDTH = 5
CIRCLE_PADDING = 14

SCAN_PROMPT = """This image is exactly {width} pixels wide and {height} pixels tall.

You are scanning a grocery store shelf. Identify and locate EVERY distinct product visible.

Return ONLY this JSON (no markdown, no explanation):
{{
  "products": [
    {{
      "x1": <integer pixels from left edge>,
      "y1": <integer pixels from top edge>,
      "x2": <integer pixels from left edge>,
      "y2": <integer pixels from top edge>,
      "name": "<brand + product name, e.g. McCormick Organic Ground Ginger>"
    }}
  ]
}}

Rules:
- All coordinates are INTEGER pixel values
- x1 < x2, both between 0 and {width}
- y1 < y2, both between 0 and {height}
- List every product you can read, even partially visible ones
- Use full brand + product name"""


def prepare_image(uploaded_file) -> tuple[Image.Image, str, str]:
    img = Image.open(uploaded_file)
    img = ImageOps.exif_transpose(img)
    if img.mode != "RGB":
        img = img.convert("RGB")
    w, h = img.size
    if max(w, h) > MAX_IMAGE_SIZE:
        scale = MAX_IMAGE_SIZE / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=90)
    b64 = base64.standard_b64encode(buf.getvalue()).decode()
    return img, b64, "image/jpeg"


def scan_shelf(
    client: anthropic.Anthropic,
    b64: str,
    media_type: str,
    img_width: int,
    img_height: int,
) -> list[dict]:
    prompt = SCAN_PROMPT.format(width=img_width, height=img_height)
    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": b64},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    raw = response.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    data = json.loads(raw)
    return data.get("products", [])


def search_products(products: list[dict], query: str) -> list[dict]:
    q = query.lower().strip()
    if not q:
        return []
    return [p for p in products if q in p["name"].lower()]


def draw_annotations(img: Image.Image, matches: list[dict]) -> Image.Image:
    annotated = img.copy()
    draw = ImageDraw.Draw(annotated)
    w, h = annotated.size

    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except Exception:
        font = ImageFont.load_default()

    for i, inst in enumerate(matches):
        color = CIRCLE_COLORS[i % len(CIRCLE_COLORS)]

        rx1, rx2 = sorted([float(inst["x1"]), float(inst["x2"])])
        ry1, ry2 = sorted([float(inst["y1"]), float(inst["y2"])])

        x1 = max(0, int(rx1 - CIRCLE_PADDING))
        y1 = max(0, int(ry1 - CIRCLE_PADDING))
        x2 = min(w, int(rx2 + CIRCLE_PADDING))
        y2 = min(h, int(ry2 + CIRCLE_PADDING))

        if x2 - x1 < 4 or y2 - y1 < 4:
            continue

        draw.ellipse([x1, y1, x2, y2], outline=color, width=CIRCLE_WIDTH)

        label = inst.get("name", "")
        if label:
            text_x = max(0, x1)
            text_y = max(0, y1 - 24)
            bbox = draw.textbbox((text_x + 2, text_y + 2), label, font=font)
            draw.rectangle([text_x, text_y, bbox[2] + 4, bbox[3] + 2], fill=color)
            draw.text((text_x + 2, text_y + 2), label, fill="white", font=font)

    return annotated


def main():
    st.set_page_config(page_title="Grocery Finder", page_icon="🛒")

    # ── Sidebar: API key ──────────────────────────────────────────────────────
    with st.sidebar:
        st.header("Settings")
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            api_key = st.text_input(
                "Anthropic API Key",
                type="password",
                placeholder="sk-ant-...",
                help="Get your key at console.anthropic.com",
            )
        else:
            st.success("API key loaded from environment.")

        if "products" in st.session_state:
            st.divider()
            st.metric("Products found", len(st.session_state.products))
            if st.button("🔄 Rescan shelf"):
                for key in ["products", "img", "img_b64", "img_media_type", "img_w", "img_h"]:
                    st.session_state.pop(key, None)
                st.rerun()

    st.title("🛒 Grocery Finder")

    # ── Step 1: Upload ────────────────────────────────────────────────────────
    uploaded = st.file_uploader(
        "Upload a grocery store aisle photo",
        type=["jpg", "jpeg", "png", "webp"],
    )

    # Reset state if a new photo is uploaded
    if uploaded:
        file_id = (uploaded.name, uploaded.size)
        if st.session_state.get("_file_id") != file_id:
            for key in ["products", "img", "img_b64", "img_media_type", "img_w", "img_h"]:
                st.session_state.pop(key, None)
            st.session_state["_file_id"] = file_id

    if uploaded:
        st.image(uploaded, caption="Uploaded photo", use_container_width=True)

    # ── Step 2: Scan ──────────────────────────────────────────────────────────
    if uploaded and "products" not in st.session_state:
        if not api_key:
            st.warning("Enter your Anthropic API key in the sidebar to scan.")
        else:
            if st.button("🔍 Scan Shelf", type="primary", use_container_width=True):
                with st.spinner("Scanning shelf — Claude is reading every product label..."):
                    try:
                        img, b64, media_type = prepare_image(uploaded)
                        img_w, img_h = img.size
                        client = anthropic.Anthropic(api_key=api_key)
                        products = scan_shelf(client, b64, media_type, img_w, img_h)
                        st.session_state.products = products
                        st.session_state.img = img
                        st.session_state.img_w = img_w
                        st.session_state.img_h = img_h
                        st.rerun()
                    except json.JSONDecodeError as e:
                        st.error(f"Unexpected response from Claude. Please try again. ({e})")
                    except anthropic.AuthenticationError:
                        st.error("Invalid API key. Please check the sidebar.")
                    except anthropic.RateLimitError:
                        st.error("Rate limit reached. Please wait a moment and try again.")
                    except Exception as e:
                        st.error(f"Error: {e}")

    # ── Step 3: Search (no API call) ──────────────────────────────────────────
    if "products" in st.session_state:
        products = st.session_state.products
        img = st.session_state.img

        st.success(f"Shelf scanned — {len(products)} products identified. Search below (no API calls).")

        # Apply voice result from previous run before widget renders
        if "_pending_voice" in st.session_state:
            st.session_state["search_query"] = st.session_state.pop("_pending_voice")

        col1, col2 = st.columns([5, 1])
        with col1:
            query = st.text_input(
                "Search for a product",
                placeholder="e.g. Honey Bunches of Oats",
                key="search_query",
            )
        with col2:
            st.write("")
            st.write("")
            voice = speech_to_text(
                language="en",
                just_once=True,
                use_container_width=True,
                key="mic",
            )
        if voice:
            st.session_state["_pending_voice"] = voice
            st.rerun()

        if query:
            matches = search_products(products, query)
            if matches:
                count = len(matches)
                label = "match" if count == 1 else "matches"
                st.info(f"**{count} {label}** for \"{query}\"")

                annotated = draw_annotations(img, matches)
                st.image(annotated, caption="Matches circled", use_container_width=True)

                buf = BytesIO()
                annotated.save(buf, format="JPEG", quality=92)
                st.download_button(
                    "⬇ Download annotated image",
                    data=buf.getvalue(),
                    file_name=f"found_{query.replace(' ', '_')}.jpg",
                    mime="image/jpeg",
                )
            else:
                st.warning(f'No matches for "{query}"')
                st.caption("Try a shorter search term, e.g. just the brand name.")

        with st.expander(f"All {len(products)} products found on shelf"):
            for p in sorted(products, key=lambda x: x["name"]):
                st.write(f"• {p['name']}")


if __name__ == "__main__":
    main()
