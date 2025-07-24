import logging
from pathlib import Path

import markdown2
from weasyprint import HTML

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_pdf(
    summary_md: str,
    user_name: str,
    user_age: int,
    test_name: str,
    output_path: Path | str,
    css_path: Path | str | None = None,
) -> Path:
    """
    Generate a styled RTL PDF from a markdown summary, using refined modern layout.

    :param summary_md: The test summary in Markdown format.
    :param user_name:  The name of the user.
    :param user_age:   The age of the user.
    :param test_name:  The title of the test.
    :param output_path: Where to write the resulting PDF.
    :param css_path:   Optional path to a custom CSS file.
    :return:           Path to the generated PDF.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Refined header container with curved bottom
    header_html = f"""
    <div class="header-container">
      <h1>{test_name}</h1>
      <div class="user-info highlight-container">
        <p>👤 نام: <strong>{user_name}</strong> | 🎂 سن: <strong>{user_age}</strong></p>
      </div>
    </div>
    """

    # Convert markdown to HTML body
    body_html = markdown2.markdown(
        summary_md,
        extras=["fenced-code-blocks", "tables", "strike", "cuddled-lists"]
    )

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
            logger.warning(f"Default CSS not found at {default_css_file}, using built-in styles.")
            css = _default_css()

    # Assemble full HTML with RTL support
    html = f"""
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{test_name} - {user_name}</title>
        <style>{css}</style>
      </head>
      <body>
        <div class="container">
          {header_html}
          <div class="content">
            {body_html}
          </div>
        </div>
      </body>
    </html>
    """

    # Generate PDF file
    HTML(string=html).write_pdf(str(output_path))
    logger.info(f"PDF generated at: {output_path.resolve()}")
    return output_path


def _default_css() -> str:
    """Returns embedded CSS matching refined modern style"""
    return Path(__file__).parent.joinpath('assets', 'pdf_style.css').read_text(encoding="utf-8")
