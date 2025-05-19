from odoo import models, fields, api


class HrBranch(models.Model):
    _name = 'hr.branch'
    _description = 'HR Branch'

    name = fields.Char(string="Branch Name")
    location = fields.Selection([
        ('head_office', 'Head Office'),
        ('branch_office', 'Branch Office')
    ], string='Location', required=True)
    company_id = fields.Many2one('res.company', string="Company")
    manager_id = fields.Many2one('hr.employee', string="Manager Cabang")
    res_branch_id = fields.Many2one('res.branch', string="Original Branch")
    unit_penempatan_ids = fields.Many2many(
        'hr.employee.unit.penempatan',
        string="Unit Penempatan"
    )

    def init(self):
        cr = self._cr
        env = self.env

        cr.execute("SELECT id, name, company_id FROM res_branch")
        all_res_branches = cr.fetchall()

        for branch_id, branch_name, company_id in all_res_branches:
            existing_hr_branch = env['hr.branch'].search([('res_branch_id', '=', branch_id)], limit=1)
            if not existing_hr_branch:
                env['hr.branch'].create({
                    'name': branch_name,
                    'company_id': company_id,
                    'res_branch_id': branch_id,
                })


class ResBranch(models.Model):
    _inherit = 'res.branch'

    @api.model
    def create(self, vals):
        record = super().create(vals)
        self.env['hr.branch'].create({
            'name': record.name,
            'company_id': record.company_id.id,
            'res_branch_id': record.id,
        })
        return record

    def write(self, vals):
        res = super().write(vals)
        for branch in self:
            hr_branch = self.env['hr.branch'].search([('res_branch_id', '=', branch.id)], limit=1)
            if hr_branch:
                update_vals = {}
                if 'name' in vals:
                    update_vals['name'] = vals['name']
                if 'company_id' in vals:
                    update_vals['company_id'] = vals['company_id']
                if update_vals:
                    hr_branch.write(update_vals)
        return res

    def unlink(self):
        hr_branches = self.env['hr.branch'].search([('res_branch_id', 'in', self.ids)])
        hr_branches.unlink()
        return super().unlink()