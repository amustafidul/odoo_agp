import datetime
from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, ValidationError


class EmployeeHistoryWizard(models.TransientModel):
    _name = 'hr.employee.history.wizard'
    _description = 'Update Histori Jabatan Wizard'

    employee_ids = fields.Many2many('hr.employee', string="Employees")
    history_line_ids = fields.One2many('hr.employee.history.line.wizard', 'wizard_id', string="Histori Jabatan")

    @api.model
    def default_get(self, field_names):
        res = super(EmployeeHistoryWizard, self).default_get(field_names)
        employee_ids = self.env.context.get('default_employee_ids')

        if employee_ids:
            res['employee_ids'] = [(6, 0, employee_ids)]

            wizard = self.env['hr.employee.history.line.wizard']
            lines = []
            for emp in self.env['hr.employee'].browse(employee_ids):
                line = wizard.create({
                    'employee_id': emp.id,
                    'jabatan_awal': emp.employment_type,
                    'jabatan_sekarang': False,
                    'tmt_date': datetime.date.today(),
                    'tanggal_pengangkatan': False,
                    'tanggal_selesai_kontrak': False,
                    'wizard_id': self.id
                })
                lines.append(line.id)
            res['history_line_ids'] = [(6, 0, lines)]
        return res

    def action_update_history(self):
        if not self.history_line_ids:
            raise UserError(_("Histori Jabatan tidak boleh kosong!"))

        employee_ids = self.env.context.get('default_employee_ids')
        if employee_ids:
            for emp_id in employee_ids:
                line = self.history_line_ids.filtered(lambda l: l.employee_id.id == emp_id)
                if line:
                    self.env['hr.employee.histori.jabatan'].create({
                        'employee_id': emp_id,
                        'employment_type': line[0].jabatan_sekarang,
                        'tmt_date': line[0].tmt_date,
                        'tanggal_pengangkatan': line[0].tanggal_pengangkatan,
                        'tanggal_selesai_kontrak': line[0].tanggal_selesai_kontrak,
                    })
                    emp_obj = self.env['hr.employee'].browse(emp_id)
                    for employee_id in emp_obj:
                        employee_id.employment_type = line[0].jabatan_sekarang


class EmployeeHistoryLineWizard(models.TransientModel):
    _name = 'hr.employee.history.line.wizard'
    _description = 'Employee History Line Wizard'

    wizard_id = fields.Many2one('hr.employee.history.wizard', string="Wizard")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    jabatan_awal = fields.Selection(selection=[
        ('tad', 'TAD'),
        ('pkwt', 'PKWT'),
        ('organik', 'Organik')
    ], string="Jabatan Awal", readonly=True)
    jabatan_sekarang = fields.Selection(selection=[
        ('tad', 'TAD'),
        ('pkwt', 'PKWT'),
        ('organik', 'Organik')
    ], string="Jabatan Sekarang")
    tmt_date = fields.Date(string="TMT")
    tanggal_pengangkatan = fields.Date(string="Tanggal Pengangkatan")
    tanggal_selesai_kontrak = fields.Date(string="Tanggal Selesai Kontrak")