import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from html_utils import generate_html_report


def test_generate_html_report_creates_themed_content(tmp_path):
    analysis_text = "## Strategy\n\nتاپیک اصلی\n\n### Detail\n\nمتن جزئیات"
    image_file = tmp_path / "result.png"
    image_file.write_text("PNG FAKE", encoding="utf-8")

    output_path = generate_html_report(
        analysis_text=analysis_text,
        user_name="نوآور",
        test_name="تست استعداد",
        output_dir=str(tmp_path),
        image_path=str(image_file),
        image_caption="کاور تصویر",
    )

    assert output_path is not None
    print(f"Generated HTML report: {output_path}")
    rendered = Path(output_path).read_text(encoding="utf-8")

    assert "hero-card" in rendered
    assert "slider-track" in rendered
    assert "hero-image" in rendered
    # Check that image is embedded as base64
    assert "data:image/png;base64" in rendered
    assert 'src="data:image/png;base64,' in rendered

    toc_items = rendered.count('class="toc-item"')
    assert toc_items == 1