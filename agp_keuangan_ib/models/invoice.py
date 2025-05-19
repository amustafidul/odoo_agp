from odoo import models, fields, api, _
import logging
from datetime import date

from odoo.tools import format_date
from babel.dates import format_date

from num2words import num2words
from math import floor

from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)

# class Payment(models.Model):
#     _inherit = 'account.payment'

#     invoice_id = fields.Many2one('account.keuangan.invoice', string="Invoice")

class Invoice(models.Model):
    _name = 'account.keuangan.invoice'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Invoice'


    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    name = fields.Char(string='Nomor', required=True, copy=True, readonly=False, default=lambda self: _('New'), tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], default='draft', string='State', tracking=True)
    
    # Group Kiri
    kepada = fields.Char(string='Kepada', tracking=True)
    ditujukan_kepada = fields.Many2one('res.partner', string='Nama Perusahaan', required=True, tracking=True)
    alamat_perusahaan = fields.Char(string='Alamat Perusahaan', compute='_compute_alamat_perusahaan', store=True, tracking=True)
    nomor_referensi = fields.Char(string='Nomor Invoice', tracking=True)
    kata_pengantar = fields.Text(string='Kata Pengantar', tracking=True)
    informasi_pembayaran = fields.Char(string='Informasi Pembayaran', tracking=True)
    jenis_kegiatan_id = fields.Many2one('jenis.kegiatan', string='Jenis Kegiatan', tracking=True, required=True, domain="[('company_id', '=', company_id)]")
    jenis_kegiatan_name = fields.Char(string="Jenis Kegiatan Name", compute="_compute_jenis_kegiatan_name", tracking=True)

    # Group Kanan
    tanggal_invoice = fields.Date(string='Tanggal Invoice', required=True, tracking=True)
    nomor_surat_perjanjian = fields.Char(string='Nomor Surat Perjanjian', tracking=True)
    tanggal_perjanjian = fields.Date(string='Tanggal Perjanjian', tracking=True)
    branch_id = fields.Many2one('res.branch', string='Branch', tracking=True)
    sub_branch_ids = fields.Many2many('sub.branch', string='Sub Branches', tracking=True)
    keterangan = fields.Text(string='Keterangan', tracking=True)
    
    total_jumlah = fields.Float(string='Total', compute='_compute_total_jumlah', store=True, tracking=True, digits=(16, 0))
    total_pajak_call_fee = fields.Float(string='Pajak Call Fee', compute='_compute_total_jumlah_call_fee', store=True, tracking=True, digits=(16, 0))
    total_pajak_lain = fields.Float(string='Pajak Lain', compute='_compute_total_pajak_lain', store=True, tracking=True, digits=(16, 0))
    total_pajak = fields.Float(
        string='Total Pajak', 
        compute='_compute_total_pajak', 
        store=True, 
        tracking=True,
        digits=(16, 0)
    )

    # total_pajak_pph = fields.Float(string='Total Pajak PPh', compute='_compute_pph_amount', store=True)
    total_sebelum_pajak = fields.Float(string='Total Sebelum Pajak', compute='_compute_sebelum_pajak', store=True, tracking=True, digits=(16, 0))
    total_sesudah_pajak = fields.Float(string='Total Sesudah Pajak', compute='_compute_sesudah_pajak', store=True, tracking=True, digits=(16, 0))

    # Relasi ke Invoice Lines
    line_ids = fields.One2many('account.keuangan.invoice.line', 'invoice_id', 
                                string='Invoice Lines', tracking=True
                                # domain=[('display_type', 'in', ('line_section', 'line_note'))],
                                )
    
    is_scf = fields.Boolean(string='SCF', default=False, tracking=True)

    ta = fields.Date(string='TA', tracking=True)
    td = fields.Date(string='TD', tracking=True)
    periode_mulai = fields.Date(string='Periode Kapal Mulai', tracking=True)
    periode_akhir = fields.Date(string='Periode Kapal Akhir', tracking=True)
    # muatan = fields.Float(string='Muatan/MT', digits=(10, 3))
    # gtbg = fields.Float(string='GT BG', digits=(16, 0))
    # tu_assist_fc = fields.Float(string='Tug Assist FC', digits=(16, 0))
    # tu_assist_vc = fields.Float(string='Tug Assist VC', digits=(16, 0))
    # pilotage_fc = fields.Float(string='Pilotage FC', digits=(16, 0))
    # pilotage_vc = fields.Float(string='Pilotage VC', digits=(16, 0))
    # in_out = fields.Float(string='Pergerakan In Out', digits=(16, 0))
    # tarif = fields.Float(string='Tarif Lumpsum', digits=(16, 0))

    tipe_tarif = fields.Selection([
        ('lumpsum', 'Lumpsum'),
        ('mt', 'MT'),
        ('grt_tongkang', 'GRT Tongkang'),
        ('grt_vessel', 'GRT Vessel'),
    ], default='', store=True, tracking=True)
    
    tipe_bm = fields.Selection([
        ('darat_bl', 'Darat BL'),
        ('darat_ds', 'Darat DS'),
        ('laut', 'Laut')
    ], default='', store=True, tracking=True)


    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.company.currency_id, tracking=True)

    show_admin_bag = fields.Boolean(string='Tampilkan Admin BAG', tracking=True)
    admin_bag = fields.Float(string='Admin BAG', compute='_compute_admin_bag', store=True, tracking=True, digits=(16, 0))
    show_nilai_pekerjaan = fields.Boolean(string='Exclude Nilai Pekerjaan', tracking=True)
    show_biaya_inklaring = fields.Boolean(string='Biaya Inklaring', tracking=True)
    show_uang_muka = fields.Boolean(string='Uang Muka', tracking=True)
    show_call_fee= fields.Boolean(string='Call Fee', tracking=True)
    nilai_pekerjaan = fields.Float(string='Nilai Pekerjaan', compute='_compute_nilai_pekerjaan', store=True, tracking=True, digits=(16, 0))
    biaya_inklaring = fields.Float(string='Biaya Inklaring', store=True, tracking=True, digits=(16, 0))
    uang_muka = fields.Float(string='Uang Muka', store=True, tracking=True, digits=(16, 0))
    call_fee = fields.Float(string='Call Fee', store=True, tracking=True, digits=(16, 0))

    total_terbilang = fields.Char(string='Total Terbilang', compute='_compute_total_terbilang')
    tempat = fields.Char(string='Tempat Penandatanganan', tracking=True)
    jabatan = fields.Char(string='Jabatan', tracking=True)
    ttd = fields.Char(string='Yang Bertanda Tangan', tracking=True)
    
    bank_account_id = fields.Many2one('res.partner.bank', string="Bank Account")

    acc_holder_name = fields.Char(
        string="Bank",
        related='bank_account_id.acc_holder_name', 
        readonly=True
    )
    acc_number = fields.Char(
        string="No. Rek",
        related='bank_account_id.acc_number', 
        readonly=True
    )
    phone = fields.Char(
        string="Phone"
        # related='bank_account_id.phone',
        # readonly=True
    )
    email = fields.Char(
        string="Email"
        # related='bank_account_id.email', 
        # readonly=True
    )
    company_name = fields.Char(
        string="Nama"
    )

    current_date = fields.Date(string='Current Date', default=fields.Date.context_today, readonly=True)
    
    formatted_date = fields.Char(
        string='Formatted Date', 
        compute='_compute_formatted_date', 
        readonly=True
    )

    formatted_invoice_date = fields.Char(
        string='Formatted Invoice Date', 
        compute='_compute_formatted_invoice_date', 
        readonly=True
    )
    
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)

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
    
    # payment_status = fields.Selection([
    #     ('unpaid', 'Unpaid'),
    #     ('paid', 'Paid'),
    #     ('partial', 'Partial Payment'),
    # ], string='Payment Status', default='unpaid', tracking=True)

    total_paid = fields.Float(string='Sudah dibayar', compute='_compute_total_paid', store=True)
    
    remaining_balance = fields.Float(string='Belum dibayar', compute='_compute_remaining_balance', store=True)

    payment_ids = fields.One2many('account.keuangan.register.payment', 'invoice_id', string="Payments")

    payment_status = fields.Selection(
        [
            ('not_paid', 'Not Paid'),
            ('partial_paid', 'Partial Paid'),
            ('paid', 'Paid')
        ],
        string='Status Pembayaran',
        compute='_compute_payment_status',
        default='not_paid',
        store=True
    )

    jumlah_keagenan = fields.Float(string='Jumlah Tagihan', compute='_compute_keagenan', store=True)               

    @api.depends('total_paid', 'remaining_balance')
    def _compute_payment_status(self):
        for record in self:
            if record.total_paid == 0:
                record.payment_status = 'not_paid'
            elif record.total_paid < record.total_sesudah_pajak:
                record.payment_status = 'partial_paid'
            else:
                record.payment_status = 'paid'


    def action_register_payment(self):
        for record in self:
            if record.state != 'confirmed':
                raise UserError("Hanya invoice yang sudah dikonfirmasi yang dapat mendaftarkan pembayaran.")
            return {
                'name': 'Register Payment',
                'type': 'ir.actions.act_window',
                'res_model': 'account.keuangan.register.payment',
                'view_mode': 'form',
                'context': {
                    'default_invoice_id': record.id,
                    'default_ditujukan_kepada': record.ditujukan_kepada.id,
                },
                'target': 'new',
            }

    @api.depends('total_sesudah_pajak', 'total_paid')
    def _compute_remaining_balance(self):
        for record in self:
            record.remaining_balance = record.total_sesudah_pajak - record.total_paid


    @api.depends('payment_ids.amount_paid')
    def _compute_total_paid(self):
        for record in self:
            # Compute the total amount paid based on related payments
            total_paid = sum(payment.amount_paid for payment in record.payment_ids)
            record.total_paid = total_paid


    @api.depends('tanggal_invoice')
    def _compute_formatted_invoice_date(self):
        for record in self:
            if record.tanggal_invoice:
                record.formatted_invoice_date = format_date(
                    record.tanggal_invoice, 
                    format='d MMMM y', 
                    locale='id_ID'
                ).upper()  # Konversi ke huruf kapital
            else:
                record.formatted_invoice_date = 'N/A'

    # payment_ids = fields.One2many('account.payment', 'invoice_id', string='Payments')
    
    @api.depends('current_date')
    def _compute_formatted_date(self):
        for record in self:
            if record.current_date:
                record.formatted_date = format_date(
                    record.current_date, 
                    format='d MMMM y', 
                    locale='id_ID'
                ).upper()
            else:
                record.formatted_date = 'N/A' 

    @api.depends('total_sesudah_pajak')
    def _compute_total_terbilang(self):
        for record in self:
            # Round down to nearest whole number
            total_whole = floor(record.total_sesudah_pajak)
            # Convert to words
            total_terbilang = num2words(total_whole, lang='id').title().replace('-', ' ')
            # Add the currency name
            currency_name = "Rupiah"  # Adjust the currency name if necessary
            record.total_terbilang = f"{total_terbilang} {currency_name}"


    @api.depends('total_sebelum_pajak', 'show_admin_bag')
    def _compute_admin_bag(self):
        for record in self:
            # Hanya hitung admin_bag jika show_admin_bag dicentang
            if record.show_admin_bag:
                record.admin_bag = round((record.total_sebelum_pajak * 0.8) / 100)
            else:
                record.admin_bag = 0.0
                

    @api.depends('call_fee', 'show_call_fee')
    def _compute_total_jumlah_call_fee(self):
        for record in self:
            # Hanya hitung admin_bag jika show_admin_bag dicentang
            if record.show_call_fee:
                record.total_pajak_call_fee = round(record.call_fee * 0.11)
            else:
                record.total_pajak_call_fee = 0.0
                

    @api.depends('line_ids.tax_amount', 'show_call_fee')
    def _compute_total_pajak_lain(self):
        for record in self:
            # Hanya hitung admin_bag jika show_admin_bag dicentang
            if record.show_call_fee:
                record.total_pajak_lain = round(sum(line.tax_amount for line in record.line_ids))
            else:
                record.total_pajak_lain = 0.0


    @api.depends('total_sebelum_pajak', 'show_nilai_pekerjaan')
    def _compute_nilai_pekerjaan(self):
        # for record in self:
        #     if record.show_nilai_pekerjaan:
        #         record.nilai_pekerjaan = round((record.total_sebelum_pajak / 1.11))
        #     else:
        #         record.nilai_pekerjaan = 0.0

        for record in self:
            record.nilai_pekerjaan = round((record.total_sebelum_pajak / 1.11))
            
    
    @api.depends('line_ids.total_harga')
    def _compute_total_jumlah(self):
        for record in self:
            record.total_jumlah = round(sum(line.total_harga for line in record.line_ids))


    @api.depends('line_ids.tax_amount', 
                'total_sesudah_pajak', 
                'total_sebelum_pajak', 
                'show_nilai_pekerjaan', 
                'show_biaya_inklaring', 
                'biaya_inklaring',
                'show_call_fee',
                'call_fee',
                'total_pajak_call_fee')
    def _compute_total_pajak(self):
        for record in self:
            if record.show_nilai_pekerjaan:
                # Jika show_nilai_pekerjaan True, hitung total_pajak berdasarkan total_sebelum_pajak * 12%
                record.total_pajak = round(record.total_sebelum_pajak * 0.12)
            elif record.show_biaya_inklaring:
                # Jika show_biaya_inklaring True, hitung total_pajak berdasarkan biaya_inklaring * 11%
                record.total_pajak = round(record.biaya_inklaring * 0.11)            
            elif record.show_call_fee:
                # Jika show_biaya_inklaring True, hitung total_pajak berdasarkan biaya_inklaring * 11%
                record.total_pajak = round(sum(line.tax_amount for line in record.line_ids)) + record.total_pajak_call_fee
            else:
                # Jika keduanya False, hitung total_pajak dari jumlah tax_amount di line_ids
                record.total_pajak = round(sum(line.tax_amount for line in record.line_ids))

    # @api.depends('line_ids.tax_ids')
    # def _compute_pph_amount(self):
    #     for record in self:
    #         total_pph_amount = 0.0  # Inisialisasi total PPh
    #         for line in record.line_ids:  # Iterasi melalui setiap line
    #             for tax in line.tax_ids:  # Iterasi melalui setiap pajak di line
    #                 # Misalkan kita anggap bahwa PPh memiliki kode tertentu, misalnya "PPh"
    #                 if tax.display_name == 'PPh':  # Gantilah 'PPh' dengan kode pajak yang sesuai
    #                     total_pph_amount += line.total_sebelum_pajak * (tax.amount / 100)

    #         record.total_pajak_pph = total_pph_amount  # Simpan total PPh


    @api.depends('nilai_pekerjaan', 'show_nilai_pekerjaan', 'show_admin_bag', 'line_ids.total_sebelum_pajak', 'admin_bag')
    def _compute_sebelum_pajak(self):
        for record in self:
            if record.show_nilai_pekerjaan:
                # Jika show_nilai_pekerjaan True, gunakan rumus (11/12) * nilai_pekerjaan
                record.total_sebelum_pajak = round((11 / 12) * record.nilai_pekerjaan)
            elif record.show_admin_bag:
                # Jika show_admin_bag True, hitung sum dari total_sebelum_pajak pada line_ids - admin_bag
                total = sum(line.total_sebelum_pajak for line in record.line_ids) - record.admin_bag
                record.total_sebelum_pajak = round(total)
            else:
                # Jika tidak ada kondisi yang aktif, hitung sum dari total_sebelum_pajak pada line_ids
                total = sum(line.total_sebelum_pajak for line in record.line_ids)
                record.total_sebelum_pajak = round(total)


    @api.depends('line_ids.total_sesudah_pajak', 'show_nilai_pekerjaan', 'show_call_fee', 'call_fee',  'nilai_pekerjaan', 'uang_muka', 'total_pajak', 'total_sebelum_pajak')
    def _compute_sesudah_pajak(self):
        for record in self:
            if record.show_nilai_pekerjaan:
                record.total_sesudah_pajak = round(record.nilai_pekerjaan + record.total_pajak)
            elif record.show_biaya_inklaring:    
                record.total_sesudah_pajak = round(record.biaya_inklaring + record.total_pajak + record.total_sebelum_pajak)
            elif record.show_call_fee:    
                record.total_sesudah_pajak = round(record.call_fee - record.uang_muka + record.total_pajak + record.total_sebelum_pajak)
            else:
                total = sum(line.total_sesudah_pajak for line in record.line_ids)
                record.total_sesudah_pajak = round(total)


    @api.depends('jenis_kegiatan_id')
    def _compute_jenis_kegiatan_name(self):
        for record in self:
            record.jenis_kegiatan_name = record.jenis_kegiatan_id.name if record.jenis_kegiatan_id else ''
        
    @api.depends('total_sebelum_pajak', 'total_pajak', 'call_fee', 'uang_muka')
    def _compute_keagenan(self):
        for record in self:
            record.jumlah_keagenan = record.total_sebelum_pajak + record.call_fee
    
    @api.depends('ditujukan_kepada')
    def _compute_alamat_perusahaan(self):
        for record in self:
            if record.ditujukan_kepada:
                partner = record.ditujukan_kepada
                # Membuat alamat manual tanpa menyertakan nama
                alamat_parts = [
                    partner.street or '',
                    partner.street2 or '',
                    partner.city or '',
                    partner.state_id.name or '',
                    partner.zip or '',
                    partner.country_id.name or ''
                ]
                # Gabungkan elemen-elemen alamat dengan koma, kosongkan jika tidak ada data
                record.alamat_perusahaan = ', '.join(filter(None, alamat_parts))
            else:
                record.alamat_perusahaan = ''


    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        if self.branch_id:
            return {'domain': {'sub_branch_ids': [('id', 'in', self.branch_id.sub_branch_ids.ids)]}}
        else:
            return {'domain': {'sub_branch_ids': []}}

    
    def action_confirm(self):
        for record in self:
            record.state = 'confirmed'
        return True

    def write(self, vals):
        # okeeeee
        for record in self:
            print('LINEEE',record.line_ids)
            if record.state == 'confirmed' and 'state' not in vals:
                raise UserError("Data yang sudah dikonfirmasi tidak dapat diedit.")
            # if record.line_ids or r:
            for lin in record.line_ids:
                print('lin.display_type', lin.display_type)
        return super(Invoice, self).write(vals)

    def action_reset_to_draft(self):
        """Reset the invoice state to draft"""
        for record in self:
            if record.state != 'draft':
                # Only allow reset to draft if the state is confirmed or posted
                record.state = 'draft'
        return True

    # Method untuk Register Payment
    # def action_register_payment(self):
    #     """Register payment for the invoice"""
    #     for record in self:
    #         # Membuka wizard pembayaran (payment register wizard)
    #         payment = self.env['account.payment'].create({
    #             'payment_type': 'inbound',  # Atau 'outbound' tergantung jenis pembayaran
    #             'ditujukan_kepada': record.ditujukan_kepada.id,
    #             # 'amount': record.amount_total,  # Jumlah yang dibayar (misalnya, total invoice)
    #             # 'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,  # Menentukan metode pembayaran
    #             # 'journal_id': self.env['account.journal'].search([('type', '=', 'bank')], limit=1).id,  # Menentukan jurnal bank
    #             # 'communication': record.name,  # Bisa diisi dengan nama invoice atau referensi lain
    #         })
    #         payment.action_post()  # Mengaktifkan pembayaran

    #         # Opsional: Ubah status invoice setelah pembayaran
    #         record.write({'state': 'paid'})  # Ubah status ke 'paid' setelah pembayaran
   
   
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
            sequence_code = self.env['ir.sequence'].next_by_code('sequence.keuangan.invoice') or '0000'

            # Generate the custom sequence
            vals['name'] = f'{sequence_code}/INV-{branch_code}/{roman_month}/{year}'
        
        return super(Invoice, self).create(vals)

    @staticmethod
    def _to_roman(month):
        roman = {
            1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI',
            7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X', 11: 'XI', 12: 'XII'
        }
        return roman.get(month, '')

    def action_preview_invoice(self):
        """
        Method to trigger the preview of the invoice report.
        """
        report = self.env.ref('agp_keuangan_ib.report_invoice_pdf')
        return report.report_action(self)


    def get_display_columns(self):
        columns = []
        # Check for conditional columns
        if self._context.get('show_tarif'):
            columns.append('tarif')
        if self._context.get('show_unit'):
            columns.append('unit')
        if self._context.get('show_satuan'):
            columns.append('satuan')
        if self._context.get('show_ta'):
            columns.append('ta')
        if self._context.get('show_td'):
            columns.append('td')
        if self._context.get('show_lumpsum'):
            columns.append('lumpsum')
        if self._context.get('show_bl'):
            columns.append('bl')
        if self._context.get('show_gtbg'):
            columns.append('gtbg')
        if self._context.get('show_fc_tunda'):
            columns.append('fc_tunda')
        if self._context.get('show_vc_tunda'):
            columns.append('vc_tunda')
        if self._context.get('show_fc_pandu'):
            columns.append('fc_pandu')
        if self._context.get('show_vc_pandu'):
            columns.append('vc_pandu')
        if self._context.get('show_pergerakan_in_out'):
            columns.append('pergerakan_in_out')
        
        return columns
        
    
    def get_total_column_count(self):
        # This function returns the total number of columns including those that are conditionally displayed
        columns = self.get_display_columns()
        return len(columns) + 2  # Add 2 for the fixed columns like 'Total Sebelum Pajak'


    @api.onchange('user_id')
    def _onchange_user_id(self):
        self._compute_user_branch()
        self._compute_user_branch_phone()
        self._compute_user_branch_email()
        self._compute_user_branch_website()


    @api.depends('user_id.branch_id')
    def _compute_user_branch(self):
        for record in self:
            branch = record.user_id.branch_id
            record.user_branch_id = branch
            if branch:
                address = f"{branch.street or ''}, {branch.street2 or ''}, {branch.city or ''}, {branch.state_id.name or ''}, {branch.zip or ''}"
                record.branch_address = address.strip(', ')
            else:
                record.branch_address = ''

    @api.depends('user_id.branch_id')
    def _compute_user_branch_phone(self):
        for record in self:
            branch = record.user_id.branch_id
            record.phone_branch = branch.phone or ''

    @api.depends('user_id.branch_id')
    def _compute_user_branch_email(self):
        for record in self:
            branch = record.user_id.branch_id
            record.email_branch = branch.email or ''

    @api.depends('user_id.branch_id')
    def _compute_user_branch_website(self):
        for record in self:
            branch = record.user_id.branch_id
            record.website_branch = branch.website or ''



