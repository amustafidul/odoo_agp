from odoo import models, fields, api, tools, _
from odoo.exceptions import ValidationError, UserError
from odoo.http import request


class AccountKeuanganSaldoAnggaran(models.Model):
    _name = 'account.keuangan.saldo.anggaran'
    _description = 'Saldo Anggaran (Seragam)'
    _auto = False

    id = fields.Integer()
    name = fields.Char()
    account_code_id = fields.Many2one('account.account')
    kode_anggaran = fields.Char()
    account_type = fields.Selection([
        ('masuk', 'Pemasukan'),
        ('keluar', 'Pengeluaran'),
    ])
    deskripsi = fields.Char()
    saldo = fields.Float()

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute(f"""
            CREATE OR REPLACE VIEW account_keuangan_saldo_anggaran AS (
                SELECT DISTINCT
                    aka.id AS id,
                    aka.kode_anggaran || ' - ' || aka.deskripsi AS name,
                    aa.id AS account_code_id,
                    aka.kode_anggaran AS kode_anggaran,
                    aka.account_type AS account_type,
                    aka.deskripsi AS deskripsi,
                    aka.saldo AS saldo
                FROM
                    account_keuangan_kode_anggaran aka
                JOIN
                    account_account aa ON aka.account_code_id = aa.id
            )
        """)

    def name_get(self):
        return [(rec.id, f"{rec.kode_anggaran} - {rec.deskripsi}") for rec in self]


class AnggaranHr(models.Model):
    _name = 'kode.anggaran.hr'
    _description = 'Anggaran HR'

    name = fields.Char(related='kode_anggaran_id.name')
    kode_anggaran_id = fields.Many2one('account.keuangan.saldo.anggaran', domain="['|',('kode_anggaran', 'like', '69%'),"
                                                                                 "('kode_anggaran', 'like', '61%')]")
    kode_anggaran_nominal = fields.Char(related='kode_anggaran_id.kode_anggaran')
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    deskripsi_anggaran = fields.Text(compute='_compute_anggaran', store=True)
    saldo_anggaran = fields.Monetary('Saldo', compute='_compute_anggaran', store=True)

    _sql_constraints = [
        ('kode_anggaran_id_unique', 'UNIQUE(kode_anggaran_id)',
         'Kode Anggaran sudah digunakan. Tidak boleh ada duplikat!'),
    ]

    @api.depends('kode_anggaran_id')
    def _compute_anggaran(self):
        self.saldo_anggaran = 0
        self.deskripsi_anggaran = ''
        for rec in self:
            rec.deskripsi_anggaran = rec.kode_anggaran_id.deskripsi
            rec.saldo_anggaran = rec.kode_anggaran_id.saldo


