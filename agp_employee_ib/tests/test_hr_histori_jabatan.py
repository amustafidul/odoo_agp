from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestHistoriJabatan(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Employee = self.env['hr.employee'].create({'name': 'John Doe'})
        self.Jabatan = self.env['hr.employee.keterangan.jabatan'].create({'name': 'Staff'})
        self.Fungsi = self.env['hr.employee.fungsi.penugasan'].create({'name': 'Support'})
        self.Grade = self.env['odoo.payroll.grade'].create({'name': 'G1'})
        self.Branch = self.env['hr.branch'].create({'name': 'Jakarta'})

    def test_create_histori_and_sync(self):
        histori = self.env['hr.employee.histori.jabatan'].create({
            'employee_id': self.Employee.id,
            'employment_type': 'organik',
            'keterangan_jabatan_id': self.Jabatan.id,
            'grade_id': self.Grade.id,
            'hr_branch_id': self.Branch.id,
            'tmt_date': '2023-01-01',
            'tanggal_pengangkatan': '2023-01-01',
        })

        self.assertEqual(histori.employee_id.keterangan_jabatan_id.id, self.Jabatan.id)
        self.assertEqual(histori.employee_id.grade_id.id, self.Grade.id)
        self.assertEqual(histori.employee_id.hr_branch_id.id, self.Branch.id)

    def test_duplicate_histori_should_fail(self):
        vals = {
            'employee_id': self.Employee.id,
            'employment_type': 'organik',
            'keterangan_jabatan_id': self.Jabatan.id,
            'tmt_date': '2023-01-01',
            'tanggal_pengangkatan': '2023-01-01',
        }
        self.env['hr.employee.histori.jabatan'].create(vals)
        with self.assertRaises(ValidationError):
            self.env['hr.employee.histori.jabatan'].create(vals)

    def test_compute_masa_jabatan(self):
        histori = self.env['hr.employee.histori.jabatan'].create({
            'employee_id': self.Employee.id,
            'employment_type': 'organik',
            'keterangan_jabatan_id': self.Jabatan.id,
            'tanggal_pengangkatan': '2022-01-01',
        })
        histori._compute_masa_jabatan()
        self.assertIn('tahun', histori.masa_jabatan_bulan)

    def test_unlink_resets_employee(self):
        histori = self.env['hr.employee.histori.jabatan'].create({
            'employee_id': self.Employee.id,
            'employment_type': 'organik',
            'keterangan_jabatan_id': self.Jabatan.id,
        })
        histori.unlink()
        self.assertFalse(self.Employee.keterangan_jabatan_id)