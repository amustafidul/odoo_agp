from odoo import models, fields, api, _


class HrEmployeeIjazah(models.Model):
    _name = "hr.employee.ijazah"
    _description = "Ijazah Employee"
    _order = 'create_date desc'

    sequence = fields.Integer('Seq')
    name = fields.Char('NIK')
    employee_name = fields.Char('Nama Pegawai')
    pendidikan_terakhir = fields.Char('Pendidikan Terakhir')
    pendidikan_terakhir_selc = fields.Selection(
        [
            ('sd', 'SD Sederajat'),
            ('smp', 'SMP Sederajat'),
            ('sma', 'SMA Sederajat'),
            ('d1', 'D1'),
            ('d2', 'D2'),
            ('d3', 'D3'),
            ('d4', 'D4'),
            ('s1', 'S1'),
            ('s2', 'S2'),
            ('s3', 'S3'),
        ],
        string='Pendidikan Terakhir'
    )
    ijazah_doc_attachment = fields.Binary('Document Ijazah')
    ijazah_attachment_id = fields.Many2many('ir.attachment', string='Ijazah')
    ijazah_filename = fields.Char('Filename')
    ijazah_doc_name = fields.Char('Doc Name')
    ijazah_name = fields.Char('Ijazah Name')
    ijazah_and_sertifikat = fields.Text('Ijazah & Sertifikat')
    jurusan = fields.Char('Jurusan')
    asal_sekolah = fields.Char('Asal Sekolah')
    ijazah_date = fields.Date('Tanggal Ijazah')
    employee_id = fields.Many2one('hr.employee')