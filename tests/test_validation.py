import unittest

from validation import normalize_contacts, validate_identity


class EmailTest(unittest.TestCase):
    def payload(self, email):
        return {'Họ và tên': 'Nguyễn Văn A', 'Số điện thoại': '0123456789', 'Email': email}

    def test_blank_email_is_optional(self):
        for email in ('', '   ', None):
            with self.subTest(email=email):
                data = normalize_contacts(self.payload(email))
                self.assertEqual(data['Email'], '')
                data['_can_kiem_tra'] = ['Email']
                self.assertEqual(validate_identity(data), [])

    def test_missing_domain_is_added(self):
        data = normalize_contacts(self.payload('  nguyenvana  '))
        self.assertEqual(data['Email'], 'nguyenvana@gmail.com')
        self.assertEqual(validate_identity(data), [])
        self.assertEqual(normalize_contacts(data)['Email'], data['Email'])

    def test_existing_gmail_is_trimmed_and_preserved(self):
        data = normalize_contacts(self.payload('  nguyenvana@gmail.com  '))
        self.assertEqual(data['Email'], 'nguyenvana@gmail.com')
        self.assertEqual(validate_identity(data), [])

    def test_malformed_email_still_reports_error(self):
        for email in ('a b', 'a@', '@gmail.com', 'a@yahoo.com'):
            with self.subTest(email=email):
                data = normalize_contacts(self.payload(email))
                self.assertEqual(data['Email'], email)
                self.assertTrue(validate_identity(data))


if __name__ == '__main__':
    unittest.main()
