"""
Website Builder — Award-quality websites inspired by Awwwards.com

Pipeline:
  1. Open awwwards.com with Playwright (headless), grab winner sites + screenshots
  2. Feed screenshots to Gemini Vision for design analysis
  3. Generate full HTML/CSS/JS with GSAP, Three.js, custom cursor, scroll effects
  4. Serve locally + open in browser
  5. Write a live progress log so user can ask "what are you doing?"
"""

from __future__ import annotations
import asyncio
import base64
import io
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path


# ── Progress Logger ────────────────────────────────────────────────────────────

class BuildLog:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(f"[{_ts()}] Ali is starting the website build...\n", encoding="utf-8")

    def add(self, msg: str):
        line = f"[{_ts()}] {msg}\n"
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line)
        print(f"[WEB] {msg}")

    def read(self) -> str:
        try:
            return self.path.read_text(encoding="utf-8")
        except Exception:
            return "(log unavailable)"


def _ts():
    return datetime.now().strftime("%H:%M:%S")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _find_free_port(start=8500, end=8600):
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return port
            except OSError:
                continue
    return 8500


def _serve(directory: str, port: int):
    orig = os.getcwd()
    os.chdir(directory)

    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    server = HTTPServer(("", port), QuietHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    os.chdir(orig)
    return server


def _open_browser(url: str):
    try:
        subprocess.Popen(["open", url])
    except Exception:
        pass


def _img_to_b64(img_bytes: bytes) -> str:
    return base64.b64encode(img_bytes).decode()


# ── Awwwards Scraper ───────────────────────────────────────────────────────────

async def _scrape_awwwards(log: BuildLog) -> list[dict]:
    """
    Visit awwwards.com with Playwright, grab site names, URLs, descriptions,
    and screenshots of 3-4 winner/SOTD pages.
    Returns list of {name, url, description, screenshot_b64}
    """
    results = []
    try:
        from playwright.async_api import async_playwright

        log.add("Opening awwwards.com (headless browser)...")
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            ctx     = await browser.new_context(
                viewport={"width": 1440, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            )
            page = await ctx.new_page()

            # ── 1. Awwwards SOTD page ──
            try:
                await page.goto("https://www.awwwards.com/websites/", timeout=20000)
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
                await asyncio.sleep(2)

                # Screenshot the gallery page
                shot = await page.screenshot(full_page=False)
                log.add("Captured awwwards.com gallery screenshot")

                # Extract site cards
                cards = await page.query_selector_all("figure.js-item-figure, li.js-item-figure, article")
                log.add(f"Found {len(cards)} site cards on awwwards")

                for card in cards[:6]:
                    try:
                        title_el = await card.query_selector("h2, h3, .title, [class*='title']")
                        name = (await title_el.inner_text()).strip() if title_el else "Unknown"

                        link_el = await card.query_selector("a[href]")
                        href = await link_el.get_attribute("href") if link_el else ""
                        if href and not href.startswith("http"):
                            href = "https://www.awwwards.com" + href

                        desc_el = await card.query_selector("p, .description, [class*='desc']")
                        desc = (await desc_el.inner_text()).strip()[:200] if desc_el else ""

                        results.append({"name": name, "url": href, "description": desc, "screenshot_b64": None})
                        log.add(f"  → Site: {name}")
                    except Exception:
                        continue

                # Screenshot one actual winner site for design analysis
                if results:
                    winner_url = results[0].get("url", "")
                    if winner_url and "awwwards.com" in winner_url:
                        try:
                            await page.goto(winner_url, timeout=15000)
                            await page.wait_for_load_state("domcontentloaded", timeout=10000)
                            await asyncio.sleep(1.5)
                            detail_shot = await page.screenshot(full_page=False)
                            results[0]["screenshot_b64"] = _img_to_b64(detail_shot)
                            log.add(f"Captured detail screenshot of: {results[0]['name']}")
                        except Exception:
                            pass

            except Exception as e:
                log.add(f"Awwwards gallery scrape error: {e} — using SOTD fallback")

            # ── 2. Also grab SOTD ──
            try:
                await page.goto("https://www.awwwards.com/", timeout=15000)
                await page.wait_for_load_state("domcontentloaded", timeout=10000)
                await asyncio.sleep(1.5)

                sotd_shot = await page.screenshot(full_page=False)
                log.add("Captured awwwards.com homepage screenshot")

                # Get the SOTD title
                sotd_el = await page.query_selector("h1, h2, .site-name, [class*='winner']")
                sotd_name = (await sotd_el.inner_text()).strip() if sotd_el else "SOTD"
                results.insert(0, {
                    "name": f"SOTD: {sotd_name}",
                    "url": "https://www.awwwards.com",
                    "description": "Site of the Day from Awwwards — highest quality web design",
                    "screenshot_b64": _img_to_b64(sotd_shot),
                })
                log.add(f"Got Site of the Day: {sotd_name}")
            except Exception as e:
                log.add(f"SOTD grab error: {e}")

            await browser.close()

    except Exception as e:
        log.add(f"Browser scrape failed: {e} — continuing with text-based inspiration")

    # Fallback: curated design reference data
    if not results:
        log.add("Using curated design reference library (awwwards-inspired)")
        results = [
            {
                "name": "Apple.com", "url": "https://apple.com",
                "description": "Ultra-clean minimalism. Massive typography, full-bleed product photography, subtle scroll animations, monochromatic with accent highlights.",
                "screenshot_b64": None
            },
            {
                "name": "Linear.app", "url": "https://linear.app",
                "description": "Dark premium SaaS. Gradient glows, smooth hover states, glassmorphism cards, animated noise texture backgrounds.",
                "screenshot_b64": None
            },
            {
                "name": "Stripe.com", "url": "https://stripe.com",
                "description": "Colourful gradients, 3D tilt effects, crisp sans-serif, layered depth, animated gradient blobs.",
                "screenshot_b64": None
            },
        ]
    return results


# ── Gemini Vision Analysis ─────────────────────────────────────────────────────

def _analyze_with_gemini(sites: list[dict], topic: str, style: str, api_key: str, log: BuildLog) -> str:
    """Use Gemini to analyze screenshots and extract design patterns."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)

        # Build parts for the analysis request
        parts = []
        parts.append(
            f"You are an expert web designer analyzing Awwwards-winning websites.\n"
            f"I'm building a website for: {topic} (style: {style})\n\n"
            f"Here are {len(sites)} reference sites from Awwwards:\n"
        )

        screenshots_sent = 0
        for site in sites[:3]:
            parts.append(f"\n**{site['name']}**: {site['description']}")
            if site.get("screenshot_b64") and screenshots_sent < 2:
                parts.append({
                    "mime_type": "image/png",
                    "data": base64.b64decode(site["screenshot_b64"])
                })
                screenshots_sent += 1

        parts.append(
            f"\n\nAnalyze these and provide a DETAILED design brief for my {topic} website:\n"
            "1. COLOUR PALETTE (exact hex codes — 5-6 colours)\n"
            "2. TYPOGRAPHY (Google Font choices, sizes, weights)\n"
            "3. KEY ANIMATIONS (list 5-8 specific animations to implement)\n"
            "4. LAYOUT PATTERNS (hero, sections, product grid, footer)\n"
            "5. SPECIAL EFFECTS (cursor, parallax, noise texture, gradients)\n"
            "6. PRODUCT SECTION design (even if no products provided — create luxury placeholders)\n"
            "Be SPECIFIC and DETAILED. This design brief will be used to generate actual code."
        )

        model = genai.GenerativeModel("gemini-2.5-flash")
        # Send text-only if vision fails
        try:
            content_parts = []
            for p in parts:
                if isinstance(p, str):
                    content_parts.append(p)
                elif isinstance(p, dict):
                    from google.generativeai.types import BlobDict
                    content_parts.append({"inline_data": p})

            response = model.generate_content(content_parts, request_options={"timeout": 60})
        except Exception:
            text_only = "\n".join(p for p in parts if isinstance(p, str))
            response = model.generate_content(text_only, request_options={"timeout": 60})

        brief = response.text.strip()
        log.add(f"Design brief generated ({len(brief)} chars)")
        return brief

    except Exception as e:
        log.add(f"Vision analysis error: {e} — using default brief")
        return (
            f"Design brief for {topic} ({style}):\n"
            "COLOURS: #0a0a0f (bg), #f5f5f0 (text), #c8a96e (gold accent), #1a1a2e (deep navy)\n"
            "TYPOGRAPHY: Playfair Display (headings), Inter (body), huge 10-20vw hero text\n"
            "ANIMATIONS: GSAP scroll reveal, magnetic cursor, parallax layers, text scramble, smooth page transitions\n"
            "LAYOUT: Full-bleed hero, horizontal product scroll, alternating feature rows, editorial grid\n"
            "EFFECTS: Custom magnetic cursor, grain texture overlay, gradient glow orbs, clip-path reveals\n"
            "PRODUCTS: Luxury product cards with hover 3D tilt, name/price/material details"
        )


# ── HTML Generator ─────────────────────────────────────────────────────────────

def _generate_html(topic: str, style: str, pages: list, design_brief: str, api_key: str, log: BuildLog) -> dict[str, str]:
    """Generate complete, spectacular HTML files using the design brief."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")

        pages_desc = ", ".join(pages)

        prompt = f"""You are an award-winning web developer building a production website.

TOPIC: {topic}
STYLE: {style}
PAGES TO BUILD: {pages_desc}

DESIGN BRIEF (from Awwwards analysis):
{design_brief}

━━━ BUILD REQUIREMENTS ━━━

TECHNOLOGY (you MUST use these):
- GSAP 3.x via CDN (https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js)
- GSAP ScrollTrigger via CDN
- Google Fonts via @import
- Vanilla JS for all interactivity (no jQuery, no Vue, no React)
- CSS custom properties (variables) for theming
- CSS Grid + Flexbox layouts

MANDATORY FEATURES:
1. Custom animated cursor (magnetic effect on buttons/links)
2. Smooth scroll (CSS scroll-behavior + JS scroll handling)
3. Hero section with animated text (GSAP or CSS keyframes) — HUGE typography (8-15vw)
4. Scroll-triggered reveal animations (GSAP ScrollTrigger or IntersectionObserver)
5. Product/service section — create beautiful placeholder items if none provided
   Each product: high-quality CSS-drawn shape or SVG + name + description + price
6. Gradient noise texture overlay (CSS SVG filter or radial gradients)
7. Navigation with blur backdrop + smooth hide/show on scroll
8. Footer with links, copyright, social icons (SVG inline)
9. Mobile responsive (CSS clamp(), fluid typography)
10. Loading screen (brief, then dissolves away)

PERFORMANCE:
- All CSS inline in <style>
- All JS inline in <script> at bottom
- External CDN only for GSAP (2 script tags max)
- Google Fonts via @import inside <style>

DESIGN QUALITY:
- DO NOT build a generic/template website
- Use the exact colours and fonts from the design brief
- Make it feel like an Awwwards winner — bold, unexpected, premium
- Spacing should be generous (100px+ between sections)
- Use clip-path, mix-blend-mode, backdrop-filter for depth
- Horizontal rules and decorative elements should feel editorial

OUTPUT FORMAT:
For each page, output EXACTLY this JSON (one per line, valid JSON):
{{"filename": "index.html", "content": "<COMPLETE HTML — NO TRUNCATION>"}}

Critical: output the COMPLETE HTML. Do not say "rest of code here" or truncate.
Every page must be a fully working, standalone HTML file.
"""

        log.add("Calling Gemini to generate full website code...")
        log.add("(This may take 30-60 seconds for a complete, high-quality build)")

        response = model.generate_content(
            prompt,
            generation_config={"max_output_tokens": 65536},
            request_options={"timeout": 180}
        )
        raw = response.text.strip()
        log.add(f"Gemini returned {len(raw):,} characters of code")

        # Parse JSON blocks
        files = {}
        # Try strict JSON blocks first
        for m in re.finditer(r'\{"filename"\s*:\s*"([^"]+)"\s*,\s*"content"\s*:\s*("(?:[^"\\]|\\.)*"|\'.+?\')', raw, re.DOTALL):
            pass  # placeholder — use full parse below

        # Full parse: find JSON objects with filename + content
        decoder = json.JSONDecoder()
        idx = 0
        while idx < len(raw):
            try:
                brace = raw.index('{', idx)
                obj, end = decoder.raw_decode(raw, brace)
                if isinstance(obj, dict) and "filename" in obj and "content" in obj:
                    files[obj["filename"]] = obj["content"]
                    log.add(f"Parsed file: {obj['filename']} ({len(obj['content']):,} chars)")
                idx = end
            except (ValueError, KeyError):
                idx = (raw.index('{', idx) + 1) if '{' in raw[idx+1:] else len(raw)

        # Fallback: if the whole response looks like HTML
        if not files:
            if raw.strip().startswith("<!DOCTYPE") or raw.strip().startswith("<html"):
                files["index.html"] = raw
                log.add("Using raw HTML output as index.html")
            else:
                # Try to extract HTML blocks
                html_match = re.search(r'(<!DOCTYPE html.*?</html>)', raw, re.DOTALL | re.IGNORECASE)
                if html_match:
                    files["index.html"] = html_match.group(1)
                    log.add("Extracted HTML block as index.html")

        if not files:
            log.add("WARNING: Could not parse output — writing raw response")
            files["index.html"] = raw

        return files

    except Exception as e:
        log.add(f"HTML generation error: {e}")
        return {}


# ── Fallback Beautiful Template ────────────────────────────────────────────────

def _build_fallback(topic: str, style: str) -> str:
    """Spectacular fallback when Gemini fails — hand-coded award-quality template."""
    slug = topic.lower().replace(" ", "-")
    yr   = time.strftime('%Y')
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{topic.title()} — Premium</title>
<meta name="description" content="A premium {style} experience for {topic}.">
<meta property="og:title" content="{topic.title()}">
<meta property="og:description" content="Premium {style} website for {topic}.">
<link rel="canonical" href="https://example.com">
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700;900&family=Inter:wght@300;400;500;600&display=swap');
*,*::before,*::after{{margin:0;padding:0;box-sizing:border-box}}
:root{{
  --bg:#060608;--bg2:#0e0e16;--fg:#f0eee8;--acc:#c8a96e;--acc2:#8b5cf6;
  --dim:rgba(240,238,232,.5);--card:rgba(255,255,255,.04);
  --border:rgba(200,169,110,.15);--glow:rgba(200,169,110,.25);
}}
html{{scroll-behavior:smooth}}
body{{font-family:'Inter',sans-serif;background:var(--bg);color:var(--fg);overflow-x:hidden;cursor:none}}

/* ── Custom Cursor ── */
#cursor{{position:fixed;width:12px;height:12px;background:var(--acc);border-radius:50%;pointer-events:none;z-index:9999;transition:transform .15s ease,width .2s,height .2s,background .2s;transform:translate(-50%,-50%)}}
#cursor-ring{{position:fixed;width:40px;height:40px;border:1px solid var(--acc);border-radius:50%;pointer-events:none;z-index:9998;transition:transform .08s linear,width .25s,height .25s,opacity .3s;transform:translate(-50%,-50%);opacity:.6}}
body:hover #cursor{{opacity:1}}

/* ── Loading Screen ── */
#loader{{position:fixed;inset:0;background:var(--bg);z-index:10000;display:flex;align-items:center;justify-content:center;transition:opacity .8s ease, visibility .8s}}
#loader.hidden{{opacity:0;visibility:hidden}}
.loader-text{{font-family:'Playfair Display',serif;font-size:clamp(1rem,4vw,2rem);color:var(--acc);letter-spacing:.3em;text-transform:uppercase;animation:pulse 1.2s ease-in-out infinite}}
@keyframes pulse{{0%,100%{{opacity:.3}}50%{{opacity:1}}}}

/* ── Nav ── */
nav{{position:fixed;top:0;left:0;right:0;z-index:100;padding:1.5rem 4rem;display:flex;align-items:center;justify-content:space-between;transition:all .4s ease;backdrop-filter:blur(0px)}}
nav.scrolled{{backdrop-filter:blur(20px);background:rgba(6,6,8,.8);border-bottom:1px solid var(--border);padding:1rem 4rem}}
.nav-logo{{font-family:'Playfair Display',serif;font-size:1.3rem;font-weight:700;color:var(--acc);letter-spacing:.1em;text-transform:uppercase;text-decoration:none}}
.nav-links{{display:flex;gap:2.5rem;list-style:none}}
.nav-links a{{color:var(--dim);text-decoration:none;font-size:.85rem;letter-spacing:.15em;text-transform:uppercase;transition:color .3s}}
.nav-links a:hover{{color:var(--fg)}}

/* ── Hero ── */
.hero{{height:100vh;display:grid;place-items:center;position:relative;overflow:hidden;padding:0 4rem}}
.hero-bg{{position:absolute;inset:0;background:radial-gradient(ellipse 80% 60% at 50% 40%, rgba(139,92,246,.15) 0%, transparent 70%), radial-gradient(ellipse 60% 40% at 80% 70%, rgba(200,169,110,.1) 0%, transparent 60%)}}
.hero-noise{{position:absolute;inset:0;opacity:.03;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='4'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='1'/%3E%3C/svg%3E");background-size:200px 200px}}
.hero-content{{text-align:center;position:relative;z-index:1}}
.hero-eyebrow{{font-size:.75rem;letter-spacing:.4em;text-transform:uppercase;color:var(--acc);margin-bottom:2rem;opacity:0;animation:fadeUp .8s .3s forwards}}
.hero-title{{font-family:'Playfair Display',serif;font-size:clamp(4rem,12vw,10rem);line-height:.9;font-weight:900;letter-spacing:-.02em;margin-bottom:2.5rem;opacity:0;animation:fadeUp .9s .5s forwards}}
.hero-title em{{font-style:italic;color:var(--acc)}}
.hero-sub{{font-size:clamp(1rem,2vw,1.2rem);color:var(--dim);max-width:500px;margin:0 auto 3rem;line-height:1.7;opacity:0;animation:fadeUp .9s .7s forwards}}
.hero-cta{{display:inline-flex;align-items:center;gap:.75rem;padding:1rem 2.5rem;border:1px solid var(--acc);color:var(--acc);text-decoration:none;font-size:.85rem;letter-spacing:.2em;text-transform:uppercase;transition:all .3s;opacity:0;animation:fadeUp .9s .9s forwards}}
.hero-cta:hover{{background:var(--acc);color:var(--bg)}}
.scroll-indicator{{position:absolute;bottom:3rem;left:50%;transform:translateX(-50%);display:flex;flex-direction:column;align-items:center;gap:.5rem;opacity:.4;animation:fadeIn 1s 1.5s forwards both}}
.scroll-line{{width:1px;height:60px;background:linear-gradient(to bottom,transparent,var(--acc));animation:scrollLine 2s ease-in-out infinite}}
@keyframes scrollLine{{0%{{transform:scaleY(0);transform-origin:top}}50%{{transform:scaleY(1);transform-origin:top}}51%{{transform:scaleY(1);transform-origin:bottom}}100%{{transform:scaleY(0);transform-origin:bottom}}}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(40px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes fadeIn{{from{{opacity:0}}to{{opacity:.4}}}}

/* ── Section Base ── */
section{{padding:clamp(5rem,12vw,10rem) clamp(1.5rem,6vw,8rem)}}
.section-label{{font-size:.7rem;letter-spacing:.4em;text-transform:uppercase;color:var(--acc);margin-bottom:1.5rem;display:block}}
.section-title{{font-family:'Playfair Display',serif;font-size:clamp(2.5rem,6vw,5rem);line-height:1;font-weight:700;margin-bottom:2rem}}
.reveal{{opacity:0;transform:translateY(50px);transition:opacity .9s ease, transform .9s ease}}
.reveal.visible{{opacity:1;transform:none}}

/* ── Products ── */
.products{{background:var(--bg2)}}
.products-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:2px;margin-top:4rem}}
.product-card{{position:relative;aspect-ratio:3/4;overflow:hidden;background:var(--card);border:1px solid var(--border);cursor:none}}
.product-visual{{width:100%;height:70%;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,rgba(200,169,110,.08),rgba(139,92,246,.08));transition:transform .6s ease}}
.product-card:hover .product-visual{{transform:scale(1.05)}}
.product-shape{{width:100px;height:140px;border:1px solid var(--acc);border-radius:4px;position:relative;display:flex;align-items:center;justify-content:center}}
.product-shape::before{{content:'';position:absolute;inset:8px;border:1px solid rgba(200,169,110,.3);border-radius:2px}}
.product-info{{padding:1.5rem;border-top:1px solid var(--border)}}
.product-name{{font-family:'Playfair Display',serif;font-size:1.1rem;margin-bottom:.3rem}}
.product-detail{{font-size:.8rem;color:var(--dim);letter-spacing:.1em;text-transform:uppercase;margin-bottom:.5rem}}
.product-price{{font-size:1rem;color:var(--acc)}}

/* ── Features ── */
.features-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1px;background:var(--border);margin-top:4rem}}
.feature{{background:var(--bg);padding:3rem 2.5rem;transition:background .3s}}
.feature:hover{{background:var(--bg2)}}
.feature-num{{font-family:'Playfair Display',serif;font-size:3rem;color:var(--border);margin-bottom:1rem;line-height:1}}
.feature h3{{font-family:'Playfair Display',serif;font-size:1.4rem;margin-bottom:1rem}}
.feature p{{color:var(--dim);font-size:.9rem;line-height:1.8}}

