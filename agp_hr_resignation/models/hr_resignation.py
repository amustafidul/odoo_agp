from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    contract_end = fields.Boolean(string="Contrac End", default=False, store=True, help="If checked, then the employee has an ended contract.")
    pensiun = fields.Boolean(string="Pensiun", default=False, store=True, help="If checked, the employee has retired and is no longer under contract.")
    pensiun_dini = fields.Boolean(string="Pensiun Dini", default=False, store=True, help="If checked, the employee has taken early retirement and is no longer under contract.")
    meninggal_dunia = fields.Boolean(string="Meninggal Dunia", default=False, store=True, help="If checked, the employee has passed away and is no longer under contract.")
    date_masuk = fields.Date(string="Tanggal Masuk", compute="_compute_date_masuk", store=True)
    date_keluar = fields.Date(string="Tanggal Keluar", compute="_compute_date_keluar", store=True)
    status_mutasi = fields.Selection([
        ('in', 'Mutasi In'),
        ('out', 'Mutasi Out')
    ], string="Status Mutasi", compute="_compute_status_mutasi", store=True)
    resignation_reason = fields.Char(string="Alasan Keluar", compute="_compute_resignation_reason", store=True)
    date_masuk_month = fields.Char(string="Bulan Masuk", compute="_compute_date_masuk_month", store=True)
    date_keluar_month = fields.Char(string="Bulan Keluar", compute="_compute_date_keluar_month", store=True)
    employee_count = fields.Integer(string="Employee Count", default=1, store=True)

    @api.depends('histori_jabatan_ids')
    def _compute_date_masuk(self):
        for rec in self:
            if rec.histori_jabatan_ids:
                earliest_history = rec.histori_jabatan_ids.sorted('create_date')[0]
                rec.date_masuk = earliest_history.tmt_date or False
            else:
                rec.date_masuk = False

    @api.depends('resign_date')
    def _compute_date_keluar(self):
        for rec in self:
            rec.date_keluar = rec.resign_date

    @api.depends('active')
    def _compute_status_mutasi(self):
        for rec in self:
            rec.status_mutasi = 'in' if rec.active else 'out'

    @api.depends('resigned', 'fired', 'contract_end', 'pensiun', 'pensiun_dini', 'meninggal_dunia', 'active')
    def _compute_resignation_reason(self):
        for rec in self:
            if rec.active:
                rec.resignation_reason = ''
            else:
                if rec.resigned:
                    rec.resignation_reason = 'Resign Normal'
                elif rec.fired:
                    rec.resignation_reason = 'PHK'
                elif rec.contract_end:
                    rec.resignation_reason = 'Kontrak Berakhir'
                elif rec.pensiun:
                    rec.resignation_reason = 'Pensiun'
                elif rec.pensiun_dini:
                    rec.resignation_reason = 'Pensiun Dini'
                elif rec.meninggal_dunia:
                    rec.resignation_reason = 'Meninggal Dunia'
                else:
                    rec.resignation_reason = ''

    @api.depends('date_masuk')
    def _compute_date_masuk_month(self):
        for rec in self:
            if rec.date_masuk:
                rec.date_masuk_month = rec.date_masuk.strftime("%Y-%m")
            else:
                rec.date_masuk_month = ''

    @api.depends('date_keluar')
    def _compute_date_keluar_month(self):
        for rec in self:
            if rec.date_keluar:
                rec.date_keluar_month = rec.date_keluar.strftime("%Y-%m")
            else:
                rec.date_keluar_month = ''


class HrResignationCustom(models.Model):
    _inherit = 'hr.resignation'

    resignation_type = fields.Selection(
        selection_add=[
            ('contract_end', 'Kontrak Berakhir'),
            ('pensiun', 'Pensiun'),
            ('pensiun_dini', 'Pensiun Dini'),
            ('meninggal_dunia', 'Meninggal Dunia'),
            ('fired', 'PHK'),
        ],
        string="Resignation Type"
    )

    def approve_resignation(self):
        for rec in self:
            if rec.expected_revealing_date and rec.resign_confirm_date:
                no_of_contract = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id)])
                for contracts in no_of_contract:
                    if contracts.state == 'open':
                        rec.employee_contract = contracts.name
                        rec.state = 'approved'
                        rec.approved_revealing_date = rec.resign_confirm_date + timedelta(days=contracts.notice_days)
                    else:
                        rec.approved_revealing_date = rec.expected_revealing_date
                # Changing state of the employee if resigning today
                if rec.expected_revealing_date <= fields.Date.today() and rec.employee_id.active:
                    rec.employee_id.active = False
                    # Changing fields in the employee table with respect to resignation
                    rec.employee_id.resign_date = rec.expected_revealing_date
                    if rec.resignation_type == 'resigned':
                        rec.employee_id.resigned = True
                    elif rec.resignation_type == 'fired':
                        rec.employee_id.fired = True
                    elif rec.resignation_type == 'contract_end':
                        rec.employee_id.contract_end = True
                    elif rec.resignation_type == 'pensiun':
                        rec.employee_id.pensiun = True
                    elif rec.resignation_type == 'pensiun_dini':
                        rec.employee_id.pensiun_dini = True
                    elif rec.resignation_type == 'meninggal_dunia':
                        rec.employee_id.meninggal_dunia = True
                    # Removing and deactivating user
                    if rec.employee_id.user_id:
                        rec.employee_id.user_id.active = False
                        rec.employee_id.user_id = None
            else:
                raise ValidationError(_('Please enter valid dates.'))