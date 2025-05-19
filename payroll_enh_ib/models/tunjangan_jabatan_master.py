from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class MasterTunjangan(models.Model):
    _name = 'odoo.payroll.tunjangan'
    _description = 'Master Tunjangan'

    name = fields.Char(compute='_compute_name')
    jabatan_id = fields.Many2one('employee.position.payroll', string='Jabatan')
    unit_id = fields.Many2one('employee.unit.payroll')
    hr_branch_id = fields.Many2one('hr.branch', string='Unit Penempatan')
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    amount_tunjangan = fields.Monetary('Tunjangan')
    amount_bpfp = fields.Monetary('BPFP')
    koef_kemahalan_percent = fields.Float('Koef Kemahalan (%)')
    amount_kemahalan = fields.Monetary('Nilai Kemahalan', compute='_compute_tunjangan_kemahalan')

    @api.depends('jabatan_id','hr_branch_id')
    def _compute_name(self):
        self.name = 'New'
        for rec in self:
            rec.name = 'Positional Allowance - ' + rec.jabatan_id.name + ' ' + rec.hr_branch_id.name if rec.jabatan_id and rec.hr_branch_id else 'New'

    @api.depends('hr_branch_id')
    def _compute_tunjangan_kemahalan(self):
        self.amount_kemahalan = 0
        for rec in self:
            nilai_kemahalan_obj = self.env['odoo.payroll.nilai.kemahalan'].search([('hr_branch_id', 'in', rec.hr_branch_id.ids)])
            for nilai_kemahalan in nilai_kemahalan_obj:
                value = (nilai_kemahalan.nilai_kemahalan * rec.koef_kemahalan_percent) / 100
                rec.amount_kemahalan = value