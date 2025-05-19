from odoo import models, fields, api, _

class AntrianPembayaran(models.Model):
    _name = 'account.keuangan.antrian.pembayaran'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Antrian Pembayaran'

    name = fields.Char(string='Antrian Pembayaran Number')

    spp_id = fields.Many2one(
        'report.report_multi_branch.spp',
        string='SPP',
        required=True)

    kkhc_line_id = fields.Many2one(
        'account.keuangan.kkhc.line',
        string='KKHC',
        domain=[('approval_status', '=', 'approved')]
    )
    antrian_pembayaran_line_ids = fields.One2many('account.keuangan.antrian.pembayaran.line', 'antrian_pembayaran_id', string='Antrian Pembayaran Lines')

    combined_lines = fields.Text(string='Nomor KKHC / SPP', compute='_compute_combined_lines', tracking=True)

    # kode_anggaran_id = fields.Many2one(
    #     'account.keuangan.kode.anggaran',
    #     string='Kode Anggaran',
    #     required=True,
    # )

    deskripsi = fields.Text(string='Deskripsi Pembayaran', tracking=True)

    sifat_pembayaran = fields.Selection([
        ('prioritas', 'Prioritas'),
        ('non_prioritas', 'Non-Prioritas'),
        # Tambahkan status lain jika perlu
    ], tracking=True)

    jumlah_pembayaran = fields.Float(string='Jumlah Pembayaran', required=True, tracking=True)
    bank_pembayaran = fields.Char(string='Bank Pembayaran', required=True, tracking=True)
    rekening_pembayaran = fields.Char(string='Rekening Pembayaran', required=True, tracking=True)
    tanggal_pembayaran = fields.Date(string='Tanggal Pembayaran', required=True, tracking=True)


    @api.depends('kkhc_line_id', 'spp_id')
    def _compute_combined_lines(self):
        for record in self:
            combined_data = []
            
            # Menggabungkan data dari kkhc_line_ids
            for line in record.kkhc_line_id:
                combined_data.append(f"KKHC: {line.deskripsi}")

            # Menggabungkan data dari antrian_pembayaran_line_ids
            for line in record.spp_id:
                combined_data.append(f"Antrian Pembayaran: {line.name}")

            # Menggabungkan semua data ke dalam satu string
            record.combined_lines = "\n".join(combined_data)


class AntrianPembayaranLine(models.Model):
    _name = 'account.keuangan.antrian.pembayaran.line'
    _description = 'Antrian Pembayaran Lines'

    antrian_pembayaran_id = fields.Many2one('account.keuangan.antrian.pembayaran', string='Antrian Pembayaran', required=True, tracking=True)
