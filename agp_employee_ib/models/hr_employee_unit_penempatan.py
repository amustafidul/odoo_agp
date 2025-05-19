from odoo import models, fields, api, _


class HrEmployeeUnitPenempatan(models.Model):
    _name = "hr.employee.unit.penempatan"
    _description = "Unit Penempatan"

    name = fields.Char("Unit Penempatan", index='trigram', required=True)
    address = fields.Text()
    phone_number = fields.Char()
    fax = fields.Char()
    email = fields.Char()
    res_sub_branch_id = fields.Many2one('sub.branch', string="Original Sub Branch")

    def init(self):
        env = self.env
        env['hr.employee.unit.penempatan'].search([('res_sub_branch_id', '!=', False)]).unlink()

        self._cr.execute("SELECT id, name FROM sub_branch")
        sub_branches = self._cr.fetchall()
        for sb_id, sb_name in sub_branches:
            env['hr.employee.unit.penempatan'].create({
                'name': sb_name,
                'res_sub_branch_id': sb_id,
            })


class SubBranch(models.Model):
    _inherit = 'sub.branch'

    @api.model
    def create(self, vals):
        record = super().create(vals)
        self.env['hr.employee.unit.penempatan'].create({
            'name': record.name,
            'res_sub_branch_id': record.id,
        })
        return record

    def write(self, vals):
        res = super().write(vals)
        for sub_branch in self:
            hr_sub_branch = self.env['hr.employee.unit.penempatan'].search([('res_sub_branch_id', '=', sub_branch.id)], limit=1)
            if hr_sub_branch:
                update_vals = {}
                if 'name' in vals:
                    update_vals['name'] = vals['name']
                if update_vals:
                    hr_sub_branch.write(update_vals)
        return res

    def unlink(self):
        sub_branches = self.env['hr.employee.unit.penempatan'].search([('res_sub_branch_id', 'in', self.ids)])
        sub_branches.unlink()
        return super().unlink()