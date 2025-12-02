"""
Telegram text optimizer for converting Markdown formatted text into
attractive Telegram-friendly messages with emojis and proper formatting.
"""

import re
from typing import List, Tuple

# Mapping of Markdown patterns to Telegram-friendly formats
HEADER_PATTERNS = [
    (r'^# (.+)$', '🔷 <b>\g<1></b>', 'main header'),
    (r'^## (.+)$', '💠 <b>\g<1></b>', 'subheader'),
    (r'^### (.+)$', '🔹 <b>\g<1></b>', 'sub-subheader'),
]

LIST_PATTERNS = [
    (r'^\* (.+)$', '• \g<1>', 'unordered list'),
    (r'^- (.+)$', '• \g<1>', 'unordered list dash'),
    (r'^\+ (.+)$', '• \g<1>', 'unordered list plus'),
    (r'^\d+\. (.+)$', '🔸 \g<1>', 'ordered list'),
]

EMPHASIS_PATTERNS = [
    (r'\*\*(.+?)\*\*', '<b>\g<1></b>', 'bold'),
    (r'\*(.+?)\*', '<i>\g<1></i>', 'italic'),
    (r'`(.+?)`', '<code>\g<1></code>', 'code'),
]

SECTION_INDICATORS = {
    'نتیجه': '📊',
    'تحلیل': '🔍',
    'توصیه': '💡',
    'نقاط قوت': '✨',
    'نقاط ضعف': '⚠️',
    'پیشنهادات': '💭',
    'خلاصه': '📝',
    'مقدمه': '🎯',
    'ویژگی‌های شخصیتی': '👤',
}

def optimize_section_headers(text: str) -> str:
    """Add relevant emojis to known section headers."""
    for keyword, emoji in SECTION_INDICATORS.items():
        # Match headers like '# تحلیل' or 'تحلیل:'
        text = re.sub(
            f'(?m)^(#+ )?({keyword}:?)',
            f'{emoji} <b>\g<2></b>',
            text
        )
    return text

def apply_patterns(text: str, patterns: List[Tuple[str, str, str]]) -> str:
    """Apply a list of regex patterns with their replacements."""
    for pattern, replacement, _ in patterns:
        text = re.sub(pattern, replacement, text, flags=re.MULTILINE)
    return text

def optimize_for_telegram(markdown_text: str) -> str:
    """
    Convert Markdown text into an optimized Telegram-friendly format.
    
    Args:
        markdown_text: Input text in Markdown format
        
    Returns:
        Telegram-optimized text with emojis and proper formatting
    """
    if not markdown_text:
        return ""
    
    # Split the text into paragraphs based on blank lines
    paragraphs = re.split(r'\n\s*\n', markdown_text.strip())
    
    processed_paragraphs = []
    for para in paragraphs:
        if not para.strip():
            continue

        # Process each line within the paragraph
        lines = para.strip().split('\n')
        processed_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Apply patterns in order
            line = optimize_section_headers(line)
            line = apply_patterns(line, HEADER_PATTERNS)
            line = apply_patterns(line, LIST_PATTERNS)
            line = apply_patterns(line, EMPHASIS_PATTERNS)
            
            # Final cleanup of any remaining Markdown symbols for this line
            line = re.sub(r'[#_*`]', '', line)
            processed_lines.append(line)
        
        # Rejoin lines of a paragraph with single newlines
        processed_paragraphs.append('\n'.join(processed_lines))

    # Join paragraphs with double newlines for separation
    text = '\n\n'.join(processed_paragraphs)
    
    return text.strip()

def format_analysis_for_telegram(analysis: str) -> str:
    """
    Special formatter for psychological analysis results.
    
    Args:
        analysis: Raw analysis text (potentially in Markdown)
        
    Returns:
        Formatted text optimized for Telegram display
    """
    # Apply general Markdown optimization
    text = optimize_for_telegram(analysis)
    
    return text

