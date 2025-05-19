from odoo import api, models, fields, _
from odoo.exceptions import UserError
from datetime import datetime
from num2words import num2words

import babel


class PermintaanPembayaran(models.Model):
    _name = 'report.report_multi_branch.spp'
    _description = 'Surat Permintaan Pembayaran'

    name = fields.Char(string='SPP Number', required=True, copy=False, readonly=False, default=lambda self: _('New'))
    unit_kerja = fields.Char(string='Unit Kerja')
    # dibayarkan_kepada = fields.Char(string='Dibayarkan Kepada')
    partner_id = fields.Many2one('res.partner', string="Dibayarkan Kepada")
    alamat = fields.Char(string='Alamat', compute='_compute_alamat', store=True)
    rek_bank = fields.Char(string='Rekening Bank')
    tanggal_spp = fields.Date(
        string='Tanggal',
        required=True,
        tracking=True,
        default=fields.Date.context_today
    ) 

    branch_ids = fields.Many2one('res.branch', string='Branch', tracking=True)
    sub_branch_ids = fields.Many2one('sub.branch', string='Sub Branches', tracking=True)
      
    surat_permohonan = fields.Selection([
        ('ada', 'Ada'),
        ('tidak_ada', 'Tidak Ada')
    ], string='Surat Permohonan Pembayaran')
    
    invoice = fields.Selection([
        ('ada', 'Ada'),
        ('tidak_ada', 'Tidak Ada')
    ], string='Invoice')
    
    kwitansi = fields.Selection([
        ('ada', 'Ada'),
        ('tidak_ada', 'Tidak Ada')
    ], string='Kwitansi')
    
    faktur_pajak = fields.Selection([
        ('ada', 'Ada'),
        ('tidak_ada', 'Tidak Ada')
    ], string='Faktur Pajak')
    
    pph = fields.Selection([
        ('ada', 'Ada'),
        ('tidak_ada', 'Tidak Ada')
    ], string='Bukti Pemotongan Pajak')
    
    perjanjian_pekerjaan = fields.Selection([
        ('ada', 'Ada'),
        ('tidak_ada', 'Tidak Ada')
    ], string='Perjanjian Pekerjaan')
    
    surat_perintah_kerja = fields.Selection([
        ('ada', 'Ada'),
        ('tidak_ada', 'Tidak Ada')
    ], string='Surat Perintah Kerja')
    
    berita_acara = fields.Selection([
        ('ada', 'Ada'),
        ('tidak_ada', 'Tidak Ada')
    ], string='Berita Acara Serah Terima Pekerjaan')
    
    berita_acara2 = fields.Selection([
        ('ada', 'Ada'),
        ('tidak_ada', 'Tidak Ada')
    ], string='Berita Acara Penyelesaian Pekerjaan')
    
    tipe_berita_acara = fields.Selection([
        ('serah_terima', 'Berita Acara Serah Terima Pekerjaan'),
        ('penyelesaian', 'Berita Acara Penyelesaian Pekerjaan')
    ], string='Tipe Berita Acara')
    
    lainnya = fields.Selection([
        ('ada', 'Ada'),
        ('tidak_ada', 'Tidak Ada')
    ], string='Lainnya')

    lainnya1 = fields.Char(string='Keterangan', optional=True)

    # lainnya1 = fields.Boolean(string='Pekerjaan Lain', default=False)\
    disetujui1 = fields.Many2one('hr.employee', string='Disetujui')
    disetujui = fields.Char(string='Disetujui', optional=True)
    diminta1 = fields.Many2one('hr.employee', string='Diminta')
    diminta = fields.Char(string='Diminta', optional=True)
    disiapkan1 = fields.Many2one('hr.employee', string='Disiapkan')
    disiapkan = fields.Char(string='Disiapkan', optional=True)

    verifikasi_keuangan = fields.Char(string='Verifikasi Akuntansi', optional=True)
    verifikasi_keuangan1 = fields.Many2one('hr.employee', string='Verifikasi Akuntansi', optional=True)
    verifikasi_pajak = fields.Char(string='Verifikasi Pajak', optional=True)
    verifikasi_pajak1 = fields.Many2one('hr.employee', string='Verifikasi Pajak', optional=True)
    manager_keuangan = fields.Char(string='Manager Bidang pada Divisi Akuntansi', optional=True)
    manager_keuangan3 = fields.Many2one('hr.employee', string='Manager Bidang pada Divisi Akuntansi', optional=True)
    manager_keuangan1 = fields.Many2one('hr.employee', string='Manager Bidang Keuangan ', optional=True)
    manager_keuangan2 = fields.Char(string='Manager Bidang Keuangan ', optional=True)
    manager_anggaran = fields.Char(string='Manager Bidang Anggaran & Asuransi ', optional=True)
    manager_anggaran1 = fields.Many2one('hr.employee', string='Manager Bidang Anggaran & Asuransi ', optional=True)
    kepala_div_keuangan = fields.Char(string='Kepala Divisi Keuangan', optional=True)
    kepala_div_keuangan1 = fields.Many2one('hr.employee', string='Kepala Divisi Keuangan', optional=True)
    kepala_div_akuntansi = fields.Char(string='Kepala Divisi Akuntansi', optional=True)
    kepala_div_akuntansi1 = fields.Many2one('hr.employee', string='Kepala Divisi Akuntansi', optional=True)
    
    wewenang1 = fields.Char(string='Wewenang I', optional=True)
    wewenang2 = fields.Char(string='Wewenang II', optional=True)
    jabatan_wewenang1 = fields.Char(string='Jabatan Wewenang I', optional=True)
    jabatan_wewenang2 = fields.Char(string='Jabatan Wewenang II', optional=True)

    created_by = fields.Many2one('res.users', string='Created By', readonly=True, default=lambda self: self.env.user)
    create_date = fields.Datetime(string='Created Date', readonly=True, default=fields.Datetime.now)
    
    line_ids = fields.One2many('report.report_multi_branch.spp.line', 'spp_id', string='Rincian Permintaan Pembayaran')
    total_jumlah = fields.Float(string='Total', compute='_compute_total_jumlah', store=True)
    total_jumlah_text = fields.Char(string='Total Text', compute='_compute_total_jumlah_text', store=True)
    branch_id = fields.Many2one('res.branch', string='Dari', required=True, default=lambda self: self.env.user.branch_id.id, readonly=True)
    # tipe = fields.Selection([
    #     ('keu', 'Keuangan'),
    #     ('non-keu', 'Non-Keuangan')
    # ], string='Tipe', store=True, default='keu')
    # state = fields.Selection([
    #     ('draft', 'Draft'),
    #     ('submitted', 'Submitted'),
    #     ('paid', 'Paid'),
    # ], string='Status', tracking=True, default='draft')

    # def action_submit(self):
    #     if self.state != 'submitted':
    #         self.write({'state': 'submitted'})
    #     return True

    # def action_pay(self):
    #     if self.state != 'paid':
    #         self.write({'state': 'paid'})
    #     return True

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        branch_id = self.env.user.branch_id.id
        args.append(('branch_id', '=', branch_id))
        return super(PermintaanPembayaran, self).search(args, offset, limit, order, count)

    @api.depends('line_ids.jumlah')
    def _compute_total_jumlah(self):
        for record in self:
            record.total_jumlah = sum(line.jumlah for line in record.line_ids)


    @api.depends('total_jumlah')
    def _compute_total_jumlah_text(self):
        for record in self:
            if record.total_jumlah:
                jumlah_text = num2words(record.total_jumlah, lang='id', to='currency')
                
                # Hilangkan ", nol" jika tidak ada desimal
                if record.total_jumlah == int(record.total_jumlah):
                    jumlah_text = jumlah_text.replace("koma nol", "")

                record.total_jumlah_text = jumlah_text + "."
            else:
                record.total_jumlah_text = 'Rp 0.'

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):            
            # Get the date details
            date_str = vals.get('date', fields.Date.context_today(self))
            date_obj = fields.Date.from_string(date_str) if isinstance(date_str, str) else date_str
            year = date_obj.strftime('%Y')
            month = int(date_obj.strftime('%m'))
            roman_month = self._to_roman(month)
            
            # Get the default branch of the user
            user = self.env.user
            default_branch = user.branch_id[0] if user.branch_id else None
            branch_code = default_branch.code if default_branch else 'KOSONG'
            
            # Get the department code of the user
            department_code = user.department_id.kode if user.department_id else 'NO_DEPT'
            
            # Generate the custom sequence number
            sequence_code = self.env['ir.sequence'].next_by_code('report.spp') or '0000'

            # Generate the custom sequence
            vals['name'] = f'{sequence_code}/{department_code}/SPP-{branch_code}/{roman_month}/{year}'
        
        return super(PermintaanPembayaran, self).create(vals)

    @staticmethod
    def _to_roman(month):
        roman = {
            1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI',
            7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X', 11: 'XI', 12: 'XII'
        }
        return roman.get(month, '')

    def print_spp(self):
        return self.env.ref('report_multi_branch.report_spp').report_action(self)

    def action_duplicate(self):
        new_record = self.copy()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': new_record.id,
            'target': 'current',
        }

    @api.depends('partner_id')
    def _compute_alamat(self):
        """Mengisi alamat otomatis berdasarkan partner_id"""
        for record in self:
            if record.partner_id:
                record.alamat = ', '.join(filter(None, [
                    record.partner_id.street,
                    record.partner_id.street2,
                    record.partner_id.city,
                    record.partner_id.state_id.name if record.partner_id.state_id else '',
                    record.partner_id.zip,
                    record.partner_id.country_id.name if record.partner_id.country_id else ''
                ]))
            else:
                record.alamat = ''

class PermintaanPembayaranLine(models.Model):
    _name = 'report.report_multi_branch.spp.line'
    _description = 'Surat Permintaan Pembayaran Line'

    rincian = fields.Char(string='Rincian Permintaan Pembayaran')
    jumlah = fields.Float(string='Jumlah', required=True)
    spp_id = fields.Many2one('report.report_multi_branch.spp', string='SPP Reference', ondelete='cascade')
