"""Browser regression checks; run with Playwright and Chromium installed."""
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from playwright.sync_api import sync_playwright, Page
from browser import QUESTION_SELECTOR, norm, read_questions, select_random_options, submit_buttons, score_policy, random_score, fill_form


class QuestionBlocksTest(unittest.TestCase):
    def test_score_steps_and_endpoints(self):
        expected = [f'{value // 10},{value % 10}' for value in range(70, 95, 2)]
        with patch('browser.random.choice', side_effect=list(range(70, 95, 2))) as choose:
            self.assertEqual([random_score() for _ in range(13)], expected)
            self.assertEqual(list(choose.call_args.args[0]), list(range(70, 95, 2)))
        self.assertIsNone(score_policy({'question': '2.1. Điểm TSA/SPT/VSAT:', 'options': []}))
        self.assertIsNone(score_policy({'question': 'Môn khác', 'options': ['A', 'B']}))

    def test_fill_random_scores_and_leave_excluded_subjects_blank(self):
        subjects = ['Toán', 'Vật lí', 'Hoá học', 'Ngữ Văn', 'Tiếng Anh', 'Sinh học',
                    'Vẽ Mỹ thuật', 'Địa lý', 'Môn khác', 'Họ và tên']
        questions = [{'index': i, 'question': title, 'options': []} for i, title in enumerate(subjects)]
        html = ''.join(f'<div role="listitem"><div role="heading">{title}</div><input type="text"></div>' for title in subjects)
        captured = []
        def capture(page, **kwargs):
            captured.extend(page.locator('input').evaluate_all('els => els.map(el => el.value)'))
            return b''
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / 'form.html'
            fixture.write_text('<meta charset="utf-8">' + html, encoding='utf-8')
            # Explicit Excel mappings must not override the requested score rules.
            mapping = {str(i): title for i, title in enumerate(subjects)}
            data = {title: '10,0' for title in subjects}
            data['Họ và tên'] = 'Kiểm thử'
            with patch('browser.random.choice', side_effect=[70, 72, 74, 76, 78, 94]), patch.object(Page, 'screenshot', autospec=True, side_effect=capture):
                result = fill_form(fixture.as_uri(), data, questions, mapping, submit=False)
        self.assertEqual(result, ['Đang ở chế độ kiểm thử: chưa bấm Gửi.'])
        self.assertEqual(captured, ['7,0', '7,2', '7,4', '7,6', '7,8', '9,4', '', '', '', 'Kiểm thử'])

    def test_decomposed_vietnamese_submit_button(self):
        self.assertEqual(norm('Gư\u0309i'), norm('Gửi'))
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content('''<button aria-label="Gư\u0309i">Gư\u0309i</button>
                <button>Xóa hết câu trả lời</button><button disabled>Submit</button>
                <button style="display:none">Submit</button>''')
            buttons = submit_buttons(page)
            self.assertEqual(len(buttons), 1)
            self.assertEqual(norm(buttons[0].inner_text()), 'gửi')
            browser.close()

    def test_nested_checkbox_answers_are_not_questions(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content('''
                <div role="listitem"><div role="heading">Họ và tên</div><input type="text"></div>
                <div role="listitem"><div role="heading">Lĩnh vực quan tâm *</div>
                  <div role="listitem"><button role="checkbox" aria-label="Kinh tế" aria-checked="false">Kinh tế</button></div>
                  <div role="listitem"><button role="checkbox" aria-label="CNTT" aria-checked="false">CNTT</button></div>
                  <div role="listitem"><button role="checkbox" aria-label="Mục khác:" data-answer-value="__other_option__" aria-checked="false">Mục khác:</button><input type="text"></div>
                </div>
                <div role="listitem"><div role="heading">Yếu tố chọn trường *</div>
                  <div role="listitem"><button role="checkbox" aria-label="Học phí" aria-checked="false">Học phí</button></div>
                  <div role="listitem"><button role="checkbox" aria-label="Gia đình" aria-checked="false">Gia đình</button></div>
                </div>
                <div role="listitem"><div role="heading">Trắc nghiệm</div>
                  <button role="radio" aria-label="A" aria-checked="false">A</button>
                  <button role="radio" aria-label="B" aria-checked="false">B</button>
                </div>
                <script>
                  document.addEventListener('click', e => {
                    const el = e.target;
                    if (!el.matches('[role="checkbox"], [role="radio"]')) return;
                    if (el.role === 'radio') {
                      el.parentElement.querySelectorAll('[role="radio"]').forEach(n => n.setAttribute('aria-checked', 'false'));
                      el.setAttribute('aria-checked', 'true');
                    } else el.setAttribute('aria-checked', String(el.getAttribute('aria-checked') !== 'true'));
                  });
                </script>
            ''')
            questions = read_questions(page)
            self.assertEqual([q['index'] for q in questions], [0, 1, 2, 3])
            self.assertEqual(questions[1]['question'], 'Lĩnh vực quan tâm *')
            self.assertEqual(questions[1]['options'], ['Kinh tế', 'CNTT', 'Mục khác:'])
            self.assertEqual(questions[2]['options'], ['Học phí', 'Gia đình'])
            blocks = page.locator(QUESTION_SELECTOR)
            # Force all eligible checkboxes, then one: stale selections must clear.
            with patch('browser.random.randint', return_value=2):
                select_random_options(blocks.nth(1))
            self.assertEqual(blocks.nth(1).locator('[aria-checked="true"]').count(), 2)
            self.assertEqual(blocks.nth(1).locator('[aria-label="Mục khác:"]').get_attribute('aria-checked'), 'false')
            with patch('browser.random.randint', return_value=1):
                select_random_options(blocks.nth(1))
            self.assertEqual(blocks.nth(1).locator('[aria-checked="true"]').count(), 1)
            self.assertEqual(blocks.nth(2).locator('[aria-checked="true"]').count(), 0)
            select_random_options(blocks.nth(2))
            self.assertGreaterEqual(blocks.nth(2).locator('[aria-checked="true"]').count(), 1)
            for _ in range(10):
                select_random_options(blocks.nth(3))
                self.assertEqual(blocks.nth(3).locator('[aria-checked="true"]').count(), 1)
            browser.close()


if __name__ == '__main__':
    unittest.main()
