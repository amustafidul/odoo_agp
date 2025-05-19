from odoo import models, fields, api
from odoo.exceptions import UserError
import re


class HrDinasBiayaHeader(models.Model):
    _name = 'hr.dinas.biaya.header'
    _description = 'Master Daftar Biaya Perjalanan Dinas'

    name = fields.Char(string='Nama Daftar Komponen Biaya', required=True)
    keterangan = fields.Text(string='Keterangan')
    biaya_line_ids = fields.One2many('hr.dinas.biaya.line', 'header_id', string='Detail Komponen Biaya')


class HrDinasBiayaLine(models.Model):
    _name = 'hr.dinas.biaya.line'
    _description = 'Detail Komponen Biaya Perjalanan Dinas'

    header_id = fields.Many2one('hr.dinas.biaya.header', string='Referensi Header', ondelete='cascade')
    komponen_id = fields.Many2one('dinas.komponen', string='Komponen', required=True)
    jenis_lokasi = fields.Selection([
        ('ibu_kota', 'Ibu Kota Provinsi'),
        ('non_ibu_kota', 'Non Ibu Kota Provinsi'),
    ], string='Jenis Lokasi', required=True)
    golongan = fields.Selection([
        ('direksi', 'Dewan Komisaris / Direksi'),
        ('ks', 'KS/KDIV/VP/Setingkat/GM'),
        ('manager_bidang', 'Manager Bidang'),
        ('manager_sub', 'Manager Sub Bidang / Manager Unit'),
        ('staf', 'Staf'),
    ], string='Golongan Pegawai', required=True)
    jumlah = fields.Monetary(string='Jumlah (Rp)', required=True)
    satuan = fields.Char(string='Satuan', help='Contoh: Rp / Hari, Rp / Perjalanan')
    currency_id = fields.Many2one('res.currency', string='Mata Uang', default=lambda self: self.env.company.currency_id.id)

    @api.constrains('satuan')
    def _check_valid_satuan(self):
        allowed_keywords = ['hari', 'minggu', 'bulan', 'tahun', 'perjalanan']
        for rec in self:
            if rec.satuan:
                satuan_bersih = re.sub(r'[^a-zA-Z0-9\s]', '', rec.satuan).lower()
                if not any(kw in satuan_bersih for kw in allowed_keywords):
                    raise UserError(_(
                        "Satuan '%s' pada komponen '%s' tidak dikenali.\n"
                        "Gunakan satuan seperti: 'Rp / Hari', 'Rp / 7 Hari', 'Rp / Bulan', dst."
                    ) % (rec.satuan, rec.komponen_id.name or 'Tanpa Nama'))