from odoo import models, fields, api, _
import logging
from num2words import num2words
from math import floor

from odoo.tools import format_date
from babel.dates import format_date


_logger = logging.getLogger(__name__)

class PermohonanPembayaran(models.Model):
    _name = 'account.keuangan.permohonan.pembayaran'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Permohonan Pembayaran'

    name = fields.Char(string='Nomor Surat', required=True, tracking=True)
    invoice_id = fields.Many2one(
        'account.keuangan.invoice', 
        string='Invoice', 
        required=True
    )

    nomor_referensi = fields.Char(related='invoice_id.nomor_referensi', string="Nomor", readonly=True)
    tempat = fields.Char(string='Tempat', tracking=True)
    tanggal = fields.Date(string='Tanggal dibuat', required=True, tracking=True)
    perihal = fields.Char(string='Perihal', tracking=True)
    lampiran = fields.Char(string='Lampiran', tracking=True)
    kepada = fields.Char(related='invoice_id.kepada', string="Kepada", readonly=True)
    ditujukan_kepada = fields.Many2one(related='invoice_id.ditujukan_kepada', string='Nama Perusahaan', required=True, tracking=True)
    alamat_perusahaan = fields.Char(related='invoice_id.alamat_perusahaan', string="Alamat Perusahaan", readonly=True)

    kata_pengantar = fields.Text(string='Kata Pengantar', tracking=True)
    # kata_pengantar2 = fields.Html(string='Kata Pengantar', tracking=True)
    nomor_surat_perjanjian = fields.Char(related='invoice_id.nomor_surat_perjanjian', string='Nomor Surat Perjanjian', tracking=True)
    tanggal_perjanjian = fields.Date(related='invoice_id.tanggal_perjanjian', string='Tanggal Perjanjian', tracking=True)
    total_sesudah_pajak = fields.Float(related='invoice_id.total_sesudah_pajak', string='Jumlah Tagihan', compute='_compute_sesudah_pajak', store=True, tracking=True)
    total_terbilang = fields.Char(related='invoice_id.total_terbilang', string='Jumlah Terbilang', compute='_compute_total_terbilang')
    jabatan = fields.Char(string='Jabatan', tracking=True)
    ttd = fields.Char(string='Yang Bertanda Tangan', tracking=True)
    
    bank_account_id = fields.Many2one('res.partner.bank', string="Bank Account")

    acc_holder_name = fields.Char(
        string="Bank",
        related='bank_account_id.acc_holder_name', 
        readonly=True
    )

    acc_number = fields.Char(
        string="No. Rek",
        related='bank_account_id.acc_number', 
        readonly=True
    )
    phone = fields.Char(
        string="Phone"
        # related='bank_account_id.phone',
        # readonly=True
    )
    email = fields.Char(
        string="Email"
        # related='bank_account_id.email', 
        # readonly=True
    )
    company_name = fields.Char(
        string="Nama"
    )

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    formatted_date = fields.Char(
        string='Formatted Date', 
        compute='_compute_formatted_date', 
        readonly=True
    )

    branch_id = fields.Many2one('res.branch', string='Branch', tracking=True)

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

    @api.depends('branch_id')
    def _compute_user_branch(self):
        for record in self:
            user = self.env.user
            branch = user.branch_id  # Mengambil branch dari user yang login
            record.user_branch_id = branch
            if branch:
                address = f"{branch.street or ''}, {branch.street2 or ''}, {branch.city or ''}, {branch.state_id.name or ''}, {branch.country_id.name or ''}, {branch.zip or ''}"
                record.branch_address = address.strip(', ')
            else:
                record.branch_address = ''

    @api.depends('tanggal')
    def _compute_formatted_date(self):
        for record in self:
            if record.tanggal:
                record.formatted_date = format_date(
                    record.tanggal, 
                    format='d MMMM y', 
                    locale='id_ID'
                )
            else:
                record.formatted_date = 'N/A'
