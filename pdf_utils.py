import logging
from pathlib import Path

import markdown2
from weasyprint import HTML

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
def generate_pdf(
    summary_md,
    user_name,
    user_age,
    test_name,
    output_path,
    css_path=None,
    image_path=None,
):
    """
    Generate a styled RTL PDF from a markdown summary, using refined modern layout.

    :param summary_md: The test summary in Markdown format.
    :param user_name:  The name of the user.
    :param user_age:   The age of the user.
    :param test_name:  The title of the test.
    :param output_path: Where to write the resulting PDF.
    :param css_path:   Optional path to a custom CSS file.
    :param image_path: Optional path to an image to include at the top of the PDF.
    :return:           Path to the generated PDF.
    """
    # Prepare filesystem path
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Sanitize inputs
    user_name = str(user_name) if user_name else "کاربر گرامی"
    user_age = int(user_age) if user_age else 0
    test_name = str(test_name) if test_name else "تست روانشناسی"
    summary_md = str(summary_md) if summary_md else "نتایج تست"

    # Use raw text; Pango handles shaping when font + dir=rtl are set
    label_name = "نام"
    label_age = "سن"

    # Build header WITHOUT user info (AI will include user details in content)
    header_html = f"""
    <div class=\"header-container\">
      <h1>{test_name}</h1>
    </div>
    """
    
    # Embed hero image AFTER header (base64) if provided
    image_section = ""
    if image_path and Path(image_path).exists():
        try:
            import base64
            with open(image_path, "rb") as img_file:
                img_data = base64.b64encode(img_file.read()).decode("utf-8")
            img_ext = Path(image_path).suffix.lower().lstrip(".")
            if img_ext == "jpg":
                img_ext = "jpeg"
            image_section = (
                f"<div class=\"hero-image-container\">"
                f"<img src=\"data:image/{img_ext};base64,{img_data}\" alt=\"نتیجه تست\" class=\"hero-image\"/>"
                f"</div>"
            )
        except Exception as img_e:
            logger.warning(f"Failed to embed image: {img_e}")

    # Convert markdown to HTML
    try:
        body_html = markdown2.markdown(
            summary_md,
            extras=["fenced-code-blocks", "tables", "strike", "cuddled-lists"],
        )
    except Exception as e:
        logger.error(f"Error converting markdown to HTML: {e}")
        body_html = f"<p>{summary_md}</p>"

    # Load CSS
    if css_path:
        css_file = Path(css_path)
        if css_file.is_file():
            css = css_file.read_text(encoding="utf-8")
        else:
            logger.warning(f"CSS file not found at {css_file}, falling back to embedded default.")
            css = _default_css()
    else:
        default_css_file = Path(__file__).parent / "assets" / "pdf_style.css"
        if default_css_file.is_file():
            css = default_css_file.read_text(encoding="utf-8")
        else:
            logger.warning(
                f"Default CSS not found at {default_css_file}, using built-in styles."
            )
            css = _default_css()

    # Assemble and render (image placed AFTER header, BEFORE content)
    html = f"""
    <!DOCTYPE html>
    <html lang=\"fa\" dir=\"rtl\">
      <head>
        <meta charset=\"utf-8\">
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
        <title>{test_name} - {user_name}</title>
        <style>{css}</style>
      </head>
      <body>
        <div class=\"container\">
          {header_html}
          {image_section}
          <div class=\"content\">{body_html}</div>
        </div>
      </body>
    </html>
    """

    HTML(string=html).write_pdf(str(output_path))
    logger.info(f"PDF generated successfully at: {output_path.resolve()}")
    return output_path


def _default_css() -> str:
    """Returns embedded CSS matching refined modern style"""
    return Path(__file__).parent.joinpath('assets', 'pdf_style.css').read_text(encoding="utf-8")
