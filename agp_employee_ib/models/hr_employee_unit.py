from odoo import models, fields, api, _


class HrEmployeeUnit(models.Model):
    _name = "hr.employee.unit"
    _description = "Employee Unit"
    _check_company_auto = True

    name = fields.Char('Unit', index='trigram', required=True)
    branch_id = fields.Many2one('res.branch', string='Branch/Cabang', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company, readonly=1)

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 'Unit must be unique per company.')
    ]