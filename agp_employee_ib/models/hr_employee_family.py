from odoo import models, fields, api, _

import logging

_logger = logging.getLogger(__name__)


class HrEmployeeFamily(models.Model):
    _name = "hr.employee.family"
    _inherit = 'hr.employee.family'
    _description = "Employee Family"

    name = fields.Char('Nama')
    nik = fields.Char('NIK')
    gender = fields.Selection(
        [
            ('male', 'Laki-laki'),
            ('female', 'Perempuan'),
        ],
        string='Jenis Kelamin'
    )
    status_hubungan = fields.Selection(
        [
            ('suami', 'Suami'),
            ('istri', 'Istri'),
            ('anak1', 'Anak ke 1'),
            ('anak2', 'Anak ke 2'),
            ('anak3', 'Anak ke 3'),
            ('anak4', 'Anak ke 4'),
            ('anak5', 'Anak ke 5'),
            ('anak6', 'Anak ke 6'),
            ('ibu', 'Orang Tua (Ibu)'),
            ('bapak', 'Bapak (Bapak)'),
        ],
        string='Hubungan Dengan Karyawan'
    )
    tempat_lahir = fields.Char('Tempat Lahir')
    tanggal_lahir = fields.Date('Tanggal Lahir')
    attachment_doc_ktp = fields.Binary('Upload KTP')
    employee_id = fields.Many2one('hr.employee')