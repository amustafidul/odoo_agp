from odoo import models, fields, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math


import base64
import io
import xlsxwriter

class ShareholderLoan(models.Model):
    _name = 'account.keuangan.shl'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Shareholder Loan'

    name = fields.Char(string='Shareholder Loan Number', required=True, tracking=True)
    
    tujuan = fields.Char(string='Tujuan Peminjaman', tracking=True)
    # no_perjanjian = fields.Char(string='Nomor Perjanjian', tracking=True)
    # no_addendum = fields.Char(string='Nomor Addendum', tracking=True)
    tanggal_perjanjian = fields.Date(string='Tanggal Perjanjian', tracking=True)
    # tanggal_addendum = fields.Date(string='Tanggal Addendum', tracking=True)
    # periode_mulai = fields.Date(string='Periode Mulai Garansi', required=True)
    # periode_akhir = fields.Date(string='Periode Akhir Garansi', required=True)

    nominal_perjanjian = fields.Float(string='Nominal Sesuai Perjanjian', tracking=True)
    nominal_dipinjamkan = fields.Float(string='Nominal Yang Dipinjamkan', compute='_compute_nominal_yang_dipinjamkan', store=True, tracking=True)
    nominal_pengembalian = fields.Float(string='Nominal Pengembalian', compute='_compute_nominal_pengembalian', store=True, tracking=True)
    nominal_belum_dipinjamkan = fields.Float(string='Nominal yang Belum Dipinjamkan', compute='_compute_nominal_belum_dipinjamkan', store=True)
    nominal_kekurangan_pembayaran_shl = fields.Float(string='Nominal Kekurangan Pembayaran Angsuran SHL', compute='_compute_nominal_kekurangan_pembayaran_shl', store=True)


    shl_line_ids = fields.One2many('account.keuangan.shl.line', 'shl_id', string='Shareholder Loan Lines')

    nomor_perjanjian_id = fields.Many2one('account.keuangan.surat.perjanjian', string='Nomor Surat Perjanjian', store=True)

    nomor_addendum = fields.Many2many(
        'account.keuangan.surat.perjanjian.line',  # Terkait dengan account.keuangan.surat.perjanjian.line
        string='No. Addendum',
        domain="[('nomor_perjanjian_id', '=', nomor_perjanjian_id)]",  # Memfilter berdasarkan nomor_perjanjian_id
        store=True
    )

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

    @api.depends('nominal_dipinjamkan', 'nominal_pengembalian')
    def _compute_nominal_kekurangan_pembayaran_shl(self):
        for record in self:
            record.nominal_kekurangan_pembayaran_shl = record.nominal_dipinjamkan - record.nominal_pengembalian

    @api.depends('nominal_perjanjian', 'nominal_dipinjamkan')
    def _compute_nominal_belum_dipinjamkan(self):
        for record in self:
            record.nominal_belum_dipinjamkan = record.nominal_perjanjian - record.nominal_dipinjamkan
    
    @api.depends('shl_line_ids.nominal', 'shl_line_ids.tipe_shl')
    def _compute_nominal_yang_dipinjamkan(self):
        for record in self:
            # Menghitung total nominal untuk tipe 'pinjaman'
            record.nominal_dipinjamkan = sum(
                line.nominal_transaksi 
                for line in record.shl_line_ids 
                if line.tipe_shl == 'pinjaman'
            )

    @api.depends('shl_line_ids.nominal', 'shl_line_ids.tipe_shl')
    def _compute_nominal_pengembalian(self):
        for record in self:
            # Menghitung total nominal untuk tipe 'pengembalian'
            record.nominal_pengembalian = sum(
                line.nominal_transaksi 
                for line in record.shl_line_ids 
                if line.tipe_shl == 'pengembalian'
        )


    def export_to_excel(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Shareholder Loan')

        # Menambahkan informasi di atas table sebagai judul
        sheet.write(0, 0, f"Tujuan: {self.tujuan or ''}")
        # sheet.write(1, 0, f"Pengajuan Oleh: {self.pengajuan_oleh or ''}")
        # sheet.write(2, 0, f"Tanggal Pengajuan: {self.tanggal_pengajuan.strftime('%d/%m/%Y') if self.tanggal_pengajuan else ''}")
        sheet.write(1, 0, f"Nominal Perjanjian: {self.nominal_perjanjian if self.nominal_perjanjian else ''}")
        sheet.write(2, 0, f"Nominal Dipinjamkan: {self.nominal_dipinjamkan if self.nominal_dipinjamkan else ''}")
        sheet.write(3, 0, f"Nominal Pengembalian: {self.nominal_pengembalian if self.nominal_pengembalian else ''}")
        sheet.write(5, 0, f"Nominal Belum Dipinjamkan: {self.nominal_belum_dipinjamkan if self.nominal_belum_dipinjamkan else ''}")
        sheet.write(5, 0, f"Nominal Kekurangan Pembayaran SHL: {self.nominal_kekurangan_pembayaran_shl if self.nominal_kekurangan_pembayaran_shl else ''}")

        
        # Menambahkan header untuk data tabel
        headers = ['No.Invoice', 'No.SPP', 'Pengajuan Oleh', 'Tanggal Pengajuan', 'Tipe SHL', 'Tanggal', 'Bank / Sumber Dana', 'Nominal Transaksi', 'Keterangan']
        for col, header in enumerate(headers):
            sheet.write(9, col, header)  # Start from row 11 after the titles

        # Menambahkan data untuk setiap baris 'sinking_line_ids'
        for row, line in enumerate(self.shl_line_ids, start=10):
            sheet.write(row, 0, line.no_invoice)
            sheet.write(row, 1, line.no_spp)
            sheet.write(row, 2, line.pengajuan_oleh)
            sheet.write(row, 3, line.tanggal_pengajuan.strftime('%d/%m/%Y') if line.tanggal_pengajuan else '')
            sheet.write(row, 4, line.tipe_shl)
            sheet.write(row, 5, line.tanggal_transaksi.strftime('%d/%m/%Y') if line.tanggal_transaksi else '')
            sheet.write(row, 6, line.bank_account_id.acc_number if line.bank_account_id else '')
            sheet.write(row, 7, line.nominal_transaksi)
            sheet.write(row, 8, line.keterangan)

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
            'res_model': 'account.keuangan.shl',
            'res_id': self.id,
        })

        # Membuka file attachment
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }
    

    def action_open_export_shl_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Export Shl',
            'res_model': 'shl.export.wizard',
            'view_mode': 'form',
            'target': 'new',
        }



