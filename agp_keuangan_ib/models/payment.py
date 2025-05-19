from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

class AccountKeuanganRegisterPayment(models.Model):
    _name = 'account.keuangan.register.payment'
    _description = 'Register Payment for Invoice'

    name = fields.Char(string="Payment Reference", required=True, default="New")
    payment_date = fields.Date(string="Payment Date", required=True, default=fields.Date.context_today)
    
    tax_ids = fields.Many2many(
        'account.tax',
        string='Pajak',
        # domain=[('type_tax_use', '=', 'sale'), ('amount', '>', 0)]
        domain=[('type_tax_use', '!=', 'none')]
    )

    tax_amount = fields.Float(
        string='Nilai Pajak',
        compute='_compute_tax_amount',
        tracking=True,
        digits=(16, 0)
    )

    nominal = fields.Float(string="Nominal Pembayaran", default=0.0, help="Nominal")
    pph_23 = fields.Float(string="PPH 23", default=0.0, help="Potongan PPH 23 yang dipotong atas pembayaran")
    ppn_tidak_dibayar = fields.Float(string="PPN Tidak Dibayar", default=0.0, help="Nilai PPN yang tidak dibayar")
    admin_bank = fields.Float(string="Admin Bank", default=0.0, help="Biaya administrasi bank")
    denda = fields.Float(string="Denda", default=0.0, help="Denda untuk pembayaran terlambat")
    nominal_lain = fields.Float(string="Nilai Lain", default=0.0, help="Nominal Lain")
    keterangan = fields.Text(string="Keterangan", help="Keterangan untuk selisih nominal pembayaran dan invoice")
    
    total_sesudah_pajak = fields.Float(string='Nilai Pekerjaan', compute="_compute_total_sesudah_pajak", store=True)
    jenis_kegiatan_name = fields.Char(string='Jenis Kegiatan', related="invoice_id.jenis_kegiatan_name", store=True)
    
    # Amount paid
    total_nilai_pekerjaan = fields.Float(string="Total Nilai Pekerjaan Yang Harus Dibayar", compute="_compute_total_nilai_pekerjaan", store=True, help="Total jumlah yang dibayarkan")
    amount_paid = fields.Float(string="Nominal Pembayaran", store=True, help="Nilai Bayar")

    # Amount residual (sisa yang belum dibayar)
    amount_residual = fields.Float(string="Amount Residual", compute="_compute_amount_residual", store=True)

    ditujukan_kepada = fields.Many2one('res.partner', string="Partner", required=True)
    invoice_id = fields.Many2one('account.keuangan.invoice', string="Related Invoice", required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
    ], default='draft', string="Status")

    # payment_method = fields.Selection([
    #     ('cash', 'Cash'),
    #     ('bank_transfer', 'Bank Transfer'),
    #     ('credit_card', 'Credit Card'),
    # ], string="Payment Method", required=True)

    bank_account_id = fields.Many2one('res.partner.bank', string="Bank Account", related="invoice_id.bank_account_id", readonly=True, store=True)
    jenis_kegiatan_id = fields.Many2one('jenis.kegiatan', string="Jenis Kegiatan", related="invoice_id.jenis_kegiatan_id", readonly=True, store=True)
    total_sebelum_pajak = fields.Float(string="Nilai Sebelum Pajak", related="invoice_id.total_sebelum_pajak", readonly=True, store=True)
    account_code_id = fields.Many2one('account.account', string="Account Code", compute='_compute_kode_anggaran', store=True)
    kode_anggaran = fields.Char(string="Kode Anggaran", compute='_compute_kode_anggaran', store=True)


    @api.onchange('total_sesudah_pajak', 'pph_23', 'tax_amount', 'ppn_tidak_dibayar', 'admin_bank', 'denda', 'nominal_lain')
    def _compute_total_nilai_pekerjaan(self):
        for record in self:
            record.total_nilai_pekerjaan = ((
                record.total_sesudah_pajak + record.tax_amount) -
                ( record.ppn_tidak_dibayar
                + record.admin_bank
                + record.denda
                + record.nominal_lain)
            )

    @api.depends('jenis_kegiatan_id')
    def _compute_kode_anggaran(self):
        for record in self:
            if record.jenis_kegiatan_id:
                # Search for kode anggaran with kepala "4" and matching jenis_kegiatan_id
                anggaran = self.env['account.keuangan.kode.anggaran'].search([
                    ('jenis_kegiatan_id', '=', record.jenis_kegiatan_id.id),
                    ('kode_anggaran', '=like', '4%')  # Matches codes starting with '4'
                ], limit=1)

                if anggaran:
                    record.kode_anggaran = anggaran.kode_anggaran
                    record.account_code_id = anggaran.account_code_id
                else:
                    record.kode_anggaran = False
                    record.account_code_id = False

    @api.onchange('tax_ids')
    def _compute_tax_amount(self):
        for record in self:
            total_tax_amount = 0.0  # Inisialisasi total pajak
            for tax in record.tax_ids:  # Iterasi melalui setiap pajak yang dipilih
                # Hitung nilai pajak sebagai persentase dari total sebelum pajak
                total_tax_amount = record.total_sebelum_pajak * (tax.amount / 100)

            record.tax_amount = total_tax_amount  # Simpan total pajak

    
    @api.depends('invoice_id')
    def _compute_total_sesudah_pajak(self):
        for record in self:
            if record.invoice_id:
                record.total_sesudah_pajak = record.invoice_id.remaining_balance  # Get remaining balance from invoice


    @api.depends('invoice_id.remaining_balance', 'amount_paid')
    def _compute_amount_residual(self):
        for record in self:
            if record.invoice_id:
                # Calculate the residual based on the remaining balance of the invoice
                record.amount_residual = record.invoice_id.remaining_balance - record.amount_paid


    @api.model
    def create(self, vals):
        # Access context variables
        context = self.env.context
        invoice_id = context.get('default_invoice_id')  # Replace 'custom_key' with your actual key
        if invoice_id:
            invoice = self.env['account.keuangan.invoice'].sudo().browse(invoice_id)
            if invoice:
                kegiatan_id = invoice.jenis_kegiatan_id.id

        if vals.get('name', 'New') == 'New' and kegiatan_id:
            print('vals_get')
            vals['name'] = self.env['ir.sequence'].next_by_code('account.keuangan.register.payment') or 'New'
            kode_anggaran_id = self.env['account.keuangan.kode.anggaran'].sudo().search([
                ('jenis_kegiatan_id', '=', kegiatan_id)
            ], limit=1)
            if kode_anggaran_id:
                print('kode_anggaran')
                coa_id = kode_anggaran_id.account_code_id
                rkap_line_id = self.env['account.keuangan.rkap.line'].sudo().search([
                    ('kode_anggaran_id', '=', kode_anggaran_id.id),
                    ('account_code_id', '=', coa_id.id),
                    ('branch_id', '=', invoice.branch_id.id),
                ], limit=1)
                kkhc_line_id = self.env['account.keuangan.kkhc.line'].sudo().search([
                    ('kode_anggaran_id', '=', kode_anggaran_id.id),
                    ('account_code_id', '=', coa_id.id),
                    ('branch_id', '=', invoice.branch_id.id),
                ], limit=1)
                if rkap_line_id and kkhc_line_id:
                    amount_paid_invoice = vals['amount_paid']
                    current_pemakaian = rkap_line_id.pemakaian_anggaran
                    current_nominal_disetujui = kkhc_line_id.nominal_disetujui
                    current_nominal = rkap_line_id.nominal
                    current_nominal_pengajuan = kkhc_line_id.nominal_pengajuan

                    # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
                    # FINAL REALISASI RKAP
                    # FIRST WRITE
                    rkap_line_id.write({'pemakaian_anggaran': current_pemakaian + amount_paid_invoice})
                    self.env.flush_all()

                    # 🚀 Reload the updated record
                    updated_rkap_line = self.env['account.keuangan.rkap.line'].browse(rkap_line_id.id)
                    current_pemakaian = updated_rkap_line.pemakaian_anggaran  # Now it holds the updated value

                    # SECOND WRITE
                    rkap_line_id.write({'realisasi': current_nominal - current_pemakaian})

                    # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
                    # FINAL REALISASI KKHC
                    # FIRST WRITE
                    kkhc_line_id.write({'nominal_disetujui': current_nominal_disetujui + amount_paid_invoice})
                    self.env.flush_all()

                    # 🚀 Reload the updated record
                    updated_kkhc_line = self.env['account.keuangan.kkhc.line'].browse(kkhc_line_id.id)
                    current_nominal_disetujui = updated_kkhc_line.nominal_disetujui  # Now it holds the updated value

                    # SECOND WRITE
                    kkhc_line_id.write({'sisa_pengajuan': current_nominal_pengajuan - current_nominal_disetujui})

                    # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
                    # CASH IN/OUT DISINIII

                    # Buat record payment
                    record = super(AccountKeuanganRegisterPayment, self).create(vals)
                    
                    # Tambahkan data ke account.keuangan.transaction
                    if record.invoice_id:
                        self.env['account.keuangan.transaction'].create({
                            'payment_id': record.id,
                            'bank_account_id': record.bank_account_id.id,
                            'invoice_id': record.invoice_id.id,
                            'amount_paid': record.amount_paid,
                            'payment_date': record.payment_date,
                        })
        
                else:
                    raise ValidationError(
                        'Item RKAP dan Item KKHC Cabang atas Invoice ini tidak ditemukan! Register Payment atas Invoice ini tidak dapat dilanjutkan. Silakan cek kembali!'
                    )

        # return super(AccountKeuanganRegisterPayment, self).create(vals)
        return record

    # def action_post(self):
    #     """Change the status to posted after payment is registered."""
    #     for record in self:
    #         if record.state == 'draft':
    #             record.state = 'posted'
    #         else:
    #             raise UserError("This payment has already been posted.")

    # def action_draft(self):
    #     """Revert status to draft if needed."""
    #     for record in self:
    #         if record.state == 'posted':
    #             record.state = 'draft'
    #         else:
    #             raise UserError("This payment is not yet posted.")
