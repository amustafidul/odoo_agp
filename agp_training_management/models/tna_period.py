from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import datetime


class TnaPeriod(models.Model):
    _name = 'tna.period'
    _description = 'Periode TNA (Tahunan/Semester)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'year desc, name desc'

    name = fields.Char(
        string='Nama Periode TNA',
        required=True,
        copy=False,
        tracking=True,
        compute='_compute_name',
        store=True,
        readonly=False
    )
    year = fields.Char(
        string='Tahun',
        required=True,
        tracking=True,
        size=4,
        default=lambda self: str(datetime.date.today().year)
    )
    semester = fields.Selection([
        ('1', 'Semester I'),
        ('2', 'Semester II'),
        ('all', 'Setahun Penuh (Semester I & II)')
        ],
        string='Cakupan Semester',
        default='all',
        tracking=True
    )
    date_start_submission = fields.Date(
        string='Tanggal Mulai Pengisian Usulan',
        tracking=True
    )
    date_end_submission = fields.Date(
        string='Batas Akhir Pengisian Usulan',
        tracking=True
    )
    responsible_user_id = fields.Many2one(
        'res.users',
        string='Penanggung Jawab (SDM)',
        tracking=True,
        default=lambda self: self.env.user
    )
    submission_ids = fields.One2many(
        'tna.submission',
        'period_id',
        string='Form Usulan TNA Diterima'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Dibuka untuk Pengisian'),
        ('closed', 'Pengisian Ditutup'),
        ('processing', 'Review & Approval SDM'),
        ('completed', 'Selesai')
        ],
        string='Status Periode',
        default='draft',
        copy=False,
        tracking=True,
        index=True,
        group_expand='_read_group_state_ids'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Perusahaan',
        default=lambda self: self.env.company,
        readonly=True,
        required=True
    )
    notes = fields.Text(string='Catatan Internal Periode')

    _sql_constraints = [
        ('year_semester_company_uniq', 'unique (year, semester, company_id)',
         'Periode TNA untuk tahun, semester, dan perusahaan yang sama sudah ada!')
    ]

    @api.constrains('year')
    def _check_year_format(self):
        for record in self:
            if record.year:
                if not record.year.isdigit():
                    raise ValidationError("Tahun harus berupa angka (contoh: 2025).")
                if len(record.year) != 4:
                    raise ValidationError("Tahun harus terdiri dari 4 digit (contoh: 2025).")

                year_int = int(record.year)
                current_year = datetime.date.today().year
                if not (current_year - 20 <= year_int <= current_year + 20):
                    raise ValidationError(f"Tahun harus dalam rentang yang wajar (misal, antara {current_year - 20} dan {current_year + 20}).")

    @api.depends('year', 'semester')
    def _compute_name(self):
        for period in self:
            if period.year:
                name_parts = [f"TNA {period.year}"]
                if period.semester and period.semester != 'all':
                    semester_display = dict(self._fields['semester'].selection).get(period.semester)
                    if semester_display:
                        name_parts.append(semester_display)
                period.name = " - ".join(name_parts)
            else:
                period.name = "Periode TNA Baru"

    @api.model
    def _read_group_state_ids(self, states, domain, order):
        state_list = [key_val[0] for key_val in self._fields['state'].selection]
        return state_list

    def action_open_submission(self):
        self.ensure_one()
        if not self.date_start_submission or not self.date_end_submission:
            raise UserError("Tanggal Mulai dan Batas Akhir Pengisian Usulan harus diisi sebelum membuka periode.")
        if self.date_start_submission > self.date_end_submission:
            raise UserError("Tanggal Mulai Pengisian tidak boleh melebihi Batas Akhir Pengisian.")
        self.state = 'open'

    def action_close_submission(self):
        self.write({'state': 'closed'})

    def action_start_processing(self):
        self.write({'state': 'processing'})

    def action_mark_completed(self):
        self.write({'state': 'completed'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})