class EmployeeUniform(models.Model):
    _name = 'employee.uniform'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Employee Uniform'

    name = fields.Char('Jenis Pakaian Dinas')
    uniform_type = fields.Selection([
        ('shirt', 'Shirt'),
        ('jacket', 'Jacket')
    ], string='Tipe Pakaian', default='shirt')
    department_ids = fields.Many2many('hr.department', string='Untuk Divisi')
    employee_ids = fields.Many2many('hr.employee', string='Employee', domain="['|', ('department_id', 'in', user_department_ids), ('department_id','in',department_ids)]")
    user_department_ids = fields.Many2many(
        'hr.department',
        string='User Department',
        compute='_compute_user_department'
    )
    is_employees_selected = fields.Boolean(compute='_compute_is_employees_selected')
    selected_employee_uniform_ids = fields.One2many('selected.employee.uniform', 'uniform_id', string='List Selected Employee for Uniform')
    completed_count = fields.Char('Pakaian Dinas Batik (Karyawan)', compute='_compute_completed_count')
    completed_count_percentage = fields.Integer(compute='_compute_completed_count')
    is_hc_assignment = fields.Boolean(default=True)
    is_kadiv_gm_assignment = fields.Boolean(default=False)
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    kode_anggaran_id = fields.Many2one('kode.anggaran.hr',
                                       domain="['|',('name', 'like', '69%'),"
                                              "('name', 'like', '61%')]")
    kode_anggaran_nominal = fields.Char(compute='_compute_kode_anggaran_id')
    harga_lengan_pendek_xs = fields.Monetary('Harga Lengan Pendek (XS)')
    harga_lengan_pendek_s = fields.Monetary('Harga Lengan Pendek (S)')
    harga_lengan_pendek_m = fields.Monetary('Harga Lengan Pendek (M)')
    harga_lengan_pendek_l = fields.Monetary('Harga Lengan Pendek (L)')
    harga_lengan_pendek_xl = fields.Monetary('Harga Lengan Pendek (XL)')
    harga_lengan_pendek_xxl = fields.Monetary('Harga Lengan Pendek (XXL)')
    harga_lengan_pendek_xxxl = fields.Monetary('Harga Lengan Pendek (XXXL)')
    harga_lengan_panjang_xs = fields.Monetary('Harga Lengan Panjang (XS)')
    harga_lengan_panjang_s = fields.Monetary('Harga Lengan Panjang (S)')
    harga_lengan_panjang_m = fields.Monetary('Harga Lengan Panjang (M)')
    harga_lengan_panjang_l = fields.Monetary('Harga Lengan Panjang (L)')
    harga_lengan_panjang_xl = fields.Monetary('Harga Lengan Panjang (XL)')
    harga_lengan_panjang_xxl = fields.Monetary('Harga Lengan Panjang (XXL)')
    harga_lengan_panjang_xxxl = fields.Monetary('Harga Lengan Panjang (XXXL)')
    harga_rok_xs = fields.Monetary('Harga Rok (XS)')
    harga_rok_s = fields.Monetary('Harga Rok (S)')
    harga_rok_m = fields.Monetary('Harga Rok (M)')
    harga_rok_l = fields.Monetary('Harga Rok (L)')
    harga_rok_xl = fields.Monetary('Harga Rok (XL)')
    harga_rok_xxl = fields.Monetary('Harga Rok (XXL)')
    harga_rok_xxxl = fields.Monetary('Harga Rok (XXXL)')
    harga_celana_xs = fields.Monetary('Harga Celana (XS)')
    harga_celana_s = fields.Monetary('Harga Celana (S)')
    harga_celana_m = fields.Monetary('Harga Celana (M)')
    harga_celana_l = fields.Monetary('Harga Celana (L)')
    harga_celana_xl = fields.Monetary('Harga Celana (XL)')
    harga_celana_xxl = fields.Monetary('Harga Celana (XXL)')
    harga_celana_xxxl = fields.Monetary('Harga Celana (XXXL)')
    selected_employee_uniform_count = fields.Integer(compute='_compute_selected_employee_uniform_count',
                                                     string='Uniforms')

    @api.depends('employee_ids')
    def _compute_is_employees_selected(self):
        self.is_employees_selected = self.env.user.ids == self.employee_ids.user_id.ids

    def _compute_completed_count(self):
        uniform_ids = self.ids
        all_uniforms = self.env['selected.employee.uniform'].search([('uniform_id', 'in', uniform_ids)])

        uniforms_by_uniform = {}
        for rec in all_uniforms:
            uniforms_by_uniform.setdefault(rec.uniform_id.id, self.env['selected.employee.uniform'])
            uniforms_by_uniform[rec.uniform_id.id] |= rec

        for rec in self:
            selected_uniforms = uniforms_by_uniform.get(rec.id, self.env['selected.employee.uniform'])
            completed_count = len(selected_uniforms.filtered(lambda u: u.state == 'done'))
            total_count = len(selected_uniforms)
            rec.completed_count = f"{completed_count}/{total_count} Completed"
            rec.completed_count_percentage = (completed_count / total_count) * 100 if total_count else 0

    @api.depends('department_ids')
    def _compute_user_department(self):
        all_dept_ids = set()
        for record in self:
            all_dept_ids.update(record.department_ids.ids)

        if not all_dept_ids:
            for record in self:
                record.user_department_ids = False
            return

        users = self.env['res.users'].search([
            ('department_id', 'in', list(all_dept_ids)),
            ('department_role', '=', 'manager')
        ])
        manager_dept_ids = {user.department_id.id for user in users}

        for record in self:
            record.user_department_ids = list(set(record.department_ids.ids) & manager_dept_ids)

    def action_notify_kadiv_gm(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        mail_obj = self.env['mail.mail']

        all_dept_ids = set()
        for rec in self:
            all_dept_ids.update(rec.department_ids.ids)

        if not all_dept_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Pesan Terkirim'),
                    'message': _('Tidak ada department yang terdaftar untuk mengirim notifikasi.'),
                    'type': 'warning',
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }

        managers = self.env['res.users'].search([
            ('department_id', 'in', list(all_dept_ids)),
            ('department_role', '=', 'manager')
        ])

        managers_by_dept = {}
        for manager in managers:
            if manager.department_id:
                managers_by_dept.setdefault(manager.department_id.id, self.env['res.users'])
                managers_by_dept[manager.department_id.id] |= manager

        for rec in self:
            rec_managers = self.env['res.users']
            for dept in rec.department_ids:
                rec_managers |= managers_by_dept.get(dept.id, self.env['res.users'])

            for manager in rec_managers:
                link = f"{base_url}/web#id={rec.id}&model=employee.uniform&view_type=form"
                email_body = (
                    f"Hi {manager.employee_id.name}, <br/>Anda diminta untuk mengisi form pendataan seragam untuk karyawan "
                    f"pada divisi {manager.department_id.name}. <br/>Silahkan klik link di bawah ini: <br/>{link}"
                )
                mail_values = {
                    'subject': _('HC Assignment - Pendataan Seragam Per Divisi'),
                    'body_html': email_body,
                    'email_to': manager.email,
                }
                mail_obj |= self.env['mail.mail'].create(mail_values)

        mail_obj.send()
        self.write({'is_kadiv_gm_assignment': True})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Pesan Terkirim'),
                'message': _('Pesan telah berhasil dikirim ke kepala divisi dan GM yang dipilih.'),
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def send_chat_message(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        mail_obj = self.env['mail.mail']

        for employee in self.employee_ids:
            uniform_record = self.env['selected.employee.uniform'].create({
                'employee_id': employee.id,
                'state': 'not_yet',
                'uniform_id': self.id,
            })

            link = f"{base_url}/web#id={uniform_record.id}&model=selected.employee.uniform&view_type=form"
            email_body = (
                f"Hi {employee.name}, <br/>Anda diminta untuk mengisi form pendataan seragam. <br/>"
                f"Silahkan klik link di bawah ini: <br/>{link}"
            )

            mail_values = {
                'subject': _('Pendataan Seragam Karyawan'),
                'body_html': email_body,
                'email_to': employee.user_id.email,
            }
            mail_obj |= self.env['mail.mail'].create(mail_values)

        mail_obj.send()

        self.is_hc_assignment = False

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Pesan Terkirim'),
                'message': _(
                    'Pesan telah berhasil dikirim ke semua karyawan yang dipilih dan form pendataan seragam telah dibuat.'),
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def _compute_selected_employee_uniform_count(self):
        if not self:
            return

        grouped_data = self.env['selected.employee.uniform'].read_group(
            [('uniform_id', 'in', self.ids)],
            ['uniform_id'],
            ['uniform_id']
        )

        counts = {data['uniform_id'][0]: data['__count'] for data in grouped_data}
        for record in self:
            record.selected_employee_uniform_count = counts.get(record.id, 0)

    def action_view_selected_uniforms(self):
        action = self.env.ref('agp_employee_ib.selected_employee_uniform_action').sudo().read()[0]
        if not self.env.user.has_group('base.group_erp_manager'):
            action['domain'] = [('uniform_id', '=', self.id), ('employee_id.user_id', '=', self.env.user.id)]
        else:
            action['domain'] = [('uniform_id', '=', self.id)]
        return action

    def write(self, vals):
        res = super(EmployeeUniform, self).write(vals)

        current_user_id = self.env.user.id

        all_nominals = list({rec.kode_anggaran_nominal for rec in self if rec.kode_anggaran_nominal})
        kkhc_lines_by_nominal = {}
        if all_nominals:
            kkhc_lines = self.env['account.keuangan.kkhc.line'].search([
                ('kkhc_id.state', '=', 'approved'),
                ('kode_anggaran_id.kode_anggaran', 'in', all_nominals)
            ])
            for line in kkhc_lines:
                key = line.kode_anggaran_id.kode_anggaran
                kkhc_lines_by_nominal.setdefault(key, self.env['account.keuangan.kkhc.line'])
                kkhc_lines_by_nominal[key] |= line

        for rec in self:
            budget = rec.kode_anggaran_id
            if budget:
                harga_total = (
                        rec.harga_lengan_pendek_xs
                        + rec.harga_lengan_pendek_s
                        + rec.harga_lengan_pendek_m
                        + rec.harga_lengan_pendek_l
                        + rec.harga_lengan_pendek_xl
                        + rec.harga_lengan_pendek_xxl
                        + rec.harga_lengan_pendek_xxxl
                        + rec.harga_lengan_panjang_xs
                        + rec.harga_lengan_panjang_s
                        + rec.harga_lengan_panjang_m
                        + rec.harga_lengan_panjang_l
                        + rec.harga_lengan_panjang_xl
                        + rec.harga_lengan_panjang_xxl
                        + rec.harga_lengan_panjang_xxxl
                        + rec.harga_rok_xs
                        + rec.harga_rok_s
                        + rec.harga_rok_m
                        + rec.harga_rok_l
                        + rec.harga_rok_xl
                        + rec.harga_rok_xxl
                        + rec.harga_rok_xxxl
                        + rec.harga_celana_xs
                        + rec.harga_celana_s
                        + rec.harga_celana_m
                        + rec.harga_celana_l
                        + rec.harga_celana_xl
                        + rec.harga_celana_xxl
                        + rec.harga_celana_xxxl
                )
                lines = kkhc_lines_by_nominal.get(rec.kode_anggaran_nominal, self.env['account.keuangan.kkhc.line'])
                for update_line in lines:
                    update_line.nominal_pengajuan += harga_total

            if rec.is_hc_assignment:
                if rec.department_ids:
                    user_kadiv = self.env['res.users'].search([
                        ('department_id', 'in', rec.department_ids.ids),
                        ('department_role', '=', 'manager'),
                        ('id', '=', current_user_id)
                    ])
                    if not user_kadiv:
                        raise UserError(
                            _("Anda tidak berhak membuat form pendataan seragam.\nSilahkan hubungi Administrator."))
        return res

    @api.depends('kode_anggaran_id')
    def _compute_kode_anggaran_id(self):
        for rec in self:
            if rec.kode_anggaran_id:
                kode_anggaran = rec.kode_anggaran_id.name.split()
                rec.kode_anggaran_nominal = kode_anggaran[0]
            else:
                rec.kode_anggaran_nominal = ''

    @api.onchange(
                  'harga_lengan_pendek_xs',
                  'harga_lengan_pendek_s',
                  'harga_lengan_pendek_m',
                  'harga_lengan_pendek_l',
                  'harga_lengan_pendek_xl',
                  'harga_lengan_pendek_xxl',
                  'harga_lengan_pendek_xxxl',
                  'harga_lengan_panjang_xs',
                  'harga_lengan_panjang_s',
                  'harga_lengan_panjang_m',
                  'harga_lengan_panjang_l',
                  'harga_lengan_panjang_xl',
                  'harga_lengan_panjang_xxl',
                  'harga_lengan_panjang_xxxl',
                  'harga_rok_xs',
                  'harga_rok_s',
                  'harga_rok_m',
                  'harga_rok_l',
                  'harga_rok_xl',
                  'harga_rok_xxl',
                  'harga_rok_xxxl',
                  'harga_celana_xs',
                  'harga_celana_s',
                  'harga_celana_m',
                  'harga_celana_l',
                  'harga_celana_xl',
                  'harga_celana_xxl',
                  'harga_celana_xxxl'
                  )
    def _onchange_harga(self):
        for rec in self:
            saldo_anggaran = rec.kode_anggaran_id.saldo_anggaran if rec.kode_anggaran_id else 0
            harga_total = sum(getattr(rec, field) for field in self._fields if field.startswith('harga_'))

            if harga_total > saldo_anggaran:
                raise UserError(_("Harga melebihi saldo anggaran yang ada. Silahkan cek kembali anggaran anda."))


class RedirectURLLog(models.TransientModel):
    _name = 'redirect.url.log'
    _description = 'Redirect URL Log'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    target_url = fields.Char(string='Target URL', required=True)
    timestamp = fields.Datetime(string='Timestamp', default=fields.Datetime.now, required=True)
    is_processed = fields.Boolean(string='Processed', default=False)


class SelectedEmployeeUniform(models.Model):
    _name = 'selected.employee.uniform'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Selected Employee Uniform'

    name = fields.Char(compute='_compute_name')
    employee_id = fields.Many2one('hr.employee', string='Employee', default=lambda self: self.env.user.employee_id)
    employee_ids = fields.Many2many('hr.employee', related='uniform_id.employee_ids')
    employment_type = fields.Selection(related='employee_id.employment_type', string='Jenis Karyawan')
    lengan = fields.Selection([
        ('panjang', 'Panjang'),
        ('pendek', 'Pendek')
    ], string='Lengan Panjang / Pendek')
    ukuran_atasan = fields.Selection([
        ('xs', 'XS'),
        ('s', 'S'),
        ('m', 'M'),
        ('l', 'L'),
        ('xl', 'XL'),
        ('xxl', 'XXL'),
        ('xxxl', 'XXXL'),
    ], string='Ukuran Pakaian (Atasan)')
    jenis_bawahan_pakaian = fields.Selection([
        ('rok', 'Rok'),
        ('celana', 'Celana')
    ], string='Jenis Bawahan')
    ukuran_bawahan = fields.Selection([
        ('xs', 'XS'),
        ('s', 'S'),
        ('m', 'M'),
        ('l', 'L'),
        ('xl', 'XL'),
        ('xxl', 'XXL'),
        ('xxxl', 'XXXL'),
    ], string='Ukuran Pakaian (Bawahan)')
    state = fields.Selection([
        ('not_yet', 'Not Yet'),
        ('done', 'Done')
    ], string='Status Pengisian Form')
    complete_stage = fields.Char(compute='_compute_complete_stage')

    ### currency
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    ###

    uniform_id = fields.Many2one('employee.uniform')

    @api.depends('state')
    def _compute_complete_stage(self):
        self.complete_stage = ''
        for rec in self:
            if rec.state == 'not_yet':
                rec.complete_stage = 'Not Completed'
            elif rec.state == 'done':
                rec.complete_stage = 'Completed'

    @api.depends('employee_id')
    def _compute_name(self):
        self.name = 'New'
        for rec in self:
            rec.name = 'Seragam untuk ' + rec.employee_id.name

    is_employees_selected = fields.Boolean(compute='_compute_is_employees_selected')

    @api.depends('employee_id')
    def _compute_is_employees_selected(self):
        self.is_employees_selected = self.env.user.id == self.employee_id.user_id.id

    def mark_as_done(self):
        required_fields = ['employee_id', 'lengan', 'ukuran_atasan', 'jenis_bawahan_pakaian', 'ukuran_bawahan']
        for rec in self:
            if any(not getattr(rec, field) for field in required_fields):
                raise ValidationError(_('Semua field wajib diisi sebelum menutup form ini.'))
            rec.state = 'done'

    def redirect_if_user_mismatch(self):
        for rec in self:
            if self.env.user.id != rec.employee_id.user_id.id:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                target_url = f"{base_url}/web#id={rec.id}&model=selected.employee.uniform&view_type=form"

                self.env['redirect.url.log'].create({
                    'employee_id': self.employee_id.id,
                    'user_id': self.employee_id.user_id.id,
                    'target_url': target_url,
                })

                return request.redirect(
                    '/web/session/logout?message=Anda tidak memiliki akses ke formulir ini. Harap login kembali.')

    def read(self, fields, load='_classic_read'):
        for rec in self:
            rec.redirect_if_user_mismatch()
        return super(SelectedEmployeeUniform, self).read(fields, load=load)