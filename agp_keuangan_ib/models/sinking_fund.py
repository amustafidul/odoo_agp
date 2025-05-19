from odoo import models, fields, api, _
import babel.dates
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math


import base64
import io
import xlsxwriter


class SinkingFund(models.Model):
    _name = 'account.keuangan.sinking'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Sinking Fund Note'

    name = fields.Char(string='Singking Fund Notes', required=True, tracking=True)
    tipe_notes = fields.Selection([   
        ('mtn', 'MTN'),
        ('ltn', 'LTN'),
        ('ipk', 'Imbalan Pasca Kerja'),
        # Tambahkan status lain jika perlu
    ], tracking=True) 

    tipe_notes_display = fields.Char(string="Tipe Notes (Display)", compute="_compute_tipe_notes_display", store=True)

    uraian_notes = fields.Text(string='Uraian Notes', tracking=True)
    # total_dana = fields.Float(string='Total Dana Sinking Fund', compute='_compute_total_jumlah', store=True)

    bank = fields.Char(string='Bank Sinking Fund', tracking=True)
    # rekening = fields.Float(string='Rekening Sinking Fund', tracking=True)
    rekening = fields.Char(string='Rekening Sinking Fund', tracking=True)
    maturity_date = fields.Date(string='Maturity Date', required=True, tracking=True)

    sinking_line_ids = fields.One2many('account.keuangan.sinking.line', 'sinking_id', string='Singking Fund Notes Lines')

    # Compute fields
    total_sinking_fund = fields.Float(string='Total Penerimaan / Pengeluaran Sinking Fund', compute='_compute_totals', store=True, tracking=True)
    total_deposito = fields.Float(string='Total Pembuatan/Pencairan Deposito', compute='_compute_totals', store=True, tracking=True)
    total_pendapatan = fields.Float(string='Total Pendapatan', compute='_compute_totals', store=True, tracking=True)
    total_biaya_admin = fields.Float(string='Total Pendapatan dan Biaya Administrasi Bank ', compute='_compute_totals', store=True, tracking=True)
    total_saldo = fields.Float(string='Total Saldo', compute='_compute_totals', store=True, tracking=True)

    branch_id = fields.Many2one('res.branch', string='Nama Cabang', tracking=True)

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

    @api.depends('tipe_notes')
    def _compute_tipe_notes_display(self):
        for rec in self:
            tipe_notes_dict = dict(self._fields['tipe_notes'].selection)
            rec.tipe_notes_display = tipe_notes_dict.get(rec.tipe_notes, '')

    @api.depends('sinking_line_ids')
    def _compute_totals(self):
        for record in self:
            total_sinking_fund = sum(line.nominal_penempatan for line in record.sinking_line_ids if line.type == 'sinking_fund')
            total_deposito = sum(line.nominal_penempatan for line in record.sinking_line_ids if line.type == 'deposito')
            total_pendapatan = sum(line.nominal_penempatan for line in record.sinking_line_ids if line.type == 'pendapatan')
            total_biaya_admin =  sum(line.nominal_penempatan for line in record.sinking_line_ids if line.type == 'biaya_admin')
            record.total_sinking_fund = total_sinking_fund
            record.total_deposito = total_deposito
            record.total_pendapatan = total_pendapatan
            record.total_biaya_admin = total_pendapatan - total_biaya_admin
            record.total_saldo = total_sinking_fund + total_deposito - total_biaya_admin
   
    # @api.depends('sinking_line_ids.nominal_penempatan')
    # def _compute_total_jumlah(self):
    #     for record in self:
    #         record.total_dana = sum(line.nominal_penempatan for line in record.sinking_line_ids)

    def export_to_excel(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Sinking Fund')

        # Menambahkan informasi di atas table sebagai judul
        sheet.write(0, 0, f"Singking Fund Notes: {self.name or ''}")
        sheet.write(1, 0, f"Type: {dict(self._fields['tipe_notes'].selection).get(self.tipe_notes, '') or ''}")
        sheet.write(2, 0, f"Uraian Notes: {self.uraian_notes or ''}")
        sheet.write(3, 0, f"Bank: {self.bank or ''}")
        sheet.write(4, 0, f"Rekening: {self.rekening or ''}")
        sheet.write(5, 0, f"Maturity Date: {self.maturity_date.strftime('%d/%m/%Y') if self.maturity_date else ''}")
        sheet.write(6, 0, f"Total Penerimaan/Pengeluaran Sinking Fund: {self.total_sinking_fund if self.total_sinking_fund else ''}")
        sheet.write(7, 0, f"Total Pembuatan/Pencairan Deposito: {self.total_deposito if self.total_deposito else ''}")
        sheet.write(8, 0, f"Total Biaya Admin: {self.total_biaya_admin if self.total_biaya_admin else ''}")
        sheet.write(9, 0, f"Total Saldo: {self.total_saldo if self.total_saldo else ''}")

        
        # Menambahkan header untuk data tabel
        headers = ['Tanggal Transfer', 'Bulan', 'Tahun', 'Type', 'Nominal']
        for col, header in enumerate(headers):
            sheet.write(11, col, header)  # Start from row 11 after the titles

        # Menambahkan data untuk setiap baris 'sinking_line_ids'
        for row, line in enumerate(self.sinking_line_ids, start=12):
            sheet.write(row, 0, line.tanggal_transfer.strftime('%d/%m/%Y') if line.tanggal_transfer else '')
            sheet.write(row, 1, line.related_month)
            sheet.write(row, 2, line.related_year)
            sheet.write(row, 3, line.type)
            sheet.write(row, 4, line.nominal_penempatan)

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
            'res_model': 'account.keuangan.sinking',
            'res_id': self.id,
        })

        # Membuka file attachment
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }
    
    def action_open_export_sinking_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Export Sinking Fund',
            'res_model': 'sinking.fund.export.wizard',
            'view_mode': 'form',
            'target': 'new',
        }



class SinkingFundLine(models.Model):
    _name = 'account.keuangan.sinking.line'
    _description = 'Sinking Fund Note'

    sinking_id = fields.Many2one('account.keuangan.sinking', string='Sinking Fund Notes', required=True)

    tanggal_transfer = fields.Date(string='Tanggal Transfer', required=True, tracking=True)
    nominal_penempatan = fields.Float(string='Nominal Penempatan', tracking=True)

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

    related_month = fields.Selection(MONTH_SELECTION, string="Bulan")
    related_year = fields.Selection(YEAR_SELECTION, string="Tahun")
    
    type = fields.Selection([
        ('deposito', 'Pembuatan/Pencairan Deposito'),
        ('sinking_fund', 'Penerimaan/Pengeluaran Sinking Fund'),
        ('biaya_admin', 'Biaya Administrasi Bank'),
        ('pendapatan', 'Pendapatan / Bunga Bank'),
    ], string='Type', required=True, tracking=True)

    type_display = fields.Char(string='Type Display', compute='_compute_type_display', store=True)

    @api.depends('type')
    def _compute_type_display(self):
        for rec in self:
            rec.type_display = dict(self.fields_get(allfields=['type'])['type']['selection']).get(rec.type, '')