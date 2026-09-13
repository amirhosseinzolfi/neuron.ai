"""
Psychological Pattern Analyzer Skill
----------------------------------------------------------------------
Analyzes user statements or thought patterns to identify emotional valence,
cognitive distortions (خطاهای شناختی), and core psychological needs.
"""

from typing import Dict, Any
import json
from langchain_core.messages import SystemMessage, HumanMessage
from ai_utils import get_neuron_llm

ANALYZER_SYSTEM_PROMPT = """
شما یک تحلیل‌گر متخصص روانشناسی بالینی و شناختی-رفتاری (CBT) هستید.
وظیفه شما تحلیل گفته یا وضعیت ذهنی کاربر و استخراج موارد زیر در قالب یک خروجی معتبر JSON است:
{
  "emotional_tone": "حس یا هیجان غالب (مثل اضطراب، خشم، امیدواری، سردرگمی)",
  "cognitive_distortions": ["لیست خطاهای شناختی احتمالی مثل فاجعه‌سازی، تفکر همه یا هیچ، ذهن‌خوانی و..."],
  "core_need": "نیاز بنیادین روانی پشت این صحبت (مثل امنیت، پذیرش، استقلال)",
  "recommended_approach": "توصیه کوتاه برای نحوه برخورد و مداخله درمانی"
}
فقط و فقط یک آبجکت معتبر JSON خروجی دهید بدون هیچ متن یا تگ اضافی.
"""


def analyze_cognitive_patterns(text: str, user_profile: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Skill: Analyzes a given text for cognitive distortions and emotional tone.
    """
    if not text:
        return {}

    llm = get_neuron_llm()
    profile_ctx = f"\nپروفایل کاربر: {json.dumps(user_profile, ensure_ascii=False)}" if user_profile else ""

    messages = [
        SystemMessage(content=ANALYZER_SYSTEM_PROMPT),
        HumanMessage(content=f"متن ورودی کاربر برای تحلیل:{profile_ctx}\n\n{text}")
    ]

    try:
        response = llm.invoke(messages)
        content = response.content.strip()
        # Clean potential markdown formatting
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return json.loads(content.strip())
    except Exception as e:
        return {
            "emotional_tone": "نامشخص",
            "cognitive_distortions": [],
            "core_need": "پشتیبانی همدلانه",
            "recommended_approach": f"تحلیل مستقیم با خطا مواجه شد: {str(e)}"
        }

