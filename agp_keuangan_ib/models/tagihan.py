from odoo import models, fields, api, _
import logging

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class Tagihan(models.Model):
    _name = 'account.keuangan.tagihan'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Tagihan'

    name = fields.Char(string='Tagihan Number', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    # Group Kiri
    ditujukan_kepada = fields.Many2one('res.partner', string='Tagihan Dari', required=True)
    alamat_perusahaan = fields.Char(string='Alamat Perusahaan', compute='_compute_alamat_perusahaan', store=True)
    nomor_referensi = fields.Char(string='No. Invoice')
    # nomor_addendum = fields.Char(string='No. Addendum')
    kata_pengantar = fields.Text(string='Kata Pengantar')
    no_rekening = fields.Char(string='Nomor Rekening')
    jenis_kegiatan_id = fields.Many2one('jenis.kegiatan', string='Jenis Kegiatan')
    jenis_kegiatan_name = fields.Char(string="Jenis Kegiatan Name", compute="_compute_jenis_kegiatan_name")

    # Group Kanan
    tanggal_invoice = fields.Date(string='Tanggal Invoice', required=True)
    nomor_surat_perjanjian = fields.Char(string='Nomor Surat Perjanjian')
    tanggal_perjanjian = fields.Date(string='Tanggal Perjanjian')
    branch_id = fields.Many2many('res.branch', string='Branch')
    sub_branch_ids = fields.Many2many('sub.branch', string='Sub Branches')
    keterangan = fields.Text(string='Keterangan')
    
    # total_jumlah = fields.Float(string='Total', compute='_compute_total_jumlah', store=True)

    # Relasi ke Invoice Lines
    tagihan_ids = fields.One2many('account.keuangan.tagihan.line', 'tagihan_id', string='Tagihan Lines')
    
    # is_scf = fields.Boolean(string='SCF', default=False)

    # ta = fields.Date(string='TA')
    # td = fields.Date(string='TD')
    # muatan = fields.Float(string='Muatan/MT', digits=(10, 3))
    # gtbg = fields.Float(string='GT BG', digits=(16, 0))
    # tu_assist_fc = fields.Float(string='Tug Assist FC', digits=(16, 0))
    # tu_assist_vc = fields.Float(string='Tug Assist VC', digits=(16, 0))
    # pilotage_fc = fields.Float(string='Pilotage FC', digits=(16, 0))
    # pilotage_vc = fields.Float(string='Pilotage VC', digits=(16, 0))
    # in_out = fields.Float(string='Pergerakan In Out', digits=(16, 0))
    # tarif = fields.Float(string='Tarif Lumpsum', digits=(16, 0))

    # tipe_tarif = fields.Selection([s
    #     ('lumpsum', 'Lumpsum'),
    #     ('mt', 'MT'),
    #     ('grt_tongkang', 'GRT Tongkang'),
    #     ('grt_vessel', 'GRT Vessel'),
    # ], default='', store=True)

    untaxed_amount = fields.Float(string="Untaxed Amount", compute="_compute_untaxed_amount", store=True)
    taxes_pph = fields.Float(string="PPh Taxes", compute="_compute_amounts", store=True)
    taxes_ppn = fields.Float(string="PPN Taxes", compute="_compute_amounts", store=True)
    total = fields.Float(string="Total Amount", compute="_compute_total", store=True)

    spp_id = fields.Many2one(
        comodel_name='report.report_multi_branch.spp',
        string='SPP',
        tracking=True
    )
    tanggal_spp = fields.Date(string='Tanggal SPP', related='spp_id.tanggal_spp', readonly=True, store=True, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], default='draft', string='State', tracking=True)
    
    nomor_perjanjian_id = fields.Many2one('account.keuangan.surat.perjanjian', string='Nomor Surat Perjanjian', domain="[('partner_id', '=', ditujukan_kepada)]", store=True)
    bank_account = fields.Char(string='Nomor Rekening')


    nomor_addendum_id = fields.Many2one(
        'account.keuangan.surat.perjanjian.line',  # Terkait dengan account.keuangan.surat.perjanjian.line
        string='No. Addendum',
        domain="[('nomor_perjanjian_id', '=', nomor_perjanjian_id)]",  # Memfilter berdasarkan nomor_perjanjian_id
        store=True
    )

    tanggal_akhir = fields.Date(string='Tanggal Akhir', related='nomor_addendum_id.tanggal_addendum_akhir', readonly=True, store=True, tracking=True)


    # tanggal_addendum = fields.Date(string='Tanggal Addendum', store=True)

    
    # @api.onchange('nomor_addendum')
    # def _onchange_nomor_addendum(self):
    #     if self.nomor_addendum:
    #         # Mengisi tanggal_addendum dengan tanggal yang terkait dengan nomor addendum yang dipilih
    #         self.tanggal_addendum = self.nomor_addendum.tanggal_addendum

    # @api.onchange('nomor_perjanjian_id')
    # def _onchange_nomor_perjanjian_id(self):
    #     if self.nomor_perjanjian_id:
    #         last_addendum = self.env['account.keuangan.surat.perjanjian.line'].search(
    #             [('nomor_perjanjian_id', '=', self.nomor_perjanjian_id.id)],
    #             order='id desc',
    #             limit=1
    #         )
    #         self.nomor_addendum_id = last_addendum if last_addendum else False

            
    @api.onchange('nomor_perjanjian_id')
    def _onchange_nomor_perjanjian_id(self):
        if self.nomor_perjanjian_id:
            # Set nilai dari related field
            self.bank_account = self.nomor_perjanjian_id.bank_account_harian_id.name
            self.branch_id = self.nomor_perjanjian_id.branch_id
            self.tanggal_perjanjian = self.nomor_perjanjian_id.tanggal_perjanjian

            # Cari addendum terakhir
            last_addendum = self.env['account.keuangan.surat.perjanjian.line'].search(
                [('nomor_perjanjian_id', '=', self.nomor_perjanjian_id.id)],
                order='id desc',
                limit=1
            )
            self.nomor_addendum_id = last_addendum if last_addendum else False
        else:
            self.bank_account = False
            self.branch_id = False
            self.tanggal_perjanjian = False
            self.nomor_addendum_id = False


    def action_confirm(self):
        for record in self: 
            record.state = 'confirmed'
        return True

    def write(self, vals):
        for record in self:
            if record.state == 'confirmed' and 'state' not in vals:
                raise UserError("Data yang sudah dikonfirmasi tidak dapat diedit.")
        return super(Tagihan, self).write(vals)

    # def write(self, vals):
    #     pass

    def action_reset_to_draft(self):
        """Reset the invoice state to draft"""
        for record in self:
            if record.state != 'draft':
                # Only allow reset to draft if the state is confirmed or posted
                record.state = 'draft'
        return True


    @api.depends('tagihan_ids.harga_per_unit', 'tagihan_ids.tax_ids', 'tagihan_ids.pajak_manual')
    def _compute_amounts(self):
        for record in self:
            untaxed_sum = sum(line.subtotal for line in record.tagihan_ids)
            ppn_sum = 0.0
            pph_sum = 0.0
            for line in record.tagihan_ids:
                for tax in line.tax_ids:
                    # Mengecek apakah tax ini adalah PPN (misalnya berdasarkan kode)
                    if tax.amount > 0:  # PPN umumnya memiliki nilai positif
                        tax_amount = tax.amount / 100  # Mengubah persentase ke desimal
                        ppn_sum += line.subtotal * tax_amount
                    if tax.amount < 0:  # PPh umumnya memiliki nilai negatif
                        tax_amount = tax.amount / 100  # Mengubah persentase ke desimal
                        pph_sum += line.subtotal * tax_amount
                # Tambahkan pajak_manual ke ppn_sum
                ppn_sum += line.pajak_manual or 0.0

            record.untaxed_amount = untaxed_sum
            record.taxes_ppn = ppn_sum
            record.taxes_pph = pph_sum


    # @api.depends('tagihan_ids.harga_per_unit')
    # def _compute_untaxed_amount(self):
    #     for record in self:
    #         record.untaxed_amount = sum(line.subtotal for line in record.tagihan_ids)

    # @api.depends('tagihan_ids.tax_ids')
    # def _compute_taxes_pph(self):
    #     for record in self:
    #         pph_sum = 0.0
    #         for line in record.tagihan_ids:
    #             for tax in line.tax_ids:
    #                 if tax.tax_group_id.name.lower() == 'pph':  # Case-insensitive check for 'Pph' or 'PPh'
    #                     tax_amount = tax.amount / 100  # Convert percentage to decimal
    #                     pph_sum += line.subtotal * tax_amount
    #         record.taxes_pph = pph_sum

    # @api.depends('tagihan_ids.tax_ids')
    # def _compute_taxes_ppn(self):
    #     for record in self:
    #         ppn_sum = 0.0
    #         for line in record.tagihan_ids:
    #             for tax in line.tax_ids:
    #                 if tax.tax_group_id.name.lower() == 'ppn':  # Case-insensitive check for 'PPN'
    #                     tax_amount = tax.amount / 100  # Convert percentage to decimal
    #                     ppn_sum += line.subtotal * tax_amount  # Assuming `line.subtotal` exists
    #         record.taxes_ppn = ppn_sum

    @api.depends('untaxed_amount', 'taxes_pph', 'taxes_ppn')
    def _compute_total(self):
        for record in self:
            record.total = record.untaxed_amount + record.taxes_pph + record.taxes_ppn


    @api.depends('tagihan_ids.total_harga')
    def _compute_total_jumlah(self):
        for record in self:
            record.total_jumlah = sum(line.total_harga for line in record.tagihan_ids)

    @api.depends('jenis_kegiatan_id')
    def _compute_jenis_kegiatan_name(self):
        for record in self:
            record.jenis_kegiatan_name = record.jenis_kegiatan_id.name if record.jenis_kegiatan_id else ''
    
    
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
            sequence_code = self.env['ir.sequence'].next_by_code('sequence.tagihan') or '0000'

            # Generate the custom sequence
            vals['name'] = f'{sequence_code}/TGHN-{branch_code}/{roman_month}/{year}'
        
        return super(Tagihan, self).create(vals)

    @staticmethod
    def _to_roman(month):
        roman = {
            1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI',
            7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X', 11: 'XI', 12: 'XII'
        }
        return roman.get(month, '')


    # @api.model
    # def create(self, vals):
    #     # Pastikan bahwa tanggal_perjanjian, nomor_addendum, dan tanggal_addendum terisi dengan benar saat create
    #     if 'nomor_perjanjian_id' in vals:
    #         nomor_perjanjian = self.env['account.keuangan.surat.perjanjian'].browse(vals['nomor_perjanjian_id'])
    #         vals['tanggal_perjanjian'] = nomor_perjanjian.tanggal_perjanjian
        
    #     return super(Tagihan, self).create(vals)

    # def write(self, vals):
    #     # Pastikan tanggal_addendum dan nomor_addendum ter-update dengan benar saat write
    #     if 'nomor_addendum' in vals:
    #         nomor_addendum = self.env['account.keuangan.surat.perjanjian.line'].browse(vals['nomor_addendum'])
    #         vals['tanggal_addendum'] = nomor_addendum.tanggal_addendum
        
    #     return super(Tagihan, self).write(vals)

