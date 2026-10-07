import io
import unittest
from datetime import datetime

import openpyxl

from attendance import export_csv, is_polk, parse_workbook, recurring_people


class AttendanceTests(unittest.TestCase):
    def workbook(self, rows):
        book = openpyxl.Workbook()
        sheet = book.active
        sheet.title = 'Occurrence Log'
        sheet.append(['Tracker'])
        sheet.append([])
        sheet.append([])
        sheet.append(['Date of Absence', 'Employee Name', 'ATS ID', 'Email', 'District', 'Type', 'Case Number'])
        for row in rows:
            sheet.append(row)
        output = io.BytesIO()
        book.save(output)
        return output.getvalue()

    def test_polk_filter(self):
        for district in ['Polk', 'FL|K12|Polk', 'Polk County', ' polk ']:
            self.assertTrue(is_polk(district))
        for district in ['HCPS', 'FL|K12|HCPS', '', 'Polkville']:
            self.assertFalse(is_polk(district))

    def test_filter_classify_deduplicate_and_recurrence(self):
        data = self.workbook([
            [datetime(2026, 8, 10), 'Example Person', '00123', '', 'Polk', 'No Show', 'A'],
            [datetime(2026, 8, 10), 'Example Person', '00123', '', 'FL|K12|Polk', 'No Show', 'B'],
            [datetime(2026, 8, 11), 'Example Person', '00123', '', 'Polk', 'Unassisted', 'C'],
            [datetime(2026, 8, 12), 'Other Person', '99', '', 'HCPS', 'No Show', 'D'],
        ])
        records, summary, errors = parse_workbook(data)
        self.assertEqual(len(records), 2)
        self.assertEqual(summary['Other districts excluded'], 1)
        self.assertEqual(summary['Duplicate incidents excluded'], 1)
        self.assertEqual(errors, [])
        self.assertEqual(records[0]['ats_id'], '00123')
        recurrent = recurring_people(records + records)
        self.assertEqual(len(recurrent), 1)
        self.assertEqual(recurrent[0]['No Show'], 1)
        self.assertEqual(recurrent[0]['Late Cancellation'], 1)
        self.assertEqual(recurrent[0]['Incidents'], 2)
        self.assertEqual(recurring_people(records, 3), [])

    def test_invalid_polk_rows_visible(self):
        data = self.workbook([['bad date', 'Example', '', '', 'Polk', 'No Show', 'A'],
            ['08/10/2026', 'Example', '', '', 'Polk', 'Unknown', 'B']])
        records, summary, errors = parse_workbook(data)
        self.assertEqual(records, [])
        self.assertEqual(summary['Rows requiring correction'], 2)
        self.assertEqual(len(errors), 2)

    def test_name_fallback_and_month_day_date(self):
        data = self.workbook([['09/10/2026', ' Example Person ', None, '', 'Polk', 'Late Cancellation', 'A']])
        records, _, _ = parse_workbook(data)
        self.assertEqual(records[0]['person_id'], 'name:example person')
        self.assertEqual(records[0]['date'], '2026-09-10')

    def test_csv_does_not_execute_formulas(self):
        self.assertIn("'=HYPERLINK", export_csv([{'Name': '=HYPERLINK("test")'}]).decode('utf-8-sig'))


if __name__ == '__main__':
    unittest.main()
