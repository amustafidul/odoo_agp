from odoo import models, fields, api

class AccountKeuanganSuratPerjanjian(models.Model):
    _name = 'account.keuangan.surat.perjanjian'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Account Keuangan Surat Perjanjian'

    name = fields.Char(string='Nomor Surat Perjanjian')
    # bank_account = fields.Char(string='Bank Account')
    tanggal_perjanjian = fields.Date(string='Tanggal Perjanjian', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    branch_id = fields.Many2many('res.branch', string='Branch')
    sub_branch_ids = fields.Many2many('sub.branch', string="Sub Branches")
    bank_account_id = fields.Many2one('res.partner.bank', string='Bank Account')
    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
   
    surat_perjanjian_line_ids = fields.One2many('account.keuangan.surat.perjanjian.line', 'nomor_perjanjian_id', string='Surat Perjanjian Lines')
    
    bank_account_harian_id = fields.Many2one(
        'account.keuangan.bank.harian.master',
        string='Bank Account'
    )

class AccountKeuanganSuratPerjanjian(models.Model):
    _name = 'account.keuangan.surat.perjanjian.line'
    _description = 'Account Keuangan Surat Perjanjian Line'

    nomor_perjanjian_id = fields.Many2one('account.keuangan.surat.perjanjian', string='Surat Perjanjian')

    no_adddendum = fields.Char(string='Nomor Addendum')
    deskripsi = fields.Text(string='Deskripsi')
    tanggal_addendum_mulai = fields.Date(string='Tanggal Mulai', tracking=True)
    tanggal_addendum_akhir = fields.Date(string='Tanggal Akhir', tracking=True)
    # bank_account_id = fields.Many2one('res.partner.bank', string='Bank Account')

    # bank_account_harian_id = fields.Many2one(
    #     'account.keuangan.bank.harian.master', 
    #     string='Bank Account'
    # )
    # Menentukan field yang ditampilkan di dropdown (bukan ID)
    _rec_name = 'no_adddendum'