/* ── CTA Section ── */
.cta-section{{text-align:center;background:linear-gradient(135deg,rgba(200,169,110,.06),rgba(139,92,246,.06));border-top:1px solid var(--border);border-bottom:1px solid var(--border)}}
.cta-section .section-title{{font-size:clamp(3rem,8vw,7rem)}}

/* ── Footer ── */
footer{{padding:3rem clamp(1.5rem,6vw,8rem);border-top:1px solid var(--border);display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:2rem}}
.footer-brand{{font-family:'Playfair Display',serif;font-size:1.1rem;color:var(--acc)}}
.footer-links{{display:flex;gap:2rem;justify-content:center}}
.footer-links a{{color:var(--dim);text-decoration:none;font-size:.8rem;letter-spacing:.15em;text-transform:uppercase;transition:color .2s}}
.footer-links a:hover{{color:var(--fg)}}
.footer-copy{{text-align:right;font-size:.75rem;color:var(--dim)}}

/* ── Responsive ── */
@media(max-width:768px){{
  nav,nav.scrolled{{padding:1rem 1.5rem}}
  .nav-links{{display:none}}
  .hero{{padding:0 1.5rem}}
  footer{{grid-template-columns:1fr;text-align:center}}
  .footer-copy{{text-align:center}}
}}
</style>
</head>
<body>

