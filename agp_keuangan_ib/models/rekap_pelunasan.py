from odoo import models, fields, api, _
import babel.dates
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math


import base64
import io
import xlsxwriter


class RekapPelunasan(models.Model):
    _name = 'account.keuangan.rekap.pelunasan'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Rekap Pelunasan dan Dropping Dana'

    
    name = fields.Char(string='Judul')

    rekap_pelunasan_line_ids = fields.One2many('account.keuangan.rekap.pelunasan.line', 'rekap_pelunasan_id', string='Detail')

    total_uang_masuk = fields.Float(
        string='Total Uang Masuk', 
        compute='_compute_totals', 
        store=True
    )
    total_dropping_dana = fields.Float(
        string='Total Dropping Dana', 
        compute='_compute_totals', 
        store=True
    )
    total_pembayaran_pihak_ketiga = fields.Float(
        string='Total Pembayaran Pihak Ketiga', 
        compute='_compute_totals', 
        store=True
    )
    total_keseluruhan = fields.Float(
        string='Total', 
        compute='_compute_totals', 
        store=True
    )

    @api.depends('rekap_pelunasan_line_ids.uang_masuk', 
    'rekap_pelunasan_line_ids.dropping_dana', 
    'rekap_pelunasan_line_ids.pembayaran_pihak_ketiga', 
    'rekap_pelunasan_line_ids.total')
    def _compute_totals(self):
        for record in self:
            record.total_uang_masuk = sum(record.rekap_pelunasan_line_ids.mapped('uang_masuk'))
            record.total_dropping_dana = sum(record.rekap_pelunasan_line_ids.mapped('dropping_dana'))
            record.total_pembayaran_pihak_ketiga = sum(record.rekap_pelunasan_line_ids.mapped('pembayaran_pihak_ketiga'))
            record.total_keseluruhan = sum(record.rekap_pelunasan_line_ids.mapped('total'))


    def copy(self, default=None):
        # Menyimpan data default untuk duplikasi
        default = dict(default or {})
        default['name'] = f"{self.name} (Copy)"  # Mengubah nama record hasil duplikasi jika perlu
        
        # Mendapatkan baris (lines) yang terkait dengan anggaran_harian_line_ids
        rekap_pelunasan_lines = self.rekap_pelunasan_line_ids
        new_record = super().copy(default)  # Cukup gunakan super() untuk memanggil copy dari kelas induk

        # Duplicating related lines
        for line in rekap_pelunasan_lines:
            line.copy(default={'rekap_pelunasan_id': new_record.id})

        return new_record   

    
    def export_to_excel(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Rekap Uang Masuk')

        
        sheet.write(1, 0, "")
        sheet.write(1, 1, f"{self.name or ''}")

        sheet.write(3, 0, "Total Uang Masuk")
        sheet.write(3, 1, f"{self.total_uang_masuk:,.0f}" if self.total_uang_masuk else "")

        sheet.write(4, 0, "Total Dropping Dana")
        sheet.write(4, 1, f"{self.total_dropping_dana:,.0f}" if self.total_dropping_dana else "")

        sheet.write(5, 0, "Total Pembayaran Pihak Ke 3")
        sheet.write(5, 1, f"{self.total_pembayaran_pihak_ketiga:,.0f}" if self.total_pembayaran_pihak_ketiga else "")
        
        sheet.write(6, 0, "Total")
        sheet.write(6, 1, f"{self.total_keseluruhan:,.0f}" if self.total_keseluruhan else "")

        
        # Menambahkan header untuk data tabel
        headers = ['No', 'Nama Branch', 'Uang Masuk', 'Dropping Dana Dari Pusat',
        'Pembayaran Pihak Ke 3', 'Total', 'Keterangan']
        for col, header in enumerate(headers):
            sheet.write(8, col, header)  # Start from row 11 after the titles


        # Menambahkan data untuk setiap baris 'rekap_pelunasan_line_ids'
        for row, line in enumerate(self.rekap_pelunasan_line_ids, start=9):

            # Menulis data ke sheet
            sheet.write(row, 0, line.no)            
            sheet.write(row, 1, line.branch_id.name)            
            sheet.write(row, 2, f"{line.uang_masuk:,.0f}")
            sheet.write(row, 3, f"{line.dropping_dana:,.0f}")
            sheet.write(row, 4, f"{line.pembayaran_pihak_ketiga:,.0f}")
            sheet.write(row, 5, f"{line.total:,.0f}")
            sheet.write(row, 6, line.keterangan or "")
        
            row += 1

        # Selesaikan dan simpan file
        workbook.close()
        output.seek(0)
        file_data = output.read()
        output.close()

        # Buat attachment dari file
        attachment = self.env['ir.attachment'].create({
            'name': f'{self.name}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(file_data),
            'store_fname': f'{self.name}.xlsx',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': 'account.keuangan.rekap.pelunasan',
            'res_id': self.id,
        })

        # Membuka file attachment
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }



class RekapPelunasanLine(models.Model):
    _name = 'account.keuangan.rekap.pelunasan.line'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Rekap Pelunasan dan Dropping Dana Line'

    
    rekap_pelunasan_id = fields.Many2one(
        'account.keuangan.rekap.pelunasan'
    )

    no = fields.Integer(string="No", compute="_compute_no")

    branch_id = fields.Many2one(
        'res.branch',  
        string='Branch',
        required=False, 
        ondelete='restrict', 
        help="Cabang terkait untuk rekap pelunasan ini.")
   
    uang_masuk = fields.Float(string='Uang Masuk', tracking=True)
    dropping_dana = fields.Float(string='Dropping Dana Dari Pusat', tracking=True)
    pembayaran_pihak_ketiga = fields.Float(string='Pembayaran Pihak Ke 3', tracking=True)
    total = fields.Float(string='Total', compute='_compute_total', store=True, tracking=True)
    keterangan = fields.Text(string='Keterangan', tracking=True)
    

    def _compute_no(self):
        for index, record in enumerate(self, start=1):
            record.no = index

    @api.depends('uang_masuk', 'dropping_dana', 'pembayaran_pihak_ketiga')
    def _compute_total(self):
        for record in self:
            record.total = (
                record.uang_masuk
                - record.dropping_dana
                - record.pembayaran_pihak_ketiga
            )


