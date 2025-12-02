import base64
import logging
import time
import hashlib
from pathlib import Path
from typing import Optional
import markdown2

LOG = logging.getLogger(__name__)

def generate_html_report(
    analysis_text: str,
    user_name: str,
    test_name: str,
    conversation_history: list = None,
    conversation_summary: str = None,
    output_dir: str = "html_reports",
    image_path: str = None,
    image_caption: str = None,
) -> Optional[str]:
    """Generate HTML report with table of contents navigation."""
    try:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = int(time.time())
        hash_suffix = hashlib.md5(f"{user_name}{timestamp}".encode()).hexdigest()[:6]
        filename = f"result_report_{timestamp}_{hash_suffix}.html"
        file_path = output_path / filename
        
        # Convert markdown to HTML
        try:
            analysis_html = markdown2.markdown(
                analysis_text,
                extras=["fenced-code-blocks", "tables", "header-ids"]
            )
        except Exception as e:
            LOG.warning(f"Markdown conversion failed: {e}")
            analysis_html = f"<div>{analysis_text}</div>"
        
        # Extract headings for TOC
        import re
        headings = re.findall(r'<h([2-3])[^>]*id="([^"]+)"[^>]*>([^<]+)</h\1>', analysis_html)
        toc_html = _build_toc(headings)
        
        from datetime import datetime
        formatted_date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")
        image_markup = ""
        if image_path:
            try:
                image_source = Path(image_path)
                if image_source.exists():
                    data = base64.b64encode(image_source.read_bytes()).decode('utf-8')
                    extension = image_source.suffix.lower().lstrip('.')
                    mime_map = {
                        'png': 'image/png',
                        'jpg': 'image/jpeg',
                        'jpeg': 'image/jpeg',
                        'webp': 'image/webp',
                        'gif': 'image/gif'
                    }
                    mime_type = mime_map.get(extension, 'image/png')
                    data_url = f"data:{mime_type};base64,{data}"
                    if image_caption:
                        image_markup = (
                            f'<figure class="hero-figure"><img src="{data_url}" alt="تصویر نتیجه" class="hero-image" />'
                            f"<figcaption>{image_caption}</figcaption></figure>"
                        )
                    else:
                        image_markup = f'<img src="{data_url}" alt="تصویر نتیجه" class="hero-image" />'
                else:
                    LOG.warning(f"Image file not found: {image_path}")
            except Exception as e:
                LOG.error(f"Failed to embed image: {e}")
                image_markup = f'<img src="{image_path}" alt="تصویر نتیجه" class="hero-image" />'
        
        html_content = f"""<!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>{test_name} — {user_name}</title>
    <style>{_get_html_styles()}</style>
    </head>
    <body>
    <div class="page-shell">
    <aside class="toc">
    <div class="slider-track">
    <span class="slider-handle"></span>
    </div>
    <div class="toc-header">
    <h3>📋 فهرست</h3>
    <p>فقط عنوان‌های اصلی نمایش داده می‌شوند</p>
    </div>
    <div class="toc-body">
    {toc_html}
    </div>
    </aside>
    <main>
    <section class="hero">
    <div class="hero-card">
    <p class="eyebrow">خلاصه نتایج</p>
    <h1>{user_name}</h1>
    <div class="badge">{test_name}</div>
    <p class="hero-text">این نمای کلی بر اساس داده‌های شما منظم شده و چشم‌انداز آینده را با جزئیاتی روشن نشان می‌دهد.</p>
    <div class="meta">📅 {formatted_date}</div>
    </div>
    <div class="hero-visual">
    {image_markup}
    </div>
    </section>
    <article>{analysis_html}</article>
    </main>
    </div>
    </body>
    </html>"""
        
        file_path.write_text(html_content, encoding="utf-8")
        LOG.info(f"✅ HTML report generated: {file_path}")
        return str(file_path)
        
    except Exception as e:
        LOG.error(f"Failed to generate HTML report: {e}")
        return None


def _build_toc(headings: list) -> str:
    """Build table of contents from headings."""
    if not headings:
        return '<div class="toc-empty">بدون بخش</div>'
    
    items = []
    for level, id_attr, text in headings:
        if level != "2":
            continue
        items.append(f'<a href="#{id_attr}" class="toc-item">{text}</a>')
    
    return '\n'.join(items)