<div id="loader"><span class="loader-text">Loading</span></div>
<div id="cursor"></div>
<div id="cursor-ring"></div>

<nav id="nav">
  <a class="nav-logo" href="#">{topic.split()[0].upper()}</a>
  <ul class="nav-links">
    <li><a href="#products">Collection</a></li>
    <li><a href="#features">Craftsmanship</a></li>
    <li><a href="#about">About</a></li>
    <li><a href="#contact">Contact</a></li>
  </ul>
</nav>

<section class="hero" id="home">
  <div class="hero-bg"></div>
  <div class="hero-noise"></div>
  <div class="hero-content">
    <span class="hero-eyebrow">Est. {yr} · Crafted to Perfection</span>
    <h1 class="hero-title">
      The Art<br>of <em>{topic.split()[0].title()}</em>
    </h1>
    <p class="hero-sub">
      Where precision engineering meets timeless design.
      Every detail, intentional. Every moment, extraordinary.
    </p>
    <a href="#products" class="hero-cta">
      Explore Collection
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
    </a>
  </div>
  <div class="scroll-indicator">
    <span style="font-size:.65rem;letter-spacing:.3em;text-transform:uppercase">Scroll</span>
    <div class="scroll-line"></div>
  </div>
</section>

<section id="products" class="products">
  <div>
    <span class="section-label reveal">The Collection</span>
    <h2 class="section-title reveal">{topic.title()}<br><em style="font-style:italic;color:var(--acc)">Refined</em></h2>
    <div class="products-grid">
      {''.join(f'''
      <div class="product-card reveal">
        <div class="product-visual">
          <div class="product-shape"></div>
        </div>
        <div class="product-info">
          <div class="product-name">{topic.split()[0].title()} {s}</div>
          <div class="product-detail">{mat} · Limited Edition</div>
          <div class="product-price">${price}</div>
        </div>
      </div>''' for s, mat, price in [
        ("Noir", "Black Steel", "4,200"),
        ("Blanc", "White Gold", "6,800"),
        ("Azure", "Titanium", "5,500"),
        ("Obsidian", "Carbon Fibre", "7,900"),
      ])}
    </div>
  </div>
