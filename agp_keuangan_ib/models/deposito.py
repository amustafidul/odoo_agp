from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta


class Deposito(models.Model):
    _name = 'account.keuangan.deposito'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Deposito'

    name = fields.Char(string='Deposito Number', required=True, tracking=True)
    no_rek = fields.Char(string='Nomor Rekening', required=True, tracking=True)
    billyet = fields.Char(string='Nomor Billyet', tracking=True)

    status_pencairan = fields.Selection([
        ('aktif', 'Sudah'),
        ('non_aktif', 'Belum'),
    ], string="Status Pencairan", compute="_compute_status_pencairan", store=True, tracking=True)
    
    status_pencairan_display = fields.Char(string="Status Pencairan (Display)", compute="_compute_status_pencairan_display", store=True)

    periode_produk_id = fields.Many2one(
        'account.keuangan.periode.produk',
        string='Periode Produk',
        required=True, 
        tracking=True
    )

    keterangan = fields.Text(string='Keterangan', tracking=True)
    tanggal_deposito = fields.Date(string='Tanggal Deposito', required=True, tracking=True)
    tanggal_pencairan = fields.Date(string='Tanggal Pencairan', tracking=True)
    tanggal_jatuh_tempo = fields.Date(string='Tanggal Jatuh Tempo', required=True, tracking=True)
    
    tipe_produk = fields.Selection([
        ('mma', 'MMA'),
        ('deposito', 'Deposito'),
    ], tracking=True)

    tipe_produk_display = fields.Char(string="Tipe Produk (Display)", compute="_compute_tipe_produk_display", store=True)

    status_tergadai = fields.Selection([
        ('yes', 'Ya'),
        ('no', 'Tidak'),
    ], tracking=True)

    status_tergadai_display = fields.Char(string="Status Tergadai (Display)", compute="_compute_status_tergadai_display", store=True)
    
    branch_id = fields.Many2many('res.branch', string='Nama Cabang', tracking=True, domain="[('company_id', '=', company_id)]")
    saldo = fields.Float(string='Saldo', tracking=True)
    bank_pembuka = fields.Text(string='Bank Cabang Pembuka', tracking=True)
    
    currency_id = fields.Many2one(
        'res.currency', 
        string='Mata Uang', 
        domain="[('active', '=', True)]",  # Hanya mata uang yang aktif
        required=True, 
        tracking=True
    )

    presentase_bunga = fields.Float(
        string='Persentase Bunga (%)',
        digits=(6, 2),  # Mengatur digit agar tampil hingga 2 tempat desimal
        help='Persentase bunga yang diterapkan', 
        tracking=True
    )

    no_gadai = fields.Char(string='Nomor Gadai', tracking=True)

    # Related field to Bank Garansi (conditional field)
    nama_bank_garansi = fields.Many2one('account.keuangan.bank.garansi', string='Nama Bank Garansi', tracking=True)
    bank_garansi_ids = fields.Many2one('account.keuangan.bank.garansi', string='Bank Garansi')

    jangka_waktu = fields.Integer(string='Jangka Waktu (Bulan)', compute='_compute_jangka_waktu', store=True, tracking=True)


    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, readonly=True)

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

    # @api.model
    # def create(self, vals):
    #     # Automatically set the branch based on the logged-in user
    #     vals['branch_id'] = self.env.user.branch_id.id  # Assuming the user has a field branch_id
    #     return super(Deposito, self).create(vals)

    @api.depends('user_id.branch_id')
    def _compute_user_branch(self):
        for record in self:
            user = self.env.user
            branch = user.branch_id  # Mengambil branch dari user yang login
            record.user_branch_id = branch
            if branch:
                address = f"{branch.street or ''}, {branch.street2 or ''}, {branch.city or ''}, {branch.state_id.name or ''}, {branch.zip or ''}"
                record.branch_address = address.strip(', ')
            else:
                record.branch_address = ''

    @api.depends('user_id.branch_id')
    def _compute_user_branch_phone(self):
        for record in self:
            user = self.env.user
            branch = user.branch_id  # Mengambil branch dari user yang login
            record.phone_branch = branch.phone or ''

   
    @api.depends('user_id.branch_id')
    def _compute_user_branch_email(self):
        for record in self:
            user = self.env.user
            branch = user.branch_id  # Mengambil branch dari user yang login
            record.email_branch = branch.email or ''

    @api.depends('user_id.branch_id')
    def _compute_user_branch_website(self):
        for record in self:
            user = self.env.user
            branch = user.branch_id  # Mengambil branch dari user yang login
            record.website_branch = branch.website or ''
            
    @api.depends('status_pencairan')
    def _compute_status_pencairan_display(self):
        for rec in self:
            status_dict = dict(self._fields['status_pencairan'].selection)
            rec.status_pencairan_display = status_dict.get(rec.status_pencairan, '').upper()

    
    @api.depends('tipe_produk')
    def _compute_tipe_produk_display(self):
        for rec in self:
            tipe_produk_dict = dict(self._fields['tipe_produk'].selection)
            rec.tipe_produk_display = tipe_produk_dict.get(rec.tipe_produk, '')

    @api.depends('status_tergadai')
    def _compute_status_tergadai_display(self):
        for rec in self:
            status_tergadai_dict = dict(self._fields['status_tergadai'].selection)
            rec.status_tergadai_display = status_tergadai_dict.get(rec.status_tergadai, '')

    @api.onchange('status_tergadai')
    def _onchange_status_tergadai(self):
        if self.status_tergadai == 'no':
            self.nama_bank_garansi = False  # Clear the field if 'no' is selected@api.onchange('status_tergadai')
    
    @api.depends('tanggal_pencairan')
    def _compute_status_pencairan(self):
        for rec in self:
            if rec.tanggal_pencairan:
                rec.status_pencairan = 'aktif'
            else:
                rec.status_pencairan = 'non_aktif'
    
    @api.depends('tanggal_deposito', 'tanggal_jatuh_tempo')
    def _compute_jangka_waktu(self):
        for record in self:
            if record.tanggal_deposito and record.tanggal_jatuh_tempo:
                tanggal_deposito = fields.Date.from_string(record.tanggal_deposito)
                tanggal_jatuh_tempo = fields.Date.from_string(record.tanggal_jatuh_tempo)
                delta = relativedelta(tanggal_jatuh_tempo, tanggal_deposito)
                # Menghitung total bulan (tahun * 12 + bulan)
                record.jangka_waktu = delta.years * 12 + delta.months
            else:
                record.jangka_waktu = 0

    @api.onchange('nama_bank_garansi')
    def _onchange_nama_bank_garansi(self):
        if self.nama_bank_garansi:
            self.branch_id = self.nama_bank_garansi.branch_id
            self.no_gadai = self.nama_bank_garansi.no_bank_garansi
        else:
            self.branch_id = False
            self.no_gadai = False


    def action_open_export_deposito_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Export Deposito',
            'res_model': 'deposito.export.wizard',
            'view_mode': 'form',
            'target': 'new',
        }