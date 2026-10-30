import re, random, unicodedata
from playwright.sync_api import sync_playwright

RANDOM_ANSWER = '__random_answer__'
QUESTION_SELECTOR = 'div[role="listitem"]:has([role="heading"])'


def norm(v):
    return re.sub(r'[^\w]+',' ',unicodedata.normalize('NFC',str(v)).lower(),flags=re.UNICODE).strip()


def score_policy(question):
    if question['options']:
        return None
    title = norm(question['question'])
    if title in {'toán', 'vật lí', 'vật lý', 'hoá học', 'hóa học', 'ngữ văn', 'tiếng anh', 'sinh học'}:
        return 'random_score'
    if title in {'vẽ mỹ thuật', 'mỹ thuật', 'địa lý', 'địa lí', 'môn khác'}:
        return 'blank_score'
    return None


def random_score():
    # Integer tenths keep both endpoints and the 0.2 step exact.
    tenths = random.choice(range(70, 95, 2))
    return f'{tenths // 10},{tenths % 10}'


def submit_buttons(page):
    return [button for button in page.get_by_role('button').all()
            if norm(button.get_attribute('aria-label') or button.inner_text()) in {'gửi', 'submit'}
            and button.is_visible() and button.is_enabled()]


def read_questions(page):
    # Google Forms also uses listitem for each checkbox answer. Only the
    # enclosing question has a heading; use the same blocks when filling.
    return page.locator(QUESTION_SELECTOR).evaluate_all(r'''els => els.map((el,i) => ({
        index:i,
        question:el.querySelector('[role="heading"]').innerText.trim(),
        options:[...el.querySelectorAll('[role="checkbox"], [role="radio"]')]
            .map(n => n.getAttribute('aria-label') || n.innerText || n.parentElement?.innerText || '')
            .map(s => s.trim()),
        textboxes:el.querySelectorAll('input[type="text"],input[type="email"],textarea,[role="textbox"]').length,
        required:!!(el.querySelector('[aria-label*="Required"],[aria-label*="Bắt buộc"],[aria-required="true"]')
            || el.innerText.match(/\*\s*$/m))
    })).filter(x => x.question && (x.options.length || x.textboxes))''')


def discover(url):
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page()
        page.goto(url,wait_until='domcontentloaded',timeout=60000)
        page.wait_for_timeout(1500)
        result=read_questions(page)
        browser.close()
        return result

def proposed_mapping(form_questions, keys):
    # Không ghép tự động theo độ giống văn bản: dễ gán Logistics thành Đồng ý.
    return {str(q['index']): '' for q in form_questions}


def select_option(block, value):
    options = block.locator('[role="checkbox"], [role="radio"]')
    candidates = []
    for i in range(options.count()):
        opt = options.nth(i)
        label = (opt.get_attribute('aria-label') or opt.inner_text() or
                 opt.locator('xpath=..').inner_text()).strip()
        candidates.append((norm(label), i, label))
    exact = [c for c in candidates if c[0] == norm(value)]
    if len(exact) != 1:
        raise ValueError(f'Không có duy nhất lựa chọn KHỚP CHÍNH XÁC với "{value}". '
                         f'Các lựa chọn của Form: {[c[2] for c in candidates]}')
    opt = options.nth(exact[0][1])
    if opt.get_attribute('aria-checked') != 'true':
        opt.click()


def select_random_options(block):
    options = block.locator('[role="checkbox"], [role="radio"]')
    available = [options.nth(i) for i in range(options.count())
                 if options.nth(i).is_visible() and options.nth(i).is_enabled()
                 and options.nth(i).get_attribute('aria-disabled') != 'true'
                 and options.nth(i).get_attribute('data-answer-value') != '__other_option__'
                 and options.nth(i).get_attribute('data-value') != '__other_option__'
                 and norm(options.nth(i).get_attribute('aria-label') or options.nth(i).inner_text())
                     not in {'other', 'khác', 'mục khác', 'khác other', 'other khác'}]
    if not available:
        raise ValueError('Không có đáp án khả dụng để chọn ngẫu nhiên.')
    roles = {opt.get_attribute('role') for opt in available}
    if len(roles) != 1:
        raise ValueError('Câu hỏi chứa nhiều nhóm lựa chọn; cần kiểm tra thủ công.')
    count = random.randint(1, len(available)) if roles == {'checkbox'} else 1
    selected = set(random.sample(range(len(available)), count))
    for i, opt in enumerate(available):
        checked = opt.get_attribute('aria-checked') == 'true'
        if i in selected and not checked:
            opt.click()
        elif roles == {'checkbox'} and i not in selected and checked:
            opt.click()


def fill_form(url, data, form_questions, mapping, submit=False):
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,slow_mo=100)
        page=browser.new_page()
        page.goto(url,wait_until='domcontentloaded',timeout=60000)
        page.wait_for_timeout(1000)
        errors=[]
        for q in form_questions:
            policy=score_policy(q)
            if policy == 'blank_score': continue
            key=mapping.get(str(q['index']))
            randomize = key == RANDOM_ANSWER and bool(q['options'])
            if not randomize and policy != 'random_score' and (not key or key not in data): continue
            value = random_score() if policy == 'random_score' else (None if randomize else data[key])
            if not randomize and value in ('',None,[]): continue
            block=page.locator(QUESTION_SELECTOR).nth(q['index'])
            visible_question=(block.locator('[role="heading"]').first.inner_text() if block.locator('[role="heading"]').count() else '').strip()
            if norm(visible_question)!=norm(q['question']):
                errors.append(f'Vị trí câu hỏi thay đổi: {q["question"]} / {visible_question}'); continue
            try:
                if randomize:
                    select_random_options(block)
                elif q['options']:
                    for choice in value if isinstance(value,list) else [value]: select_option(block,choice)
                else:
                    field=block.locator('input[type="text"],input[type="email"],textarea,[role="textbox"]').first
                    field.fill(', '.join(map(str,value)) if isinstance(value,list) else str(value))
            except Exception as e:
                errors.append(f'{q["question"]}: {e}')
        if submit and not errors:
            buttons=submit_buttons(page)
            if not buttons: errors.append('Không tìm thấy nút Gửi; có thể Form nhiều trang hoặc yêu cầu đăng nhập')
            elif len(buttons) != 1: errors.append('Có nhiều nút Gửi; cần kiểm tra thủ công trước khi gửi.')
            else:
                buttons[0].click()
                page.wait_for_timeout(1500)
                if not re.search('đã được ghi|recorded|submitted|cảm ơn|thank',unicodedata.normalize('NFC',page.locator('body').inner_text()),re.I):
                    errors.append('Đã click Gửi nhưng chưa xác minh được thông báo thành công. Kiểm tra thủ công để tránh gửi trùng.')
        elif not submit:
            errors.append('Đang ở chế độ kiểm thử: chưa bấm Gửi.')
        page.screenshot(path='form_preview.png',full_page=True)
        browser.close()
        return errors