</section>

<section id="features">
  <span class="section-label reveal">Why Choose Us</span>
  <h2 class="section-title reveal">Craftsmanship<br>Without Compromise</h2>
  <div class="features-grid">
    <div class="feature reveal"><div class="feature-num">01</div><h3>Precision Engineering</h3><p>Every component is engineered to tolerances measured in microns, ensuring perfect performance for generations.</p></div>
    <div class="feature reveal"><div class="feature-num">02</div><h3>Heritage Materials</h3><p>Only the finest materials — titanium, sapphire crystal, 18k gold — are selected for their lasting beauty.</p></div>
    <div class="feature reveal"><div class="feature-num">03</div><h3>Limited Editions</h3><p>Each piece is numbered and certified, making it not just a purchase but a rare acquisition.</p></div>
    <div class="feature reveal"><div class="feature-num">04</div><h3>Lifetime Service</h3><p>Your investment is protected. Complimentary servicing and a lifetime guarantee come standard.</p></div>
  </div>
</section>

<section id="about" class="cta-section">
  <span class="section-label reveal">Our Story</span>
  <h2 class="section-title reveal">Built for<br><em style="font-style:italic;color:var(--acc)">Eternity</em></h2>
  <p class="reveal" style="max-width:600px;margin:0 auto 3rem;color:var(--dim);font-size:1.1rem;line-height:1.8">
    Since our founding, we have believed that true luxury lies in the details invisible to most —
    the weight of a case, the sweep of a hand, the silence between ticks.
  </p>
  <a href="#contact" class="hero-cta reveal">Begin Your Journey</a>