class TagihanLine(models.Model):
    _name = 'account.keuangan.tagihan.line'
    _description = 'Tagihan Line'

    tagihan_id = fields.Many2one('account.keuangan.tagihan', string='Tagihan', required=True)
    name = fields.Char(string='Nama Pekerjaan / Nama Kapal', required=True, tracking=True)
    nama_shipper = fields.Char(string='Nama Shipper', tracking=True)
    deskripsi_tagihan = fields.Text(string='Deskripsi Tagihan', tracking=True)
    harga_per_unit = fields.Float(string='Harga per Unit', required=True, tracking=True)
    qty = fields.Float(
        string='Quantity',
        required=True,
        tracking=True,
        digits=(16, 3)  # Total digits: 16, Decimal places: 3
    )
    
    tax_ids = fields.Many2many(
        'account.tax',
        string='Pajak',
        # domain=[('type_tax_use', '=', 'sale'), ('amount', '>', 0)]
        domain=[('type_tax_use', '!=', 'none')]
    )

    pajak_manual = fields.Float(string="Pajak Manual", store=True)
    subtotal = fields.Float(string="Subtotal", compute="_compute_subtotal", store=True)
    show_pajak_manual = fields.Boolean(string='Show Pajak Manual', compute='_compute_show_pajak_manual')

    @api.depends('harga_per_unit', 'qty')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.harga_per_unit * line.qty

    @api.onchange('tax_ids')
    def _compute_show_pajak_manual(self):
        for line in self:
            line.show_pajak_manual = any(tax.name == 'PPn Hitung Manual' for tax in line.tax_ids)