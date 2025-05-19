from odoo import models, fields, api, _

class KkhcReject(models.Model):
    _name = 'account.keuangan.kkhc.reject'
    _description = 'KKHC with Rejected Lines (for Cabang)'

    name = fields.Char(string='No.')
    nama_anggaran = fields.Char(string='Nama Anggaran')
    branch_id = fields.Many2one('res.branch', string='Nama Cabang')
    rkap_id = fields.Many2one('account.keuangan.rkap', string='No. RKAP')
    periode_kkhc_start = fields.Date(string='Dari')
    periode_kkhc_end = fields.Date(string='Sampai')
    tanggal_pengajuan = fields.Date(string='Tanggal Pengajuan')
    tanggal_disetujui = fields.Date(string='Tanggal Disetujui')
    kkhc_reject_ids = fields.One2many('account.keuangan.kkhc.reject.line', 'kkhc_reject_id', string='KKHC Lines Rejected')

    @api.model
    def cron_update_rejected_kkhc(self):
        Monitoring = self.env['account.keuangan.monitor.kkhc.line'].sudo()
        KKHC = self.env['account.keuangan.kkhc'].sudo()
        RejectLine = self.env['account.keuangan.kkhc.reject.line'].sudo()

        rejected_lines = Monitoring.search([('is_rejected', '=', True)])
        grouped = {}

        for line in rejected_lines:
            kkhc_id = line.kkhc_id.id
            grouped.setdefault(kkhc_id, []).append(line)

        for kkhc_id, lines in grouped.items():
            kkhc = KKHC.browse(kkhc_id)
            if not kkhc.exists():
                continue

            reject_rec = self.create({
                'name': kkhc.name,
                'nama_anggaran': kkhc.nama_anggaran,
                'branch_id': kkhc.branch_id.id,
                'rkap_id': kkhc.rkap_id.id,
                'periode_kkhc_start': kkhc.periode_kkhc_start,
                'periode_kkhc_end': kkhc.periode_kkhc_end,
                'tanggal_pengajuan': kkhc.tanggal_pengajuan,
                'tanggal_disetujui': kkhc.tanggal_disetujui,
            })

            for line in lines:
                RejectLine.create({
                    'kkhc_reject_id': reject_rec.id,
                    'kode_anggaran_id': line.kode_anggaran_id.id,
                    'deskripsi': line.deskripsi,
                    'account_code_id': line.account_code_id.id,
                    'uraian_pemakaian': line.uraian,
                    'nominal_pengajuan': line.nominal_pengajuan,
                    'nominal_disetujui_divisi': line.nominal_final,
                })

        self.env.cr.commit()
    
class KkhcRejectLine(models.Model):
    _name = 'account.keuangan.kkhc.reject.line'
    _description = 'Lines of KKHC with Rejected Lines (for Cabang)'

    kkhc_reject_id = fields.Many2one('account.keuangan.kkhc.reject', string='No. KKHC Reject')
    kode_anggaran_id = fields.Many2one('account.keuangan.kode.anggaran', string='Kode Anggaran')
    deskripsi = fields.Char(string='Deskripsi')
    account_code_id = fields.Many2one('account.account', string='COA')
    uraian = fields.Many2one('account.account', string='COA')
    uraian_pemakaian = fields.Text(string='Uraian')
    nominal_pengajuan = fields.Float(string='Pengajuan')
    nominal_disetujui_divisi = fields.Float(string='Disetujui Divisi')