</section>

<footer id="contact">
  <div class="footer-brand">{topic.split()[0].upper()}</div>
  <div class="footer-links">
    <a href="#">Instagram</a>
    <a href="#">Contact</a>
    <a href="#">Privacy</a>
  </div>
  <div class="footer-copy">© {yr} {topic.title()}. Built by A.L.I</div>
</footer>

<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/ScrollTrigger.min.js"></script>
<script>
// ── Loader ──
window.addEventListener('load', () => {{
  setTimeout(() => document.getElementById('loader').classList.add('hidden'), 800);
}});

// ── Custom Cursor ──
const cur = document.getElementById('cursor');
const ring = document.getElementById('cursor-ring');
let mx = 0, my = 0, rx = 0, ry = 0;
document.addEventListener('mousemove', e => {{
  mx = e.clientX; my = e.clientY;
  cur.style.left = mx + 'px';
  cur.style.top  = my + 'px';
}});
(function animRing() {{
  rx += (mx - rx) * 0.12;
  ry += (my - ry) * 0.12;
  ring.style.left = rx + 'px';
  ring.style.top  = ry + 'px';
  requestAnimationFrame(animRing);
}})();
document.querySelectorAll('a, button, .product-card').forEach(el => {{
  el.addEventListener('mouseenter', () => {{
    cur.style.width = '20px'; cur.style.height = '20px';
    ring.style.width = '60px'; ring.style.height = '60px';
    ring.style.opacity = '1';
  }});
  el.addEventListener('mouseleave', () => {{
    cur.style.width = '12px'; cur.style.height = '12px';
    ring.style.width = '40px'; ring.style.height = '40px';
    ring.style.opacity = '.6';
  }});
}});

