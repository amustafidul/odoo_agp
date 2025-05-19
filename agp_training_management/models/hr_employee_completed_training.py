from odoo import models, fields, api


class HrEmployeeCompletedTraining(models.Model):
    _name = 'hr.employee.completed.training'
    _description = 'Histori Training Karyawan yang Telah Selesai'
    _order = 'employee_id, end_date desc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Karyawan',
        required=True,
        ondelete='cascade',
        index=True
    )
    realization_id = fields.Many2one(
        'training.course',
        string='Realisasi Training',
        required=True,
        ondelete='restrict',
        index=True
    )
    training_name = fields.Char(
        string='Nama Training',
        related='realization_id.name',
        store=True,
        readonly=True
    )
    start_date = fields.Date(
        string='Tanggal Mulai',
        related='realization_id.actual_start_date',
        store=True,
        readonly=True
    )
    end_date = fields.Date(
        string='Tanggal Selesai',
        related='realization_id.actual_end_date',
        store=True,
        readonly=True
    )
    organizer = fields.Char(
        string='Penyelenggara',
        related='realization_id.organizer',
        store=True,
        readonly=True
    )
    certificate_number = fields.Char(
        string='Nomor Sertifikat',
        related='realization_id.certificate_number',
        store=True,
        readonly=True
    )
    certificate_expiry_date = fields.Date(
        string='Tanggal Kadaluarsa Sertifikat',
        related='realization_id.certificate_expiry_date',
        store=True,
        readonly=True
    )
    notes = fields.Text(string='Catatan Tambahan')
    company_id = fields.Many2one(
        'res.company',
        string='Perusahaan',
        related='realization_id.company_id',
        store=True,
        readonly=True
    )

    _sql_constraints = [
        ('employee_realization_uniq', 'unique(employee_id, realization_id)',
         'Karyawan ini sudah tercatat mengikuti training ini.')
    ]


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    completed_training_ids = fields.One2many(
        'hr.employee.completed.training',
        'employee_id',
        string='Histori Training Selesai'
    )

    completed_training_count = fields.Integer(
        compute='_compute_completed_training_count',
        string="Jumlah Training Diikuti"
    )

    def _compute_completed_training_count(self):
        for employee in self:
            employee.completed_training_count = len(employee.completed_training_ids)