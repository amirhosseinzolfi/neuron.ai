import unittest
import json
from unittest.mock import patch, MagicMock

# Ensure ai_utils can be imported. If your project structure requires, adjust Python path.
# For example, if tests are in a 'tests' subdirectory:
# import sys
# sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from ai_utils import summarize_results, RESULT_CHATBOT_PERSONA, ANALYSIS_SUMMARY_PROMPT
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage


class TestSummarizeResults(unittest.TestCase):

    def setUp(self):
        self.sample_state_with_report_md = {
            "user_name": "تست کاربر",
            "user_age": 30,
            "test_data": {
                "result_format": {
                    "report_md": "## نتایج آزمون {{test_name}} برای {{user_name}}\n\n**سن:** {{age}}\n\n### خلاصه پاسخ‌ها:\n{{formatted_answers}}\n\n### تحلیل:\nاین یک تحلیل نمونه بر اساس قالب Markdown است."
                }
            },
            "history_summary": "User seemed engaged and thoughtful."
        }

        self.sample_state_without_report_md = {
            "user_name": "تست کاربر دیگر",
            "user_age": 25,
            "test_data": {
                "result_format": {
                    "title_template": "گزارش شخصیت برای {{user_name}}",
                    "sections": ["مقدمه", "تحلیل اصلی", "نتیجه گیری"]
                }
            },
            "history_summary": "User was concise."
        }

        self.sample_results = {
            "test_name": "تست نمونه MBTI",
            "answers": [
                {"question": "سوال ۱", "selected_option": "گزینه الف", "user_response": "پاسخ کاربر به سوال ۱"},
                {"question": "سوال ۲", "selected_option": "گزینه ب", "user_response": "پاسخ کاربر به سوال ۲"}
            ]
        }
        self.expected_llm_response_content = "این یک تحلیل تولید شده توسط LLM است."

    @patch('ai_utils.result_llm.invoke')
    def test_summarize_results_with_report_md(self, mock_invoke):
        # Configure the mock to return a specific AIMessage
        mock_invoke.return_value = AIMessage(content=self.expected_llm_response_content)

        analysis = summarize_results(self.sample_state_with_report_md, self.sample_results)

        self.assertEqual(analysis, self.expected_llm_response_content)
        
        # Check that the LLM was called
        mock_invoke.assert_called_once()
        
        # Verify the structure of the call (Langchain messages)
        args, _ = mock_invoke.call_args
        messages = args[0]
        self.assertIsInstance(messages[0], SystemMessage)
        self.assertEqual(messages[0].content, RESULT_CHATBOT_PERSONA)
        self.assertIsInstance(messages[1], HumanMessage)

        # Verify that the report_md template was correctly passed into the prompt
        formatted_answers_json = json.dumps([
            {"question": "سوال ۱", "selected_option": "گزینه الف", "user_response": "پاسخ کاربر به سوال ۱"},
            {"question": "سوال ۲", "selected_option": "گزینه ب", "user_response": "پاسخ کاربر به سوال ۲"}
        ], indent=2, ensure_ascii=False)
        
        expected_prompt_content = ANALYSIS_SUMMARY_PROMPT.format(
            test_name=self.sample_results["test_name"],
            user_name=self.sample_state_with_report_md["user_name"],
            user_age=self.sample_state_with_report_md["user_age"],
            formatted_answers=formatted_answers_json,
            test_result_format=self.sample_state_with_report_md["test_data"]["result_format"]["report_md"]
        )
        self.assertEqual(messages[1].content, expected_prompt_content)

    @patch('ai_utils.result_llm.invoke')
    def test_summarize_results_without_report_md(self, mock_invoke):
        mock_invoke.return_value = AIMessage(content=self.expected_llm_response_content)

        analysis = summarize_results(self.sample_state_without_report_md, self.sample_results)

        self.assertEqual(analysis, self.expected_llm_response_content)
        mock_invoke.assert_called_once()
        
        args, _ = mock_invoke.call_args
        messages = args[0]
        self.assertIsInstance(messages[0], SystemMessage)
        self.assertEqual(messages[0].content, RESULT_CHATBOT_PERSONA)
        self.assertIsInstance(messages[1], HumanMessage)

        formatted_answers_json = json.dumps([
            {"question": "سوال ۱", "selected_option": "گزینه الف", "user_response": "پاسخ کاربر به سوال ۱"},
            {"question": "سوال ۲", "selected_option": "گزینه ب", "user_response": "پاسخ کاربر به سوال ۲"}
        ], indent=2, ensure_ascii=False)
        
        # When report_md is not present, the full result_format object (as JSON string) is passed
        expected_test_result_format_json = json.dumps(
            self.sample_state_without_report_md["test_data"]["result_format"], 
            indent=2, 
            ensure_ascii=False
        )
        
        expected_prompt_content = ANALYSIS_SUMMARY_PROMPT.format(
            test_name=self.sample_results["test_name"],
            user_name=self.sample_state_without_report_md["user_name"],
            user_age=self.sample_state_without_report_md["user_age"],
            formatted_answers=formatted_answers_json,
            test_result_format=expected_test_result_format_json
        )
        self.assertEqual(messages[1].content, expected_prompt_content)

if __name__ == '__main__':
    unittest.main()
