from odoo import models, fields, api, _


class HrEmployeeUnitPenempatanCabang(models.Model):
    _name = "hr.employee.unit.penempatan.cabang"
    _description = "Unit penempatan/cabang"
    _check_company_auto = True

    name = fields.Char('Cabang', index='trigram', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True)

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 'Unit Penempatan Cabang must be unique per company.')
    ]