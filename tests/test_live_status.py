"""Exercise the UI send handler with fake submissions, without contacting a Form."""
import ast
import copy
from pathlib import Path
from types import SimpleNamespace
import unittest


class LiveStatusTest(unittest.TestCase):
    def test_updates_during_send_and_stops_on_failure(self):
        source = ast.parse((Path(__file__).resolve().parents[1] / 'app.py').read_text(encoding='utf-8'))
        refresh = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == 'refresh_submission')
        handler = next(n for n in ast.walk(source) if isinstance(n, ast.If)
                       and isinstance(n.test, ast.Call) and isinstance(n.test.func, ast.Attribute)
                       and n.test.func.attr == 'button' and n.test.args
                       and isinstance(n.test.args[0], ast.Constant) and n.test.args[0].value == 'GỬI THẬT')
        code = compile(ast.Module(body=[refresh] + handler.body, type_ignores=[]), 'app.py', 'exec')
        for outcome in ('success', 'error', 'exception'):
            with self.subTest(outcome=outcome):
                snapshots, calls, records, notices = [], [], {}, []
                rows = [(2, {}, [], 'a'), (3, {}, [], 'b')]

                class Widget:
                    def dataframe(self, data, **kwargs): snapshots.append(copy.deepcopy(data))
                    def progress(self, *args, **kwargs): pass
                    def write(self, value): pass

                def set_status(c, b, n, fp, state, msg=''): records[n] = (state, msg, fp)
                def status(c, b, n): return records.get(n, ('chưa gửi', '', ''))

                def fill_form(*args, **kwargs):
                    n = 2 + len(calls)
                    self.assertEqual(snapshots[-1][n-2]['Trạng thái gửi'], 'đang gửi')
                    self.assertEqual(records[n][0], 'đang gửi')
                    calls.append(n)
                    if outcome == 'exception': raise RuntimeError('failure')
                    return ['failure'] if outcome == 'error' else []

                env = dict(st=SimpleNamespace(progress=lambda *a, **k: Widget(), warning=notices.append, success=notices.append),
                           pd=SimpleNamespace(DataFrame=lambda data: data), status_table=Widget(), pending_count=Widget(),
                           summary=[{'Dòng Excel': n, 'Trạng thái gửi': 'chưa gửi', 'Chi tiết gửi': ''} for n in (2, 3)],
                           c=None, batch='test', rows=rows, valid=rows, amount=2, url='unused', questions=[], mapping={},
                           status=status, set_status=set_status, fill_form=fill_form)
                exec(code, env)
                if outcome == 'success':
                    self.assertEqual(calls, [2, 3])
                    self.assertEqual([s[0]['Trạng thái gửi'] for s in snapshots[:2]], ['đang gửi', 'đã gửi'])
                    self.assertEqual(snapshots[-1][1]['Trạng thái gửi'], 'đã gửi')
                else:
                    self.assertEqual(calls, [2])
                    self.assertEqual(snapshots[-1][0]['Trạng thái gửi'], 'chưa xác minh')
                    self.assertEqual(snapshots[-1][1]['Trạng thái gửi'], 'chưa gửi')
                self.assertTrue(notices)


if __name__ == '__main__':
    unittest.main()
