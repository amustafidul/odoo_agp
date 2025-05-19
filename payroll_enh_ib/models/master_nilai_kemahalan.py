from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class MasterNilaiKemahalan(models.Model):
    _name = 'odoo.payroll.nilai.kemahalan'
    _description = 'Master Nilai Kemahalan - Payroll'

    name = fields.Char(compute='_compute_name')
    unit_id = fields.Many2one('employee.unit.payroll')
    hr_branch_id = fields.Many2one('hr.branch', string='Unit')
    amount_kemahalan_percent = fields.Float('Prosentase Kemahalan (%)', digits=(16, 3))
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    amount_harga_sebulan = fields.Monetary('Harga Sebulan')
    nilai_kemahalan = fields.Monetary('Kemahalan', compute='_compute_nilai_kemahalan')

    @api.depends('hr_branch_id')
    def _compute_name(self):
        self.name = 'New'
        for rec in self:
            rec.name = 'Dearness Value - ' + rec.hr_branch_id.name if rec.hr_branch_id else 'New'

    @api.depends('amount_harga_sebulan', 'amount_kemahalan_percent')
    def _compute_nilai_kemahalan(self):
        for rec in self:
            nilai_kemahalan_percent = (rec.amount_harga_sebulan * rec.amount_kemahalan_percent) / 100
            rec.nilai_kemahalan  = nilai_kemahalan_percent * 100