class InvoiceLine(models.Model):
    _name = 'account.keuangan.invoice.line'
    _description = 'Invoice Line'

    # def _get_number(self):
    #     # Example: Generate a default number based on some logic
    #     line_count = len(self.search()) + 1  # Count all existing records + 1
    #     return str(line_count)  # Return the number as a string

    invoice_id = fields.Many2one('account.keuangan.invoice', string='Invoice', required=True, tracking=True, ondelete='cascade')
    name = fields.Char(string='Nama Kapal', tracking=True)
    nama_shipper = fields.Char(string='Nama Shipper', tracking=True)
    deskripsi_tagihan = fields.Text(string='Deskripsi', tracking=True)
    fixed_cost = fields.Float(string='Fixed Cost', tracking=True)
    variable_cost = fields.Float(string='Variable Cost', tracking=True)
    # tarif = fields.Float(string='Tarif', tracking=True)
    unit = fields.Float(string='Unit', digits=(16, 3), tracking=True)
    satuan = fields.Text(string='Satuan', tracking=True)
    pergerakan_in_out = fields.Float(string='Pergerakan In & Out', tracking=True, digits=(16, 0))
    # qty = fields.Float(string='Quantity')
    total_harga = fields.Float(string='Total Harga', compute='_compute_total_harga', store=True, tracking=True)
    ta = fields.Date(string='TA', tracking=True)
    td = fields.Date(string='TD', tracking=True)
    lumpsum = fields.Float(string="Lumpsum", digits=(16, 0), tracking=True)
    muatan = fields.Float(string='Muatan/MT', digits=(16, 3))
    ds = fields.Float(string='Draught Survey/DS', digits=(16, 3))

    bl = fields.Float(string="BL", tracking=True)
    tarif = fields.Float(string="Tarif", digits=(16, 0), tracking=True)

    gtbg = fields.Float(string="GT BG", tracking=True)
    fc_tunda = fields.Float(string="FC Tunda", tracking=True)
    vc_tunda = fields.Float(string="VC Tunda", tracking=True)
    fc_pandu = fields.Float(string="FC Pandu", tracking=True)
    vc_pandu = fields.Float(string="VC Pandu", tracking=True)
    # number = fields.Selection([
    #     # ('1', '1'), ('2', '2'), ('10', '10')  # Define all valid options here
    # ], string='No', default=_get_number)
    #(fc tunda+(vc tunda*gtbg))*2+(fc pandu+(vc pandu*gtbg))*2

    tipe_tarif = fields.Selection(
        related='invoice_id.tipe_tarif', 
        string="Tipe Tarif", 
        store=True, 
        tracking=True
    )
    jenis_kegiatan_name = fields.Char(
        related='invoice_id.jenis_kegiatan_name', 
        string="Jenis Kegiatan", 
        store=True, 
        tracking=True
    )

    tax_ids = fields.Many2many(
        'account.tax',
        string='Pajak',
        # domain=[('type_tax_use', '=', 'sale'), ('amount', '>', 0)]
        domain=[('type_tax_use', '!=', 'none')]
    )

    # tax_pph_ids = fields.Many2one(
    #     'account.tax',
    #     string='PPh',
    #     domain=[('type_tax_use', '=', 'sale'), ('name', 'ilike', 'pph')]
    # )

    tax_amount = fields.Float(
        string='Nilai Pajak',
        compute='_compute_tax_amount',
        tracking=True,
        digits=(16, 0)
    )
    
    # pph_amount = fields.Float(
    #     string='Nilai PPh',
    #     compute='_compute_pph_amount',
    #     store=True
    # )

    total_sebelum_pajak = fields.Float(
        string='Total Sebelum Pajak',
        compute='_compute_total_sebelum_pajak',
        tracking=True,
        digits=(16, 0)
    )

    total_sesudah_pajak = fields.Float(
        string='Total Sesudah Pajak',
        compute='_compute_total_sesudah_pajak',
        tracking=True,
        digits=(16, 0)
    )

    display_type = fields.Selection([
        ('normal', 'Normal'),
        ('line_section', 'Section Header'),
        ('line_note', 'Note'),
    ], string='Section', tracking=True, default='line_section')

    sequence = fields.Integer(string='Sequence', default=10)

    no = fields.Integer(string="Nomor", compute="_compute_no")

     
    formatted_ta = fields.Char(
        string='Formatted TA', 
        compute='_compute_formatted_ta', 
        readonly=True
    )
    
    formatted_td = fields.Char(
        string='Formatted TD', 
        compute='_compute_formatted_td', 
        readonly=True
    )

    @api.depends('ta')
    def _compute_formatted_ta(self):
        for record in self:
            if record.ta:
                record.formatted_ta = format_date(
                    record.ta, 
                    format='d MMMM y', 
                    locale='id_ID'
                ).upper()
            else:
                record.formatted_ta = 'N/A' 
                
    @api.depends('td')
    def _compute_formatted_td(self):
        for record in self:
            if record.td:
                record.formatted_td = format_date(
                    record.td, 
                    format='d MMMM y', 
                    locale='id_ID'
                ).upper()
            else:
                record.formatted_td = 'N/A'


    def _compute_no(self):
        for index, record in enumerate(self, start=1):
            record.no = index

    @api.onchange('total_sebelum_pajak', 'tax_amount')
    def _compute_total_sesudah_pajak(self):
        for record in self:
            record.total_sesudah_pajak = record.total_sebelum_pajak + record.tax_amount 


    @api.onchange('fixed_cost', 'variable_cost', 'tarif', 'unit', 'pergerakan_in_out', 
                 'lumpsum', 'bl', 'tarif', 'gtbg', 'fc_tunda', 'vc_tunda', 'fc_pandu', 'vc_pandu')
    
    def _compute_total_sebelum_pajak(self):
        for record in self:
            total = 0.0

            if record.jenis_kegiatan_name == 'Assist Tug':
                # Perhitungan berdasarkan tipe_tarif
                if record.tipe_tarif == 'lumpsum':
                    total += record.lumpsum or 0.0
                elif record.tipe_tarif == 'mt':
                    total += (record.muatan or 0.0) * (record.tarif or 0.0)
                elif record.tipe_tarif == 'grt_tongkang':
                    total += ((record.fc_tunda or 0.0) + ((record.vc_tunda or 0.0) * (record.gtbg or 0.0))) * 2
                    total += ((record.fc_pandu or 0.0) + ((record.vc_pandu or 0.0) * (record.gtbg or 0.0))) * record.pergerakan_in_out
                elif record.tipe_tarif == 'grt_vessel':
                    total += ((record.fc_tunda or 0.0) + ((record.vc_tunda or 0.0) * (record.gtbg or 0.0))) * 4
                    total += ((record.fc_pandu or 0.0) + ((record.vc_pandu or 0.0) * (record.gtbg or 0.0))) * record.pergerakan_in_out
            else:
                total += (record.tarif * record.unit or 0.0)

            record.total_sebelum_pajak = total

    @api.onchange('tax_ids')
    def _compute_tax_amount(self):
        for record in self:
            total_tax_amount = 0.0  # Inisialisasi total pajak
            for tax in record.tax_ids:  # Iterasi melalui setiap pajak yang dipilih
                # Hitung nilai pajak sebagai persentase dari total sebelum pajak
                total_tax_amount += record.total_sebelum_pajak * (tax.amount / 100)

            record.tax_amount = total_tax_amount  # Simpan total pajak

    # @api.depends('tax_pph_ids')
    # def _compute_pph_amount(self):
    #     for record in self:
    #         total_pph_amount = 0.0  # Inisialisasi total pajak
    #         for tax in record.tax_pph_ids:  # Iterasi melalui setiap pajak yang dipilih
    #             # Hitung nilai pajak sebagai persentase dari total sebelum pajak
    #             total_pph_amount += record.total_sebelum_pajak * (tax.amount / 100)

    #         record.pph_amount = total_pph_amount  # Simpan total pajak


    @api.onchange('tipe_tarif', 'lumpsum', 'bl', 'tarif', 'fc_tunda', 'vc_tunda', 'fc_pandu', 'vc_pandu', 'gtbg', 'pergerakan_in_out')
    def _compute_total_harga(self):
        for record in self:
            if record.tipe_tarif == 'lumpsum':
                # Lumpsum
                record.total_harga = record.lumpsum
            elif record.tipe_tarif == 'mt':
                # MT = bl * tarif
                record.total_harga = record.muatan * record.tarif
            elif record.tipe_tarif == 'grt_tongkang':
                # GRT Tongkang = (fc tunda + (vc tunda * gtbg)) * 2 + (fc pandu + (vc pandu * gtbg)) * 2
                record.total_harga = ((record.fc_tunda + (record.vc_tunda * record.gtbg)) * 2) + ((record.fc_pandu + (record.vc_pandu * record.gtbg)) * record.pergerakan_in_out)
            elif record.tipe_tarif == 'grt_vessel':
                # GRT Vessel = (fc tunda + (vc tunda * gtbg)) * 4 + (fc pandu + (vc pandu * gtbg)) * 2
                record.total_harga = ((record.fc_tunda + (record.vc_tunda * record.gtbg)) * 4) + ((record.fc_pandu + (record.vc_pandu * record.gtbg)) * record.pergerakan_in_out)
            else:
                # Hitung total sebelum pajak dengan memastikan nilai tidak kosong
                record.total_harga = (record.fixed_cost or 0.0) * (record.variable_cost or 0.0) * (record.tarif or 0.0) * (record.unit or 0.0) * (record.pergerakan_in_out or 0.0) 
