from odoo import models, fields, api


class TnaProposedParticipant(models.Model):
    _name = 'tna.proposed.participant'
    _description = 'Detail Peserta Diusulkan untuk Training TNA'
    _order = 'sequence, id'

    proposed_training_id = fields.Many2one(
        'tna.proposed.training',
        string='Usulan Training Induk',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string='No. Urut', default=10)
    employee_id = fields.Many2one(
        'hr.employee',
        string='Nama Karyawan Diusulkan',
        required=True
    )
    employment_type = fields.Selection(
        related='employee_id.employment_type',
        string='Tipe Kepegawaian',
        store=True,
        readonly=True
    )
    estimated_cost_participant = fields.Monetary(
        string='Estimasi Biaya per Peserta',
        currency_field='currency_id',
        required=True,
        default=0.0
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Mata Uang',
        related='proposed_training_id.currency_id',
        store=True,
        readonly=True
    )
    notes = fields.Text(string='Catatan Peserta')

    submission_id = fields.Many2one(
        related='proposed_training_id.submission_id',
        store=False,
        readonly=True
    )
    department_id = fields.Many2one(
        related='proposed_training_id.department_id',
        store=True,
        readonly=True
    )
    branch_id = fields.Many2one(
        related='proposed_training_id.branch_id',
        store=True,
        readonly=True
    )

    _sql_constraints = [
        ('employee_training_uniq', 'unique(proposed_training_id, employee_id)',
         'Karyawan ini sudah diusulkan untuk training yang sama!')
    ]

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.employment_type = self.employee_id.employment_type
        else:
            self.employment_type = False