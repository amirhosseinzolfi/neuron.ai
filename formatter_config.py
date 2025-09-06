"""
Configuration for Telegram Formatter
Contains settings and customization options for the advanced formatter
"""

# Visual Configuration
VISUAL_CONFIG = {
    # Box drawing characters for different styles
    'box_styles': {
        'simple': {
            'top_left': '┌',
            'top_right': '┐',
            'bottom_left': '└',
            'bottom_right': '┘',
            'horizontal': '─',
            'vertical': '│'
        },
        'double': {
            'top_left': '╔',
            'top_right': '╗',
            'bottom_left': '╚',
            'bottom_right': '╝',
            'horizontal': '═',
            'vertical': '║'
        },
        'rounded': {
            'top_left': '╭',
            'top_right': '╮',
            'bottom_left': '╰',
            'bottom_right': '╯',
            'horizontal': '─',
            'vertical': '│'
        }
    },
    
    # Default style preferences
    'default_box_style': 'simple',
    'separator_length': 30,
    'progress_bar_length': 10,
    'indent_size': 2,
    
    # RTL text preferences
    'rtl_alignment': True,
    'persian_numbers': True,
    'enhanced_spacing': True
}

# Content Type Specific Settings
CONTENT_SETTINGS = {
    'analysis': {
        'max_header_level': 3,
        'show_progress_bars': True,
        'highlight_key_points': True,
        'add_visual_separators': True
    },
    'question': {
        'show_question_counter': True,
        'highlight_question_box': True,
        'show_options_list': True,
        'add_instruction_text': True
    },
    'acknowledgment': {
        'show_user_response': True,
        'highlight_response': True,
        'add_psychological_note': True
    },
    'error': {
        'show_error_icon': True,
        'provide_suggestions': True,
        'add_help_text': True
    }
}

# Personality Test Specific Settings
PSYCHOLOGY_SETTINGS = {
    # Different personality traits and their associated emojis
    'trait_emojis': {
        'extraversion': '🌟',
        'introversion': '🌙',
        'openness': '🌈',
        'conscientiousness': '🎯',
        'agreeableness': '🤝',
        'neuroticism': '⚡',
        'thinking': '🧠',
        'feeling': '❤️',
        'sensing': '👁️',
        'intuition': '✨',
        'judging': '📋',
        'perceiving': '🔄'
    },
    
    # Score ranges and their descriptions
    'score_ranges': {
        'very_low': (0, 20),
        'low': (21, 40),
        'moderate': (41, 60),
        'high': (61, 80),
        'very_high': (81, 100)
    },
    
    # Colors for progress bars (using Unicode block characters)
    'progress_colors': {
        'very_low': '░',
        'low': '▒',
        'moderate': '▓',
        'high': '█',
        'very_high': '█'
    }
}

# Language and Localization
LANGUAGE_CONFIG = {
    'primary_language': 'persian',
    'rtl_support': True,
    'number_conversion': True,
    
    # Common phrases in Persian
    'phrases': {
        'continued': 'ادامه دارد...',
        'part_of': 'بخش {} از {}',
        'your_answer': 'پاسخ شما',
        'question': 'سوال',
        'analysis': 'تحلیل',
        'result': 'نتیجه',
        'score': 'امتیاز',
        'level': 'سطح',
        'recommendation': 'توصیه'
    }
}

# Performance Settings
PERFORMANCE_CONFIG = {
    'chunk_size': 4000,
    'max_caption_length': 1000,
    'processing_delay': 0.6,
    'error_retry_attempts': 2,
    'fallback_enabled': True
}

# Feature Toggles
FEATURE_FLAGS = {
    'enhanced_emojis': True,
    'progress_bars': True,
    'visual_boxes': True,
    'color_coding': True,
    'rtl_optimization': True,
    'smart_chunking': True,
    'auto_formatting': True,
    'context_aware': True
}