class ShlLine(models.Model):
    _name = 'account.keuangan.shl.line'
    _description = 'Shareholder Loan Lines'

    shl_id = fields.Many2one('account.keuangan.shl', string='Shareholder', required=True, tracking=True)

    tipe_shl = fields.Selection([
        ('pinjaman', 'Pinjaman'),
        ('pengembalian', 'Pengembalian'),
        # Tambahkan status lain jika perlu
    ], tracking=True)

    tipe_shl_display = fields.Char(string="Tipe SHL (Display)", compute="_compute_tipe_shl_display", store=True)

    no_invoice = fields.Char(string='Nomor Invoice', tracking=True)
    no_spp = fields.Char(string='Nomor SPP', tracking=True)
    pengajuan_oleh = fields.Char(string='Pengajuan Oleh', tracking=True)
    tanggal_pengajuan = fields.Date(string='Tanggal Pengajuan', tracking=True)

    nominal_transaksi = fields.Float(string='Nominal Transaksi', tracking=True)
    tanggal_transaksi = fields.Date(string='Tanggal Transaksi', required=True, tracking=True)
    bank_account_id = fields.Many2one('res.partner.bank', string='Bank / Sumber Dana', tracking=True)
    nominal = fields.Float(string='Nominal', tracking=True)
    keterangan = fields.Text(string='Keterangan', tracking=True)


    @api.depends('tipe_shl')
    def _compute_tipe_shl_display(self):
        for rec in self:
            shl_dict = dict(self._fields['tipe_shl'].selection)
            rec.tipe_shl_display = shl_dict.get(rec.tipe_shl, '')
