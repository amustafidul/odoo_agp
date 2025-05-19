from odoo import models, fields, api

class TrainingCourseParticipantLine(models.Model):
    _name = 'training.course.participant.line'
    _description = 'Detail Peserta Final & Biaya Realisasi Training'
    _order = 'sequence, id'

    course_id = fields.Many2one(
        'training.course',
        string='Pelaksanaan Training Induk',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string='No. Urut', default=10)
    employee_id = fields.Many2one(
        'hr.employee',
        string='Nama Karyawan Peserta',
        required=True
    )
    estimated_cost_from_tna = fields.Monetary(
        string='Estimasi Biaya Awal (TNA)',
        currency_field='currency_id',
        readonly=True,
        help="Estimasi biaya awal dari usulan TNA untuk peserta ini (jika ada)."
    )
    actual_cost_participant = fields.Monetary(
        string='Biaya Realisasi Peserta',
        currency_field='currency_id',
        required=True,
        default=0.0,
        tracking=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Mata Uang',
        related='course_id.currency_id',
        store=True,
        readonly=True
    )
    attendance_status = fields.Selection([
        ('present', 'Hadir'),
        ('absent', 'Tidak Hadir'),
        ('partial', 'Hadir Sebagian')
    ], string="Status Kehadiran", default="present")
    notes = fields.Text(string='Catatan Peserta Final')

    _sql_constraints = [
        ('employee_course_uniq', 'unique(course_id, employee_id)',
         'Karyawan ini sudah terdaftar sebagai peserta di training ini!')
    ]

    # @api.onchange('employee_id')
    # def _onchange_employee_id(self):
    #     pass