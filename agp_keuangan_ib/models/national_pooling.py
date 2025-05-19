from odoo import models, fields, api, _
import babel.dates
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math


import base64
import io
import xlsxwriter


class NationalPooling(models.Model):
    _name = 'account.keuangan.np'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'National Pooling'

    name = fields.Char(string='National Pooling Number', required=True, tracking=True)
    
    uraian_pooling = fields.Text(string='Uraian National Pooling', tracking=True)
    # total_pooling = fields.Float(string='Total National Pooling', compute='_compute_total_jumlah', store=True, tracking=True)

    bank = fields.Char(string='Bank Sinking Fund', tracking=True)
    rekening = fields.Char(string='Rekening Sinking Fund', tracking=True)
    maturity_date = fields.Date(string='Maturity Date', required=True, tracking=True)

    np_line_ids = fields.One2many('account.keuangan.np.line', 'np_id', string='National Pooling Lines', tracking=True)

    # Compute fields
    total_sinking_fund = fields.Float(string='Total Penerimaan / Pengeluaran Sinking Fund', compute='_compute_totals', store=True, tracking=True)
    total_deposito = fields.Float(string='Total Pembuatan/Pencairan Deposito', compute='_compute_totals', store=True, tracking=True)
    total_pendapatan = fields.Float(string='Total Pendapatan', compute='_compute_totals', store=True, tracking=True)
    total_biaya_admin = fields.Float(string='Total Pendapatan dan Biaya Administrasi Bank ', compute='_compute_totals', store=True, tracking=True)
    total_saldo = fields.Float(string='Total Saldo', compute='_compute_totals', store=True, tracking=True)


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


    @api.depends('np_line_ids')
    def _compute_totals(self):
        for record in self:
            total_sinking_fund = sum(line.nominal_penempatan for line in record.np_line_ids if line.type == 'sinking_fund')
            total_deposito = sum(line.nominal_penempatan for line in record.np_line_ids if line.type == 'deposito')
            total_pendapatan = sum(line.nominal_penempatan for line in record.np_line_ids if line.type == 'pendapatan')
            total_biaya_admin =  sum(line.nominal_penempatan for line in record.np_line_ids if line.type == 'biaya_admin')
            record.total_sinking_fund = total_sinking_fund
            record.total_deposito = total_deposito
            record.total_pendapatan = total_pendapatan
            record.total_biaya_admin = total_pendapatan - total_biaya_admin
            record.total_saldo = total_sinking_fund + total_deposito - total_biaya_admin
   

    @api.depends('np_line_ids.nominal_penempatan')
    def _compute_total_jumlah(self):
        for record in self:
            record.total_pooling = sum(line.nominal_penempatan for line in record.np_line_ids)

    def export_to_excel(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Shareholder Loan')

        # Menambahkan informasi di atas table sebagai judul
        sheet.write(0, 0, f"Nomor: {self.name or ''}")
        sheet.write(1, 0, f"Uraian: {self.uraian_pooling or ''}")
        sheet.write(2, 0, f"Bank: {self.bank or ''}")
        sheet.write(3, 0, f"Rekening: {self.rekening or ''}")
        sheet.write(4, 0, f"Maturity Date: {self.maturity_date.strftime('%d/%m/%Y') if self.maturity_date else ''}")
        sheet.write(5, 0, f"Total Pooling: {self.total_pooling if self.total_pooling else ''}")

        
        # Menambahkan header untuk data tabel
        headers = ['Uraian', 'Tanggal', 'Nominal']
        for col, header in enumerate(headers):
            sheet.write(7, col, header)  # Start from row 11 after the titles

        # Menambahkan data untuk setiap baris 'sinking_line_ids'
        for row, line in enumerate(self.np_line_ids, start=8):
            sheet.write(row, 0, line.uraian_line)
            sheet.write(row, 1, line.tanggal_transfer.strftime('%d/%m/%Y') if line.tanggal_transfer else '')
            sheet.write(row, 2, line.nominal_penempatan)

            row += 1

        # Selesaikan dan simpan file
        workbook.close()
        output.seek(0)
        file_data = output.read()
        output.close()

        # Buat attachment dari file
        attachment = self.env['ir.attachment'].create({
            'name': f'{self.name}_{datetime.now().strftime("%Y%m%d%H%M%S")}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(file_data),
            'store_fname': f'{self.name}.xlsx',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': 'account.keuangan.np',
            'res_id': self.id,
        })

        # Membuka file attachment
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }
    

    def action_open_export_np_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Export National Pooling',
            'res_model': 'np.export.wizard',
            'view_mode': 'form',
            'target': 'new',
        }



class NationalPoolingLine(models.Model):
    _name = 'account.keuangan.np.line'
    _description = 'National Pooling Line'

    np_id = fields.Many2one('account.keuangan.np', string='National Pooling Lines', required=True, tracking=True)

    tanggal_transfer = fields.Date(string='Tanggal Transfer', tracking=True)
    nominal_penempatan = fields.Float(string='Nominal Penempatan', tracking=True)
    uraian_line = fields.Text(string='Uraian / Deskripsi', tracking=True)

    MONTH_SELECTION = [
        ('01', 'Januari'),
        ('02', 'Februari'),
        ('03', 'Maret'),
        ('04', 'April'),
        ('05', 'Mei'),
        ('06', 'Juni'),
        ('07', 'Juli'),
        ('08', 'Agustus'),
        ('09', 'September'),
        ('10', 'Oktober'),
        ('11', 'November'),
        ('12', 'Desember')
    ]

    YEAR_SELECTION = [(str(year), str(year)) for year in range(2020, 2050)]

    related_month = fields.Selection(MONTH_SELECTION, string="Bulan", tracking=True)
    related_year = fields.Selection(YEAR_SELECTION, string="Tahun", tracking=True)

    type = fields.Selection([
        ('deposito', 'Pembuatan/Pencairan Deposito'),
        ('sinking_fund', 'Penerimaan/Pengeluaran Sinking Fund'),
        ('biaya_admin', 'Biaya Administrasi Bank'),
        ('pendapatan', 'Pendapatan / Bunga Bank'),
    ], string='Type', tracking=True)


    type_display = fields.Char(string='Type Display', compute='_compute_type_display', store=True)
   
    @api.depends('type')
    def _compute_type_display(self):
        for rec in self:
            rec.type_display = dict(self.fields_get(allfields=['type'])['type']['selection']).get(rec.type, '')