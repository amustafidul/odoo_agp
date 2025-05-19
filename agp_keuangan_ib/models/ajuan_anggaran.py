from odoo import models, fields, api, _

class AjuanAnggaran(models.Model):
    _name = 'account.keuangan.ajuan.anggaran'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Ajuan Anggaran'

    name = fields.Char(string='Ajuan Anggaran Number', required=True, copy=True, readonly=False, tracking=True, default=lambda self: _('New'))
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        # Tambahkan status lain jika perlu
    ], default='draft', tracking=True)
    
    # Group Kiri
    nama_anggaran = fields.Char(string='Nama Anggaran', required=True, tracking=True,)
    branch_id = fields.Many2one('res.branch', string='Nama Cabang', required=True, tracking=True)
    nomor_referensi = fields.Char(string='Nomor Referensi', tracking=True)
    kata_pengantar = fields.Text(string='Kata Pengantar', tracking=True)
    limit = fields.Float(string='Limit Anggaran', required=True, tracking=True)

    # Group Kanan
    tanggal_pengajuan = fields.Date(string='Tanggal Pengajuan', required=True, tracking=True)
    jumlah_ajuan_anggaran = fields.Float(string='Jumlah Ajuan Anggaran', required=True, tracking=True)
    tanggal_disetujui = fields.Date(string='Tanggal Disetujui', tracking=True)
    jumlah_pemasukan = fields.Float(string='Jumlah Pemasukan', required=True, tracking=True)
    jumlah_pengeluaran = fields.Float(string='Jumlah Pengeluaran', required=True, tracking=True)
    keterangan = fields.Text(string='Keterangan', tracking=True)
    
    # Relasi ke Invoice Lines
    line_ids = fields.One2many('account.keuangan.ajuan.anggaran.line', 'ajuan_anggaran_id', string='Ajuan Anggaran Lines')
    

    @api.depends('ditujukan_kepada')
    def _compute_alamat_perusahaan(self):
        for record in self:
            if record.ditujukan_kepada:
                record.alamat_perusahaan = record.ditujukan_kepada.contact_address
            else:
                record.alamat_perusahaan = ''

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        if self.branch_id:
            return {'domain': {'sub_branch_ids': [('id', 'in', self.branch_id.sub_branch_ids.ids)]}}
        else:
            return {'domain': {'sub_branch_ids': []}}

    @api.model
    def action_confirm(self):
        # Logika untuk mengonfirmasi invoice
        self.state = 'confirmed'  # Pastikan untuk menambahkan field state jika belum ada
        return True

    # @api.model
    # def action_preview(self):
    #     # Logika untuk preview invoice
    #     return {
    #         'type': 'ir.actions.act_url',
    #         'url': '/your/preview/url',  # Ganti dengan URL preview yang sesuai
    #         'target': 'new',
    #     }

    @api.model
    def action_print(self):
        # Logika untuk mencetak invoice
        return self.env.ref('agp_keuangan_ib.report_invoice').report_action(self)  # Ganti dengan ID report yang sesuai

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
            sequence_code = self.env['ir.sequence'].next_by_code('sequence.keuangan.ajuan.anggaran') or '0000'

            # Generate the custom sequence
            vals['name'] = f'{sequence_code}/Ajuan Anggaran-{branch_code}/{roman_month}/{year}'
        
        return super(NotaDinas, self).create(vals)

    @staticmethod
    def _to_roman(month):
        roman = {
            1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI',
            7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X', 11: 'XI', 12: 'XII'
        }
        return roman.get(month, '')


class AjuanAnggaranLine(models.Model):
    _name = 'account.keuangan.ajuan.anggaran.line'
    _description = 'Ajuan Anggaran Line'

    ajuan_anggaran_id = fields.Many2one('account.keuangan.ajuan.anggaran', string='Ajuan Anggaran', required=True, tracking=True)
    # kode_anggaran = fields.Char(string='Kode Anggaran', required=True)
    deskripsi = fields.Text(string='Deskripsi Penggunaan Anggaran', tracking=True)
    rekening_terkait = fields.Float(string='Rekening Terkait', required=True, tracking=True)
    total_harga = fields.Float(string='Total Harga', store=True, tracking=True)

    # Field Many2one untuk kode anggaran
    kode_anggaran_id = fields.Many2one(
        'account.keuangan.kode.anggaran',
        string='Kode Anggaran',
        required=True,
    )