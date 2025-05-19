from odoo import models, fields, api, _


class HrEmployeeSertifikasiPelatihan(models.Model):
    _name = "hr.employee.sertifikasi.pelatihan"
    _description = "Employee (Sertifikasi & Pelatihan)"
    _order = "certification_start_date asc"

    name = fields.Char()
    organizer = fields.Char()
    certificate_number_official = fields.Char()
    originating_training_course_id = fields.Many2one('training.course')
    certificate_doc_attachment = fields.Binary('Sertifikat Document', attachment=True)
    certificate_attachment_id = fields.Many2many('ir.attachment', string='Sertifikat Document')
    certificate_doc_name = fields.Char('Sertifikat Name')
    certificate_filename = fields.Char('Filename SK')
    certification_date = fields.Date('Tanggal Sertifikasi/Pelatihan')
    certification_start_date = fields.Date('Tanggal Mulai')
    certification_end_date = fields.Date('Tanggal Selesai')
    certification_expiration_date = fields.Date('Tanggal Kadaluarsa Sertifikat')
    employee_id = fields.Many2one('hr.employee')