def _get_html_styles() -> str:
    """Return minimal modern dark theme CSS."""
    return """@import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazir-font@v30.1.0/dist/font-face.css');
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Vazir',Tahoma,sans-serif;background:#f0f4f8;color:#1a2332;min-height:100vh}
h1,h2,h3{font-weight:600}
div{direction:rtl}
a{text-decoration:none}
figure{margin:0}
p{line-height:1.7}
body .page-shell{display:flex;min-height:100vh;background:linear-gradient(180deg,#dfeefb 0,#f6f8fd 40%,#fff 70%);padding:0 3vw}
body .page-shell main{flex:1;padding:2.5rem 2rem 3rem;max-width:1200px;margin:0 auto}
body .page-shell .hero{display:flex;flex-direction:row;gap:2rem;margin-bottom:2rem;position:relative;background:linear-gradient(135deg,#fff,#e8f4f8);border-radius:24px;padding:2rem;box-shadow:0 20px 60px rgba(15,35,65,.08)}
.hero-visual{flex:0 0 280px;display:flex;align-items:center;justify-content:center}
.hero-figure{display:flex;flex-direction:column;align-items:center;gap:.6rem;width:100%}
.hero-figure figcaption{color:#61627b;font-size:.9rem;background:rgba(123,44,191,.1);padding:.5rem 1rem;border-radius:12px;font-weight:600}
.hero-image{width:100%;max-width:280px;height:auto;border-radius:16px;box-shadow:0 12px 35px rgba(15,35,65,.15);object-fit:cover}
.hero-card{flex:1;padding-right:1rem}
.hero-card .eyebrow{font-size:.9rem;color:#4d6fa3;text-transform:uppercase;letter-spacing:.2em;margin-bottom:.4rem}
.hero-card h1{font-size:2.5rem;color:#0f2141;margin-bottom:.4rem}
.hero-card .badge{display:inline-flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#7b2cbf,#9d4edd);color:#fff;padding:.6rem 1.1rem;border-radius:999px;font-size:.85rem;margin:.4rem 0;box-shadow:0 10px 24px rgba(123,44,191,.35)}
.hero-card .hero-text{color:#32415b;margin:1rem 0 1.2rem;font-size:1rem}
.hero-card .meta{color:#6a7695;font-size:.9rem}
.hero-card .hero-footer{display:flex;flex-wrap:wrap;gap:.8rem;margin-top:1.4rem;font-size:.95rem;color:#1f2a3d}
.hero-card .stroke-button{border:1px solid rgba(30,95,143,.2);border-radius:999px;padding:.5rem 1rem;color:#1f2a3d;font-weight:600;background:transparent}
.toc{width:240px;max-width:260px;background:rgba(255,255,255,.95);border-radius:20px 0 0 20px;padding:2rem 1.5rem 2.5rem;margin-right:auto;margin-left:0;align-self:flex-start;height:calc(100vh - 3rem);position:sticky;top:1.5rem;box-shadow:12px 12px 40px rgba(10,30,55,.12)}
.toc-header h3{font-size:1.1rem;color:#1a3a5a;margin-bottom:.3rem;font-weight:700}
.toc-header p{font-size:.78rem;color:#5a6a84;margin-top:0;letter-spacing:.05em;line-height:1.4}
.toc-body{margin-top:1.2rem;display:flex;flex-direction:column;gap:.4rem}
.toc-item{display:block;padding:.7rem 1rem;border-radius:10px;background:transparent;color:#2a3a4d;font-weight:500;transition:all .18s;font-size:.92rem;border-left:3px solid transparent}
.toc-item:hover{color:#7b2cbf;background:rgba(123,44,191,.08);transform:translateX(-4px);border-left-color:#7b2cbf}
.toc-empty{color:#6e7a94;font-size:.92rem;padding:.7rem 1rem;background:rgba(19,56,90,.05);border-radius:12px}
.slider-track{width:calc(100% - 2rem);height:8px;border-radius:999px;background:linear-gradient(90deg,#7b2cbf,#9d4edd);margin:-.5rem auto 1.5rem auto;position:relative;opacity:.75}
.slider-handle{position:absolute;top:-6px;left:35%;width:22px;height:22px;border-radius:50%;background:#fff;border:3px solid #7b2cbf;box-shadow:0 6px 15px rgba(123,44,191,.25)}
article{background:#fff;border-radius:20px;padding:2.5rem;box-shadow:0 15px 45px rgba(10,25,45,.06);line-height:1.75}
article h2{color:#1a2e48;font-size:1.75rem;margin:2.5rem 0 1rem;font-weight:700;border-bottom:3px solid transparent;border-image:linear-gradient(to left,#7b2cbf,#f3e5f5) 1;padding-bottom:.6rem;padding-right:.5rem;position:relative}
article h2::before{content:'';position:absolute;right:0;top:50%;transform:translateY(-50%);width:6px;height:70%;background:linear-gradient(180deg,#7b2cbf,#9d4edd);border-radius:3px}
article h3{color:#2a4060;font-size:1.3rem;margin:1.5rem 0 .6rem;font-weight:600}
article p{color:#4b5a70;margin:1rem 0;font-size:1.05rem}
article ul,article ol{padding-right:1.8rem;margin:1rem 0;line-height:1.8}
article li{margin:.6rem 0;font-size:1rem;color:#3b4659;position:relative}
article ul li::marker{color:#7b2cbf;font-size:1.1em}
article ol li::marker{color:#7b2cbf;font-weight:700}
article table{width:100%;border-collapse:separate;border-spacing:0;margin:1.5rem 0;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(15,35,65,.08)}
article table thead{background:linear-gradient(135deg,#7b2cbf,#9d4edd);color:#fff}
article table th{padding:1rem 1.2rem;text-align:right;font-weight:700;font-size:1rem;border-bottom:3px solid rgba(255,255,255,.2);letter-spacing:.02em}
article table tbody tr{background:#fff;transition:all .2s ease}
article table tbody tr:nth-child(even){background:#f8fafc}
article table tbody tr:hover{background:linear-gradient(90deg,#f3e5f5,#e1bee7);transform:translateX(-3px);box-shadow:0 3px 12px rgba(123,44,191,.15)}
article table td{padding:.9rem 1.2rem;text-align:right;border-bottom:1px solid #e8f0f8;color:#2a3a4d;font-size:.98rem}
article table tbody tr:last-child td{border-bottom:none}
article table td:first-child,article table th:first-child{border-right:4px solid #7b2cbf;font-weight:600}
article table caption{caption-side:top;padding:1rem;font-size:1.1rem;font-weight:700;color:#1a2e48;text-align:right;background:linear-gradient(90deg,#f3e5f5,transparent);border-radius:8px 8px 0 0;margin-bottom:.5rem}
article strong{color:#7b2cbf;font-weight:700}
article em{color:#5a6a84;font-style:italic;font-weight:500}
article code{background:#f2f4ff;color:#0f2141;padding:.2rem .5rem;border-radius:6px;font-size:.95rem}
article pre{background:#101c33;color:#f7fbff;padding:1rem;border-radius:12px;font-size:.9rem;overflow-x:auto}
article blockquote{margin:1.5rem 0;padding:1.2rem 1.5rem;background:linear-gradient(to left,#f3e5f5,#f8fafc);border-right:5px solid #7b2cbf;border-radius:0 12px 12px 0;color:#2a3a4d;font-style:italic;box-shadow:0 3px 15px rgba(123,44,191,.12)}
article blockquote p{margin:.5rem 0;color:#2a4060}
@media(max-width:1024px){.toc{position:relative;width:100%;border-radius:32px;margin:0 0 1.5rem}}
@media(max-width:768px){body .page-shell{flex-direction:column;align-items:center;padding:1.2rem}body .page-shell main{padding:1.5rem;max-width:100%}.hero{flex-direction:column;padding:1.5rem;gap:1.5rem}.hero-visual{flex:1;max-width:100%}.hero-image{max-width:100%}.toc{width:100%;height:auto;margin:0 0 1.5rem;padding:1.5rem;border-radius:16px}article{padding:1.8rem}}"""
