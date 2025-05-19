from odoo import models, fields, api, _
import babel.dates
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
from collections import defaultdict


import base64
import io
import xlsxwriter


class BankHarian(models.Model):
    _name = 'account.keuangan.bank.harian'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Bank Harian'

    name = fields.Char(string='Judul Saldo Bank Harian')

    saldo_awal = fields.Float(string='Saldo Awal', store=True, tracking=True)
    saldo_akhir = fields.Float(string='Saldo Akhir', compute ='_compute_saldo_akhir', store=True, tracking=True)
    jumlah = fields.Float(string='Jumlah Penggunaan', compute='_compute_saldo', store=True, tracking=True)
    summary = fields.Float(string='Jumlah Penggunaan', compute='_compute_summary', store=True, tracking=True)
    jumlah_keseluruhan = fields.Float(string='Jumlah Keseluruhan', compute='_compute_keseluruhan', store=True, tracking=True)

    bank_harian_line_ids = fields.One2many('account.keuangan.bank.harian.line', 'bank_harian_id', string='Bank Harian Lines')
   
    bank_harian_summary_ids = fields.One2many(
        'account.keuangan.bank.harian.line.summary',
        'bank_harian_id',
        string='Summary Lines',
        )
    
    # Method untuk generate summary
    def action_generate_summary(self):
        for rec in self:
            # Hapus hanya baris yang dihasilkan oleh sistem sebelumnya
            rec.bank_harian_summary_ids.filtered(lambda r: r.is_generated).unlink()

            # Hitung ringkasan
            summary_map = defaultdict(lambda: {'saldo': 0.0, 'keterangan': []})

            for line in rec.bank_harian_line_ids:
                key = line.bank_harian_master_id
                summary_map[key]['saldo'] += line.saldo
                if line.keterangan:
                    summary_map[key]['keterangan'].append(line.keterangan)

            # Buat data summary baru
            for master, data in summary_map.items():
                self.env['account.keuangan.bank.harian.line.summary'].create({
                    'bank_harian_id': rec.id,
                    'bank_harian_master_id': master.id,
                    'saldo': data['saldo'],
                    'keterangan': ', '.join(data['keterangan']) if data['keterangan'] else '',
                    'is_generated': True,
                })


    @api.depends('saldo_awal', 'jumlah')
    def _compute_saldo_akhir(self):
        for record in self:
            record.saldo_akhir = record.saldo_awal - record.jumlah

    @api.depends('bank_harian_line_ids.saldo')
    def _compute_saldo(self):
        for record in self:
            record.jumlah = sum(line.saldo for line in record.bank_harian_line_ids)

    @api.depends('bank_harian_summary_ids.saldo')
    def _compute_summary(self):
        for record in self:
            record.summary = sum(line.saldo for line in record.bank_harian_summary_ids)

    @api.depends('summary', 'jumlah')
    def _compute_keseluruhan(self):
        for record in self:
            record.jumlah_keseluruhan = record.summary + record.jumlah

    def copy(self, default=None):
        # Menyimpan data default untuk duplikasi
        default = dict(default or {})
        default['name'] = f"{self.name} (Copy)"  # Mengubah nama record hasil duplikasi jika perlu
        
        # Mendapatkan baris (lines) yang terkait dengan anggaran_harian_line_ids
        bank_harian_lines = self.bank_harian_line_ids
        new_record = super().copy(default)  # Cukup gunakan super() untuk memanggil copy dari kelas induk

        # Duplicating related lines
        for line in bank_harian_lines:
            line.copy(default={'bank_harian_id': new_record.id})

        return new_record

    
    def export_to_excel(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Saldo Bank Harian')

        
        # Menulis "Tanggal Anggaran" di kolom 0, dan tanggal anggaran di kolom 1
        sheet.write(1, 0, "")
        sheet.write(1, 1, f"{self.name or ''}")

        # Menulis "Saldo Awal" di kolom 0, dan saldo awal di kolom 1
        sheet.write(3, 0, "Saldo Awal")
        sheet.write(3, 1, f"Rp {self.saldo_awal:,.2f}" if self.saldo_awal else "")

        # Menulis "Jumlah Penggunaan" di kolom 0, dan jumlah penggunaan di kolom 1
        sheet.write(4, 0, "Jumlah Penggunaan")
        sheet.write(4, 1, f"Rp {self.jumlah:,.2f}" if self.saldo_awal else "")

        # Menulis "Saldo Akhir" di kolom 0, dan saldo akhir di kolom 1
        sheet.write(5, 0, "Saldo Akhir")
        sheet.write(5, 1, f"Rp {self.saldo_akhir:,.2f}" if self.saldo_akhir else "")

        
        # Menambahkan header untuk data tabel
        headers = ['No', 'Bank', 'Saldo', 'Keterangan']
        for col, header in enumerate(headers):
            sheet.write(7, col, header)  # Start from row 11 after the titles


        # Menambahkan data untuk setiap baris 'bank_harian_summary_ids'
        for row, line in enumerate(self.bank_harian_summary_ids, start=8):

            # Menulis data ke sheet
            sheet.write(row, 0, line.no)            
            sheet.write(row, 1, line.bank_harian_master_id.name)            
            sheet.write(row, 2, line.saldo)
            sheet.write(row, 3, line.keterangan or '')
            sheet.write(row, 4, line.dana_ditahan and 'Ya' or '')  # atau gunakan 'Tidak' jika ingin eksplisit
                    
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
            'res_model': 'account.keuangan.bank.harian',
            'res_id': self.id,
        })

        # Membuka file attachment
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }



class BankHarianLine(models.Model):
    _name = 'account.keuangan.bank.harian.line'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Bank Harian Line'

    no = fields.Integer(string="No", compute="_compute_no")

    bank_harian_id = fields.Many2one(
        'account.keuangan.bank.harian',
        required=True)

    bank_harian_master_id = fields.Many2one(
        'account.keuangan.bank.harian.master',
        string='Bank Harian Master',
        required=True)
    
    saldo = fields.Float(string='Saldo', tracking=True)
    keterangan = fields.Text(string='Keterangan', default='', tracking=True)
    def _compute_no(self):
        for index, record in enumerate(self, start=1):
            record.no = index
    

class BankHarianLineSummary(models.Model):
    _name = 'account.keuangan.bank.harian.line.summary'
    _description = 'Bank Harian Line Summary'

    bank_harian_id = fields.Many2one(
        'account.keuangan.bank.harian',
        required=True)

    bank_harian_master_id = fields.Many2one(
        'account.keuangan.bank.harian.master',
        string='Nama Bank',
        required=True)
    no = fields.Integer(string="No", compute="_compute_no")

    dana_ditahan = fields.Boolean(
            string='Dana Ditahan',
            default=False
        )

    keterangan = fields.Text(string='Keterangan')
    saldo = fields.Float(string='Saldo')
    is_generated = fields.Boolean(string='Generated by System', default=False)

    def _compute_no(self):
        for index, record in enumerate(self, start=1):
            record.no = index