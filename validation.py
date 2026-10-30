"""Conservative identity/contact normalization and submission validation."""
import re

PHONE_RE = re.compile(r'[0-9]{10}\Z')
GMAIL_RE = re.compile(r'[A-Za-z0-9][A-Za-z0-9._%+\-]*@gmail\.com\Z', re.I)
LOCAL_RE = re.compile(r'[A-Za-z0-9][A-Za-z0-9._%+\-]*\Z')


def normalize_contacts(payload):
    """Only add @gmail.com to an unambiguous bare local part. Never change phone."""
    data = dict(payload)
    notes = list(data.get('_chuan_hoa_email', []))
    email = data.get('Email', '')
    if email is None:
        data['Email'] = ''
    if isinstance(email, str):
        candidate = email.strip()
        data['Email'] = candidate
        if '@' not in candidate and LOCAL_RE.fullmatch(candidate):
            data['Email'] = candidate + '@gmail.com'
            notes.append('Đã thêm @gmail.com vào email chưa có tên miền; cần đối chiếu phiếu gốc.')
    data['_chuan_hoa_email'] = notes
    return data


def validate_identity(payload):
    problems = []
    name = payload.get('Họ và tên', '')
    if not isinstance(name, str) or not name.strip():
        problems.append('Họ và tên đang trống; phải đối chiếu phiếu giấy.')
    phone = payload.get('Số điện thoại', '')
    if not isinstance(phone, str) or PHONE_RE.fullmatch(phone) is None:
        problems.append('Số điện thoại phải đúng 10 chữ số (0–9), giữ nguyên như bản gốc; không tự thêm/bớt/sửa.')
    email = payload.get('Email', '')
    email_blank = email is None or (isinstance(email, str) and not email.strip())
    if not email_blank and (not isinstance(email, str) or GMAIL_RE.fullmatch(email) is None):
        problems.append('Gmail chưa đúng dạng ten@gmail.com. Không tự sửa địa chỉ có tên miền khác hoặc lỗi không rõ.')
    if 'Họ và tên' in payload.get('_can_kiem_tra', []):
        problems.append('AI chưa chắc chắn về họ và tên; hãy sửa và bỏ cảnh báo sau khi đối chiếu.')
    if 'Số điện thoại' in payload.get('_can_kiem_tra', []):
        problems.append('AI chưa chắc chắn về số điện thoại; hãy sửa và bỏ cảnh báo sau khi đối chiếu.')
    if not email_blank and 'Email' in payload.get('_can_kiem_tra', []):
        problems.append('AI chưa chắc chắn về email; hãy sửa và bỏ cảnh báo sau khi đối chiếu.')
    return problems
