from odoo import models, fields, api, _


class HrEmployeeKelompokUmur(models.Model):
    _name = "hr.employee.kelompok.umur"
    _description = "Kelompok Umur"
    _check_company_auto = True

    name = fields.Char("Kelompok Umur", index='trigram', compute="_compute_name")
    min_age = fields.Integer("Minimum Age", required=True)
    max_age = fields.Integer("Maximum Age", required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company, readonly=1)
    employee_ids = fields.One2many('hr.employee', 'kelompok_umur_id', string='Employees in this group', readonly=True)
    employee_count = fields.Integer(string='Employees Count', compute='_compute_employee_count')

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 'Kelompok Umur must be unique per company.')
    ]

    @api.depends('min_age', 'max_age')
    def _compute_name(self):
        for rec in self:
            if rec.min_age and rec.max_age:
                rec.name = f"{rec.min_age} - {rec.max_age}"
            else:
                rec.name = False

    @api.depends('employee_ids')
    def _compute_employee_count(self):
        for rec in self:
            rec.employee_count = len(rec.employee_ids)

    def action_open_employees(self):
        self.ensure_one()
        return {
            'name': _("Employees in '%s'" % self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'view_mode': 'tree,form',
            'domain': [('employment_type','in',['organik','pkwt']), ('kelompok_umur_id', '=', self.id)],
            'context': dict(self._context, create=False),
        }