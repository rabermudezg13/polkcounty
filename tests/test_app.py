"""UI checks use synthetic attendance and mocked storage, never production Firebase."""
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from attendance import occurrence_id

APP = str(Path(__file__).resolve().parents[1] / 'app.py')


class AppTests(unittest.TestCase):
    def app(self):
        app = AppTest.from_file(APP, default_timeout=30)
        app.secrets['app_password'] = 'local-test-only-password'
        return app

    def test_sign_in_required_and_wrong_password_rejected(self):
        with patch('storage.connect') as connect:
            app = self.app().run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(app.button[0].label, 'Sign in')
            self.assertEqual(len(app.file_uploader) if hasattr(app, 'file_uploader') else 0, 0)
            app.text_input[0].set_value('incorrect')
            app.button[0].click().run()
            self.assertEqual(app.error[0].value, 'Incorrect password.')
            connect.assert_not_called()

    def test_sign_in_import_and_sign_out(self):
        app = self.app().run()
        app.text_input[0].set_value('local-test-only-password')
        app.button[0].click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(app.session_state['authenticated'])
        app.sidebar.radio[0].set_value('Import Excel').run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.subheader[0].value, 'Import Excel')
        app.sidebar.button[0].click().run()
        self.assertEqual(app.subheader[0].value, 'Sign in')

    def test_reports_and_recurrence_with_mocked_history(self):
        row = {'person_id':'ats:001', 'ats_id':'001', 'name':'Synthetic Employee',
            'email':'', 'date':'2026-09-01', 'status':'No Show'}
        row['id'] = occurrence_id(row)
        second = dict(row, date='2026-09-02', status='Late Cancellation')
        second['id'] = occurrence_id(second)
        with patch('storage.connect', return_value=object()), patch('storage.load_records', return_value=[row, second]):
            app = self.app()
            app.secrets['firebase'] = {'project_id':'subparty'}
            app.session_state['authenticated'] = True
            app.run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual([metric.value for metric in app.metric], ['2','1','1','1','1'])
            from datetime import date
            app.date_input[0].set_value(date(2026,9,2)).run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual([metric.value for metric in app.metric], ['1','0','1','1','0'])
            app.sidebar.radio[0].set_value('Recurring People').run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(app.metric[0].value, '1')
            app.sidebar.radio[0].set_value('History').run()
            app.text_input[0].set_value('missing employee').run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(app.info[0].value, 'No records to display.')


if __name__ == '__main__':
    unittest.main()
