from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class TnaSubmission(models.Model):
    _name = 'tna.submission'
    _description = 'Form Usulan TNA oleh Departemen/Cabang'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'period_id desc, create_date desc, name'

    name = fields.Char(
        string='Nomor Usulan TNA',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: 'Baru'
    )
    period_id = fields.Many2one(
        'tna.period',
        string='Periode TNA',
        required=True,
        ondelete='restrict',
        tracking=True,
        domain=[('state', '=', 'open'),('date_start_submission', '<=', fields.Date.today()),('date_end_submission', '>=', fields.Date.today())],
        help="Pilih periode TNA yang sedang dibuka untuk pengisian usulan."
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Divisi Pengusul',
        required=True,
        tracking=True
    )
    branch_id = fields.Many2one(
        'res.branch',
        string='Cabang Pengusul',
        tracking=True,
        domain="[('company_id', '=', company_id)]"
    )
    company_id = fields.Many2one(
        'res.company',
        string='Perusahaan',
        related='period_id.company_id',
        store=True,
        readonly=True
    )
    user_id = fields.Many2one(
        'res.users',
        string='Diajukan Oleh (User Sistem)',
        default=lambda self: self.env.user,
        tracking=True,
        readonly=True
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Penanggung Jawab Usulan (Pegawai)',
        tracking=True,
        compute='_compute_employee_id_from_user',
        inverse='_inverse_employee_id_from_user',
        readonly=False,
        store=True,
        help="Pegawai (Kadiv/GM) yang bertanggung jawab atas usulan TNA ini."
    )
    submission_date = fields.Datetime(
        string='Tanggal Diajukan ke SDM',
        readonly=True,
        copy=False,
        tracking=True
    )
    gm_approval_user_id = fields.Many2one(
        'res.users',
        string='Disetujui oleh GM (User)',
        tracking=True,
        copy=False
    )
    gm_approval_date = fields.Date(
        string='Tanggal Persetujuan GM',
        tracking=True,
        copy=False
    )
    proposed_training_ids = fields.One2many(
        'tna.proposed.training',
        'submission_id',
        string='Detail Usulan Kebutuhan Training',
        copy=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Diajukan ke SDM'),
        # ('under_review_sdm', 'Ditinjau SDM'),
        ('processed', 'Selesai Diproses SDM')
        ],
        string='Status Usulan',
        default='draft',
        copy=False,
        tracking=True,
        index=True,
        group_expand='_read_group_state_ids'
    )
    notes_kadiv_gm = fields.Text(
        string='Catatan Pengusul (Kadiv/GM)'
    )
    notes_sdm = fields.Text(
        string='Catatan Review dari SDM Pusat',
        readonly=True
    )
    total_proposed_trainings = fields.Integer(
        compute='_compute_summary_totals',
        string='Jumlah Judul Usulan Training',
        store=True
    )
    total_estimated_cost = fields.Monetary(
        compute='_compute_summary_totals',
        string='Total Estimasi Biaya Usulan',
        currency_field='currency_id',
        store=True
    )
    total_estimated_participants = fields.Integer(
        compute='_compute_summary_totals',
        string='Total Estimasi Peserta',
        store=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Mata Uang',
        related='company_id.currency_id',
        store=True,
        readonly=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Baru') == 'Baru':
                sequence_code = 'tna.submission.sequence'
                period_id = vals.get('period_id')
                prefix = f"TNASUB/{fields.Date.today().year}/"
                if period_id:
                    period = self.env['tna.period'].browse(period_id)
                    if period.year:
                       prefix = f"TNASUB/{period.year}/"

                vals['name'] = self.env['ir.sequence'].with_company(
                    vals.get('company_id')
                ).next_by_code(sequence_code, sequence_date=fields.Date.today()) or 'Baru'
        return super().create(vals_list)

    @api.model
    def default_get(self, fields_list):
        res = super(TnaSubmission, self).default_get(fields_list)
        if 'employee_id' not in res and self.env.user.employee_ids:
            res['employee_id'] = self.env.user.employee_ids[0].id
        return res

    @api.depends('user_id')
    def _compute_employee_id_from_user(self):
        for submission in self:
            if submission.user_id and submission.user_id.employee_ids:
                submission.employee_id = submission.user_id.employee_ids[0]
            elif not submission.employee_id:
                submission.employee_id = False

    def _inverse_employee_id_from_user(self):
        pass

    @api.depends('proposed_training_ids',
                 'proposed_training_ids.estimated_cost',
                 'proposed_training_ids.estimated_participant_count')
    def _compute_summary_totals(self):
        for submission in self:
            submission.total_proposed_trainings = len(submission.proposed_training_ids)
            submission.total_estimated_cost = sum(pt.estimated_cost for pt in submission.proposed_training_ids)
            submission.total_estimated_participants = sum(pt.estimated_participant_count for pt in submission.proposed_training_ids)

    @api.model
    def _read_group_state_ids(self, states, domain, order):
        state_list = [key_val[0] for key_val in self._fields['state'].selection]
        return state_list

    def action_submit_to_sdm(self):
        self.ensure_one()
        if not self.proposed_training_ids:
            raise UserError("Harap isi minimal satu detail usulan training sebelum mengajukan ke SDM.")

        self.proposed_training_ids.filtered(lambda line: line.state == 'new').write({'state': 'pending_approval'})

        self.write({
            'state': 'submitted',
            'submission_date': fields.Datetime.now()
        })
        return True

    def action_mark_processed_by_sdm(self):
        self.ensure_one()
        if any(line.state == 'pending_approval' for line in self.proposed_training_ids):
            raise UserError("Masih ada usulan training di dalam form ini yang statusnya 'Menunggu Approval SDM'. Harap proses semua usulan terlebih dahulu.")

        self.state = 'processed'
        if self.period_id and self.period_id.state == 'closed':
            self.period_id.action_start_processing()
        return True

    def action_reset_to_draft(self):
        self.ensure_one()
        if any(line.state in ['approved', 'rejected', 'realized'] for line in self.proposed_training_ids):
            raise UserError("Tidak bisa direset ke draft jika sudah ada usulan yang disetujui atau ditolak.")

        self.write({'state': 'draft', 'submission_date': False})
        self.proposed_training_ids.filtered(lambda line: line.state == 'pending_approval').write({'state': 'new'})
        return True

    @api.constrains('period_id', 'department_id', 'branch_id', 'company_id')
    def _check_unique_submission_per_period_dept_branch(self):
        for record in self:
            if record.period_id and record.department_id:
                domain = [
                    ('id', '!=', record.id),
                    ('period_id', '=', record.period_id.id),
                    ('department_id', '=', record.department_id.id),
                    ('company_id', '=', record.company_id.id)
                ]
                if record.branch_id:
                    domain.append(('branch_id', '=', record.branch_id.id))
                else:
                    domain.append(('branch_id', '=', False))

                existing_count = self.search_count(domain)
                if existing_count > 0:
                    branch_name = f" dan Cabang '{record.branch_id.name}'" if record.branch_id else ""
                    raise ValidationError(
                        f"Usulan TNA untuk Divisi '{record.department_id.name}'{branch_name} "
                        f"pada periode '{record.period_id.name}' sudah ada."
                    )