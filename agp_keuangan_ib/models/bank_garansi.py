from odoo import models, fields, api, _
from babel.dates import format_date


class BankGaransi(models.Model):
    _name = 'account.keuangan.bank.garansi'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Bank Garansi'

    name = fields.Char(string='Nama Bank Garansi', tracking=True)
    unit_kerja = fields.Char(string='Unit Kerja', tracking=True)
    pemberi_kerja = fields.Char(string='Pemberi Kerja', tracking=True)
    pekerjaan = fields.Char(string='Pekerjaan', tracking=True)
    branch_id = fields.Many2many('res.branch', string='Nama Cabang', tracking=True)
    no_bank_garansi = fields.Char(string='Nomor Bank Garansi', tracking=True)
    tanggal_bank_garansi = fields.Date(string='Tanggal Bank Garansi', required=True, tracking=True)
    mulai_garansi = fields.Date(string='Tanggal Mulai Bank Garansi', required=True, tracking=True)
    akhir_garansi = fields.Date(string='Tanggal Akhir Bank Garansi', required=True, tracking=True)
    masa_klaim = fields.Date(string='Masa Klaim', required=True, tracking=True)

    # tipe_bank_garansi = fields.Char(string='Tipe Bank garansi', tracking=True)
    
    nominal_bank_garansi = fields.Char(string='Nominal Bank Garansi', tracking=True)
    nominal_bank_garansii = fields.Float(string='Nominal Bank Garansi', tracking=True)
    nama_asuransi = fields.Char(string='Nama / Jenis Asuransi', tracking=True)
    nominal_jaminan = fields.Float(string='Jaminan Bank Garansi', required=True, tracking=True)
    # nama_bank_garansi = fields.Char(string='Nama Bank Garansi', tracking=True)
    biaya_asuransi = fields.Float(string='Biaya Administrasi', required=True, tracking=True)
    nama_bank_garansi = fields.Char(string='Nama Bank Garansi', tracking=True)
    bank_cabang = fields.Char(string='Bank Cabang Pembuatan Garansi', tracking=True)

    jangka_waktu = fields.Integer(string='Jangka Waktu (hari)', compute='_compute_jangka_waktu', store=True, tracking=True)

    keterangan = fields.Text(string='Keterangan', tracking=True)

    sub_branch_ids = fields.Many2many('sub.branch', string='Unit Kerja', tracking=True)

    unit_penempatan_id = fields.Many2one('hr.employee.unit', string='Divisi', required=True, store=True, tracking=True)

    deposito_ids = fields.One2many(
        'account.keuangan.deposito', 
        'nama_bank_garansi', 
        string='Deposito'
    )

    tipe_bank_garansi_id = fields.Many2one('account.keuangan.tipe.bank.garansi', string='Tipe Bank garansi', tracking=True)
    jenis_bank_garansi_id = fields.Many2one('account.keuangan.jenis.bank.garansi', string='Jenis Bank garansi', tracking=True)
    
    dana_kembali = fields.Float(string='Dana Kembali', compute='_compute_dana_kembali', store=True, tracking=True)

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)

    user_branch_id = fields.Many2one(
        'res.branch', 
        string='User Branch', 
        compute='_compute_user_branch', 
        store=True
    )
    branch_address = fields.Char(
        string='Branch Address', 
        compute='_compute_user_branch', 
        store=True
    )

    phone_branch = fields.Char(compute="_compute_user_branch_phone", store=True)
    email_branch = fields.Char(compute="_compute_user_branch_email", store=True)
    website_branch = fields.Char(compute="_compute_user_branch_website", store=True)

    @api.onchange('user_id')
    def _onchange_user_id(self):
        self._compute_user_branch()
        self._compute_user_branch_phone()
        self._compute_user_branch_email()
        self._compute_user_branch_website()


    @api.depends('user_id.branch_id')
    def _compute_user_branch(self):
        for record in self:
            branch = record.user_id.branch_id
            record.user_branch_id = branch
            if branch:
                address = f"{branch.street or ''}, {branch.street2 or ''}, {branch.city or ''}, {branch.state_id.name or ''}, {branch.zip or ''}"
                record.branch_address = address.strip(', ')
            else:
                record.branch_address = ''

    @api.depends('user_id.branch_id')
    def _compute_user_branch_phone(self):
        for record in self:
            branch = record.user_id.branch_id
            record.phone_branch = branch.phone or ''

    @api.depends('user_id.branch_id')
    def _compute_user_branch_email(self):
        for record in self:
            branch = record.user_id.branch_id
            record.email_branch = branch.email or ''

    @api.depends('user_id.branch_id')
    def _compute_user_branch_website(self):
        for record in self:
            branch = record.user_id.branch_id
            record.website_branch = branch.website or ''

    
    @api.depends('nominal_jaminan')
    def _compute_dana_kembali(self):
        for rec in self:
            rec.dana_kembali = (rec.nominal_jaminan or 0.0) * 0.1

    @api.depends('mulai_garansi', 'akhir_garansi')
    def _compute_jangka_waktu(self):
        for record in self:
            if record.mulai_garansi and record.akhir_garansi:
                mulai_garansi = fields.Date.from_string(record.mulai_garansi)
                akhir_garansi = fields.Date.from_string(record.akhir_garansi)
                delta = akhir_garansi - mulai_garansi
                record.jangka_waktu = delta.days
            else:
                record.jangka_waktu = 0


    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        if self.branch_id:
            return {'domain': {'sub_branch_ids': [('id', 'in', self.branch_id.sub_branch_ids.ids)]}}
        else:
            return {'domain': {'sub_branch_ids': []}}

    
    # # Override name_get method
    # def name_get(self):
    #     result = []
    #     for record in self:
    #         name = record.nama_bank_garansi  # Customize this to include other fields if necessary
    #         result.append((record.id, name))
    #     return result


    def action_open_export_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Export Bank Garansi',
            'res_model': 'bank.garansi.export.wizard',
            'view_mode': 'form',
            'target': 'new',
        }
    

    def get_deposito_data(self):
        self.ensure_one()  # Pastikan hanya satu record saat dipanggil
        return [{
            'name': d.name,
            'tanggal_deposito': format_date(d.tanggal_deposito, format='d MMMM y', locale='id') if d.tanggal_deposito else '',
            'tanggal_jatuh_tempo': format_date(d.tanggal_jatuh_tempo, format='d MMMM y', locale='id') if d.tanggal_jatuh_tempo else '',
            'saldo': "{:,.0f}".format(d.saldo or 0.0),
        } for d in self.deposito_ids]
    

    def get_records_dict(self):
        domain = []
        if self.tipe_bank_garansi_id:
            domain.append(('tipe_bank_garansi_id', '=', self.tipe_bank_garansi_id.id))

        records = self.env['account.keuangan.bank.garansi'].search(domain)

        result = []
        for rec in records:
            result.append({
                'sub_branch': ', '.join(rec.sub_branch_ids.mapped('name')),
                'pemberi_kerja': rec.pemberi_kerja or '',
                'pekerjaan': rec.pekerjaan or '',
                'name': rec.name or '',
                'tanggal_bank_garansi': rec.tanggal_bank_garansi.strftime('%d-%m-%Y') if rec.tanggal_bank_garansi else '',
                'nominal_jaminan': rec.nominal_jaminan or 0.0,
                'mulai_garansi': rec.mulai_garansi.strftime('%d-%m-%Y') if rec.mulai_garansi else '',
                'akhir_garansi': rec.akhir_garansi.strftime('%d-%m-%Y') if rec.akhir_garansi else '',
                'jenis_bank_garansi': rec.jenis_bank_garansi_id.name if rec.jenis_bank_garansi_id else '',
                'bank_cabang': rec.bank_cabang or '',
                'nama_asuransi': rec.nama_asuransi or '',
                'biaya_asuransi': rec.biaya_asuransi or 0.0,
                'dana_kembali': rec.dana_kembali or 0.0,
                'keterangan': rec.keterangan or '',
            })

        return result



class TipeBankGaransi(models.Model):
    _name = 'account.keuangan.tipe.bank.garansi'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Tipe Bank Garansi'

    name = fields.Char(string='Tipe Bank Garansi', tracking=True)
    


class JenisBankGaransi(models.Model):
    _name = 'account.keuangan.jenis.bank.garansi'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Jenis Bank Garansi'

    name = fields.Char(string='Jenis Bank Garansi', tracking=True)