// ── Nav scroll effect ──
const nav = document.getElementById('nav');
window.addEventListener('scroll', () => {{
  nav.classList.toggle('scrolled', window.scrollY > 60);
}});

// ── GSAP Scroll Reveals ──
gsap.registerPlugin(ScrollTrigger);
document.querySelectorAll('.reveal').forEach(el => {{
  gsap.fromTo(el,
    {{ opacity: 0, y: 60 }},
    {{
      opacity: 1, y: 0,
      duration: 1, ease: 'power3.out',
      scrollTrigger: {{ trigger: el, start: 'top 85%', toggleActions: 'play none none none' }}
    }}
  );
}});

// ── Product card 3D tilt ──
document.querySelectorAll('.product-card').forEach(card => {{
  card.addEventListener('mousemove', e => {{
    const r = card.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width  - .5;
    const y = (e.clientY - r.top)  / r.height - .5;
    card.style.transform = `perspective(800px) rotateY(${{x * 10}}deg) rotateX(${{-y * 10}}deg)`;
  }});
  card.addEventListener('mouseleave', () => {{
    card.style.transform = 'perspective(800px) rotateY(0) rotateX(0)';
    card.style.transition = 'transform .5s ease';
  }});
}});

// ── Smooth scroll ──
document.querySelectorAll('a[href^="#"]').forEach(a => {{
  a.addEventListener('click', e => {{
    e.preventDefault();
    document.querySelector(a.getAttribute('href'))?.scrollIntoView({{behavior:'smooth'}});
  }});
}});
</script>
</body>
</html>"""


# ── Main Entry ─────────────────────────────────────────────────────────────────

def website_builder(parameters: dict, player=None, speak=None) -> str:
    topic  = parameters.get("topic", "luxury brand website")
    style  = parameters.get("style", "dark luxury minimalist")
    pages  = parameters.get("pages") or ["index"]
    if isinstance(pages, str):
        pages = [p.strip() for p in pages.split(",")]

    slug = re.sub(r'[^a-z0-9]+', '_', topic.lower())[:40]
    base = Path(parameters.get("output_dir") or
                Path.home() / "Desktop" / "ali_sites" / slug)
    base.mkdir(parents=True, exist_ok=True)

    log = BuildLog(base / "build_log.txt")

    def say(msg):
        if speak:
            try: speak(msg)
            except Exception: pass
        if player:
            try: player.write_log(f"WEB: {msg}")
            except Exception: pass

    # Load API key
    try:
        api_key_path = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
        api_key = json.loads(api_key_path.read_text())["gemini_api_key"]
    except Exception as e:
        log.add(f"API key error: {e}")
        return "Cannot build — API key not found."

    say(f"On it, Ali. Building a premium {style} website for {topic}. "
        f"I'll research Awwwards first, then build the full site.")

    # ── Phase 1: Scrape Awwwards ──
    log.add("═══ PHASE 1: RESEARCHING AWWWARDS.COM ═══")
    say("Opening Awwwards.com for design inspiration...")
    try:
        sites = asyncio.run(_scrape_awwwards(log))
        log.add(f"Research complete — {len(sites)} reference sites collected")
    except Exception as e:
        log.add(f"Scrape error: {e}")
        sites = []

    # ── Phase 2: Design Analysis ──
    log.add("═══ PHASE 2: ANALYZING DESIGN PATTERNS ═══")
    say("Analyzing award-winning design patterns...")
    design_brief = _analyze_with_gemini(sites, topic, style, api_key, log)
    log.add("Design brief ready. Here's a summary:")
    for line in design_brief.split('\n')[:5]:
        if line.strip():
            log.add(f"  {line.strip()}")

    # ── Phase 3: Generate Code ──
    log.add("═══ PHASE 3: GENERATING WEBSITE CODE ═══")
    say("Generating the full website with animations, products, and effects. This takes about 30 seconds...")
    files = _generate_html(topic, style, pages, design_brief, api_key, log)

    # ── Phase 4: Write Files ──
    log.add("═══ PHASE 4: WRITING FILES ═══")
    written = []
    if files:
        for fname, content in files.items():
            out = base / fname
            out.write_text(content, encoding="utf-8")
            written.append(fname)
            log.add(f"Wrote {fname} ({len(content):,} chars)")
    else:
        log.add("Gemini output could not be parsed — using premium fallback template")
        html = _build_fallback(topic, style)
        (base / "index.html").write_text(html, encoding="utf-8")
        written = ["index.html"]
        log.add(f"Wrote fallback index.html ({len(html):,} chars)")

    # ── Phase 5: Serve & Open ──
    log.add("═══ PHASE 5: LAUNCHING LOCAL SERVER ═══")
    port = _find_free_port()
    _serve(str(base), port)
    time.sleep(0.6)
    url = f"http://localhost:{port}/index.html"
    _open_browser(url)
    log.add(f"Server running at {url}")
    log.add(f"Build log saved at: {base / 'build_log.txt'}")
    log.add("═══ BUILD COMPLETE ═══")

    say(f"Done, Ali! Your {topic} website is open in the browser. "
        f"It has {len(written)} page(s) with animations, product section, and custom cursor. "
        f"If you want to see exactly what I did, just ask me to show the build log.")

    return (f"Website built at {base}\n"
            f"URL: {url}\n"
            f"Files: {', '.join(written)}\n"
            f"Log: {base / 'build_log.txt'}")
