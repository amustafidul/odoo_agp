# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from num2words import num2words
import re

from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError, AccessError, ValidationError

from . import helpers
from odoo.tools import format_date


import re
import logging
_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'
    new_sequence = fields.Char(string='New Sequence', readonly=True, compute='_compute_new_sequence')

    jenis_kegiatan = fields.Selection([
        ('emkl', 'EMKL'),
        ('bongkar_muat', 'Bongkar Muat'),
        ('keagenan', 'Keagenan'),
        ('assist_tug', 'Assist Tug'),
        ('jetty_manajemen', 'Jetty Manajemen'),
        ('jasa_operasi_lainnya', 'Jasa Operasi Lainnya'),
        ('logistik', 'Logistik')
    ], string='Jenis Kegiatan*')

    jenis_kegiatan_id = fields.Many2one('jenis.kegiatan', string='Jenis Kegiatan')
    jenis_kegiatan_name = fields.Char(string="Jenis Kegiatan Name", compute="_compute_jenis_kegiatan_name")

    # code = fields.Char(string='Code', compute='_compute_code', store=True)

    nomor_ref = fields.Char(string='Nomor Reference') 
    note = fields.Char(string='Note')
    nama_kapal = fields.Char(string='Nama Kapal')  

    startworkperiod = fields.Date(string="Start Work Period")
    finishworkperiod = fields.Date(string="Finish Work Period")

    ta = fields.Date(string='TA')
    td = fields.Date(string='TD')
    muatan = fields.Float(string='Muatan/MT', digits=(10, 3))
    gtbg = fields.Float(string='GT BG', digits=(16, 0))
    tu_assist_fc = fields.Float(string='Tug Assist FC', digits=(16, 0))
    tu_assist_vc = fields.Float(string='Tug Assist VC', digits=(16, 0))
    pilotage_fc = fields.Float(string='Pilotage FC', digits=(16, 0))
    pilotage_vc = fields.Float(string='Pilotage VC', digits=(16, 0))
    in_out = fields.Float(string='Pergerakan In Out', digits=(16, 0))
    tarif = fields.Float(string='Tarif Lumpsum', digits=(16, 0))

    total = fields.Float(string='Total', compute='_compute_total', digits=(16, 0))
    total_terbilang = fields.Char(string='Total Terbilang', compute='_compute_total_terbilang')

    no_invoice = fields.Char(string='Nomor Invoice')
    no_efaktur = fields.Char(string='Nomor E-Faktur')
    no_bupot = fields.Char(string='Nomor Bukti Potong')
    kode_kontrak = fields.Char(string='Nomor/ Kode Kontrak')
    tgl_kontrak = fields.Date(string='Tanggal Kontrak')

    # ref_no = fields.Char(string='Ref No')

    taxes = fields.Float(string='Taxes', compute='compute_taxes')
    # bank_account_ids = fields.Many2one('res.partner.bank', string='Bank Accounts', compute='_compute_bank_accounts', store=True)
    bank_account_ids = fields.Many2many('res.partner.bank', string='Bank Accounts', store=True)
    # account_id = fields.Many2one('account.account', string='Account', compute='_compute_account_id', store=True)    
    # # nomor_perjanjian_id = fields.Many2one('account.keuangan.surat.perjanjian', string='Nomor Surat Perjanjian', domain="[('partner_id', '=', ditujukan_kepada)]", store=True)
    
    # # nomor_addendum_id = fields.Many2one(
    # #         'account.keuangan.surat.perjanjian.line',  # Terkait dengan account.keuangan.surat.perjanjian.line
    # #         string='No. Addendum',
    # #         domain="[('nomor_perjanjian_id', '=', nomor_perjanjian_id)]",  # Memfilter berdasarkan nomor_perjanjian_id
    # #         store=True
    # #     )

    # # tanggal_akhir = fields.Date(string='Tanggal Akhir', related='nomor_addendum_id.tanggal_addendum_akhir', readonly=True, store=True, tracking=True)

    state = fields.Selection(
        selection_add=[
            ('submitted_by_receptionist', 'Submitted by Receptionist'),
            ('submitted_by_division', 'Submitted by Division'),
            ('submitted_to_accounting', 'Submitted to Accounting')
        ],
        ondelete={
            'submitted_by_receptionist': 'set default',
            'submitted_by_division': 'set default',
            'submitted_to_accounting': 'set default'
        }
    )
    # alamat_perusahaan = fields.Char(string='Alamat Perusahaan', compute='_compute_alamat_perusahaan', store=True)
    nomor_referensi = fields.Char(string='No. Invoice')
    spp_id = fields.Many2one(   
        comodel_name='report.report_multi_branch.spp',
        string='SPP',
        tracking=True
    )
    # tanggal_spp = fields.Date(string='Tanggal SPP', related='spp_id.tanggal_spp', readonly=True, store=True, tracking=True)
    kata_pengantar = fields.Text(string='Kata Pengantar')
    nomor_rekening = fields.Char(string='No. Rekening')
    nomor_perjanjian_id = fields.Many2one('account.keuangan.surat.perjanjian', string='No. Perjanjian')
    tanggal_perjanjian = fields.Date(string='Tanggal Perjanjian')
    tanggal_akhir = fields.Date(string='Tanggal Akhir')
    nomor_addendum_id = fields.Many2one('account.keuangan.surat.perjanjian.line', string='No. Addendum')
    # tanggal_akhir_addendum = fields.Date(
    #     string='Tanggal Akhir',
    #     related='nomor_addendum_id.tanggal_addendum_akhir',
    #     readonly=True,
    #     store=True,
    #     tracking=True
    # )
    branch_ids = fields.Many2many('res.branch', string='Cabang')
    sub_branch_ids = fields.Many2many('sub.branch', string='Sub Cabang')
    keterangan = fields.Text(string='Keterangan')
    spp = fields.Text(string='SPP')


    # @api.constrains('state')
    # def _check_state_transition(self):
    #     """Validate state transitions follow receptionist -> division -> accounting flow."""
    #     valid_transitions = {
    #         'submitted_by_receptionist': 'submitted_by_division',
    #         'submitted_by_division': 'submitted_to_accounting'
    #     }
    #     for record in self:
    #         if record.state and record._origin.state:
    #             if valid_transitions.get(record._origin.state) != record.state:
    #                 raise ValidationError(
    #                     f"Invalid state transition from {record._origin.state} to {record.state}. "
    #                     f"Expected transition to {valid_transitions.get(record._origin.state)}."
    #                 )

    def action_submit_by_receptionist(self):
        """Submit the account move to receptionist state."""
        if self.state != 'submitted_by_receptionist':
            self.write({'state': 'submitted_by_receptionist'})
        return True

    def action_submit_to_division(self):
        """Submit the account move to division state."""
        if self.state != 'submitted_by_receptionist':
            raise ValidationError(
                "Cannot submit to division. Move must be in 'Submitted by Receptionist' state."
            )
        self.write({'state': 'submitted_by_division'})
        return True

    def action_submit_to_accounting(self):
        """Submit the account move to accounting state."""
        self.ensure_one()
        if self.state != 'submitted_by_division':
            raise ValidationError(
                "Cannot submit to accounting. Move must be in 'Submitted by Division' state."
            )
        self.write({'state': 'submitted_to_accounting'})
        self.action_confirm()
        self.action_post()
        return True

    # @api.depends('partner_id')
    # def _compute_alamat_perusahaan(self):
    #     for record in self:
    #         if record.partner_id:
    #             record.alamat_perusahaan = record.partner_id.contact_address
    #         else:
    #             record.alamat_perusahaan = ''

    @api.onchange('nomor_perjanjian_id')
    def _onchange_nomor_perjanjian_id(self):
        if self.nomor_perjanjian_id:
            # Set nilai dari related field
            # self.bank_account = self.nomor_perjanjian_id.bank_account_harian_id.name
            # self.branch_id = self.nomor_perjanjian_id.branch_id
            self.tanggal_perjanjian = self.nomor_perjanjian_id.tanggal_perjanjian

            # Cari addendum terakhir
            last_addendum = self.env['account.keuangan.surat.perjanjian.line'].search(
                [('nomor_perjanjian_id', '=', self.nomor_perjanjian_id.id)],
                order='id desc',
                limit=1
            )
            self.nomor_addendum_id = last_addendum if last_addendum else False
        else:
            # self.bank_account = False
            # self.branch_id = False
            self.tanggal_perjanjian = False
            self.nomor_addendum_id = False

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        user = self.env.user
        company_ids = user.company_ids.ids  # Daftar perusahaan yang diizinkan untuk pengguna
        allowed_branch_ids = user.branch_ids.ids  # Daftar cabang yang diizinkan
        
        # Log untuk melacak perusahaan yang diizinkan
        _logger.info("User %s allowed companies: %s", user.name, company_ids)
        
        # Log untuk melacak cabang yang diizinkan
        _logger.info("User %s allowed branches: %s", user.name, allowed_branch_ids)

        # Tambahkan filter company_id hanya jika pengguna memiliki akses ke perusahaan tertentu
        if company_ids:
            args.append(('company_id', 'in', company_ids))
            _logger.info("Filtering by company_id: %s", company_ids)
            
            # Tambahkan filter branch_id jika perusahaan valid dan pengguna memiliki akses ke cabang tertentu
            if allowed_branch_ids:
                args.append(('branch_id', 'in', allowed_branch_ids))
                _logger.info("Filtering by branch_id: %s", allowed_branch_ids)
        
        result = super(AccountMove, self).search(args, offset, limit, order, count)
        
        # Log hasil akhir dari query pencarian
        _logger.info("Search result count: %s", len(result) if not count else result)
        
        return result

    @api.depends('jenis_kegiatan_id')
    def _compute_jenis_kegiatan_name(self):
        for record in self:
            record.jenis_kegiatan_name = record.jenis_kegiatan_id.name if record.jenis_kegiatan_id else ''
    
    
    # @api.depends('jenis_kegiatan')
    # def _compute_code(self):
    #     codes = {
    #         'emkl': 'EMK',
    #         'bongkar_muat': 'PBM',
    #         'keagenan': '   AGN',
    #         'assist_tug': 'ASS',
    #         'jetty_manajemen': 'JTM',
    #         'jasa_operasi_lainnya': 'OTH',
    #         'logistik': 'LOG'
    #     }
        
    #     for record in self:
    #         record.code = codes.get(record.jenis_kegiatan, '')

    @api.depends('invoice_line_ids.quantity', 'invoice_line_ids.price_unit', 'invoice_line_ids.tax_ids')
    def compute_taxes(self):
        for rec in self:
            rec.taxes = 0.0
            if rec.invoice_line_ids:
                taxes = sum((line.quantity * line.price_unit) * tax.amount / 100 for line in rec.invoice_line_ids for tax in line.tax_ids.filtered(lambda x:x.include_taxes))
                if rec.company_id.round_tax and not rec.company_id.round_tax == 'NONE':
                    precision = float(rec.company_id.precision_rounding)
                    rounding_method = str(rec.company_id.round_tax)
                    taxes = float_round(taxes, precision_rounding=precision, rounding_method=rounding_method)
                rec.taxes = taxes
    

    
    @api.depends('total')
    def _compute_total_terbilang(self):
        for record in self:
            total_terbilang = num2words(record.total, lang='id').title().replace('-', ' ')
            currency_name = "Rupiah"  # Ubah ke mata uang yang sesuai jika perlu
            record.total_terbilang = f"{total_terbilang} {currency_name}"

    @api.depends('ta', 'td', 'muatan', 'gtbg', 'tu_assist_fc', 'tu_assist_vc', 'pilotage_fc', 'pilotage_vc', 'in_out')
    def _compute_total(self):
        for record in self:
            tu_assist_fc = record.tu_assist_fc or 0
            tu_assist_vc = record.tu_assist_vc or 0
            pilotage_fc = record.pilotage_fc or 0
            pilotage_vc = record.pilotage_vc or 0
            gtbg = record.gtbg or 0
            in_out = record.in_out or 0

            total = ((tu_assist_fc + (gtbg * tu_assist_vc)) + (pilotage_fc + (gtbg * pilotage_vc))) * in_out
            record.total = total

    # @api.onchange('jenis_kegiatan')
    # def _onchange_jenis_kegiatan_company(self):
    #     """Method to update accounts in accounting_entries group based on jenis_kegiatan"""
    #     company = self.env.user.company_id
    #     receivable_account = False
    #     payable_account = False

    #     if self.jenis_kegiatan == 'emkl':
    #         receivable_account = company.emkl_account_id
    #         payable_account = company.emkl_account_id
    #     elif self.jenis_kegiatan == 'bongkar_muat':
    #         receivable_account = company.bongkar_muat_account_id
    #         payable_account = company.bongkar_muat_account_id
    #     elif self.jenis_kegiatan == 'keagenan':
    #         receivable_account = company.keagenan_account_id
    #         payable_account = company.keagenan_account_id
    #     elif self.jenis_kegiatan == 'assist_tug':
    #         receivable_account = company.assist_tug_account_id
    #         payable_account = company.assist_tug_account_id
    #     elif self.jenis_kegiatan == 'jetty_manajemen':
    #         receivable_account = company.jetty_manajemen_account_id
    #         payable_account = company.jetty_manajemen_account_id
    #     elif self.jenis_kegiatan == 'jasa_operasi_lainnya':
    #         receivable_account = company.jasa_operasi_lainnya_account_id
    #         payable_account = company.jasa_operasi_lainnya_account_id
    #     elif self.jenis_kegiatan == 'logistik':
    #         receivable_account = company.logistik_account_id
    #         payable_account = company.logistik_account_id

    #     if receivable_account and payable_account:
    #         self.property_account_receivable_id = receivable_account.id
    #         self.property_account_payable_id = payable_account.id


    @api.onchange('jenis_kegiatan')
    def _onchange_jenis_kegiatan(self):
        account_code = False  # Inisialisasi awal
        if self.jenis_kegiatan == 'emkl':
            account_code = '4101000'
        elif self.jenis_kegiatan == 'bongkar_muat':
            account_code = '4102000'
        elif self.jenis_kegiatan == 'keagenan':
            account_code = '4103000'
        elif self.jenis_kegiatan == 'assist_tug':
            account_code = '4104000'
        elif self.jenis_kegiatan == 'jetty_manajemen':
            account_code = '4105000'
        elif self.jenis_kegiatan == 'jasa_operasi_lainnya':
            account_code = '4106000'
        elif self.jenis_kegiatan == 'logistik':
            account_code = '4107000'

        if account_code:
            account = self.env['account.account'].search([('code', '=', account_code)], limit=1)
            if account:
                for line in self.invoice_line_ids:
                    line.account_id = account.id

    sub_branch_ids = fields.Many2many('sub.branch', string="Sub Branches")

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        if self.branch_id:
            return {'domain': {'sub_branch_ids': [('id', 'in', self.branch_id.sub_branch_ids.ids)]}}
        else:
            return {'domain': {'sub_branch_ids': []}}

    def _get_default_branch(self):
        return False

    def _get_branch_domain(self):
        return []

    def action_post(self):
        user = self.env.user
        if not user.has_group('base.group_system') and not user.has_group('module_name.group_advisor') and not user.allow_posting_journal_entries:
             raise AccessError(_('Kesalahan Hak Akses: \n'
                                 'Operasi yang diminta tidak dapat diselesaikan karena hak akses. \n'
                                 'Silakan hubungi administrator.\n '
                                'Fitur ini hanya diizinkan untuk grup pengguna:\n '
                                '- Allow Confirm / Posting Journal Entries'))
        
        # user = self.env.user
        # if not user.has_group('base.group_system') and not user.has_group('module_name.group_advisor') and not user.allow_posting_journal_entries:
        #     return {
        #         'type': 'ir.actions.act_window',
        #         'name': 'Access Denied',
        #         'res_model': 'ir.actions.client',
        #         'view_mode': 'form',
        #         'view_id': self.env.ref('agp_custom_fields.action_access_denied').id,
        #         'target': 'new',
        #     }

        moves_with_payments = self.filtered('payment_id')
        other_moves = self - moves_with_payments
        if moves_with_payments:
            moves_with_payments.payment_id.action_post()
        if other_moves:
            other_moves._post(soft=False)

        return True

    # def action_post(self):
    #     for move in self:
    #         if not move.nomor_journal or move.nomor_journal == '/':
    #             move.nomor_journal = self.env['ir.sequence'].next_by_code('account.move.nomor_journal') or '/'
    #     return super(AccountMove, self).action_post()

    
    # @api.depends('bank_account_ids')
    # def _compute_account_id(self):
    #     for move in self:
    #         if move.bank_account_ids:
    #             move.account_id = move.bank_account_ids[0].account_id.id if move.bank_account_ids[0].account_id else False
    #             _logger.info('Account ID set to: %s', move.account_id)
    #         else:
    #             move.account_id = False
    #             _logger.info('No bank account IDs found, setting account_id to False')

    @api.depends('company_id')
    def _compute_bank_accounts(self):
        for move in self:
            if move.company_id:
                bank_accounts = self.env['res.partner.bank'].search([('company_id', '=', move.company_id.id)])
                move.bank_account_ids = [(6, 0, bank_accounts.ids)]
                _logger.info('Bank accounts set to: %s', bank_accounts)
            else:
                move.bank_account_ids = [(5,)]
                _logger.info('No company ID found, setting bank_account_ids to False')

    # @api.onchange('bank_account_ids')
    # def _onchange_bank_account_ids(self):
    #     account_id = False  # Initialize account_id
    #     if self.bank_account_ids:
    #         account_id = self.bank_account_ids[0].account_id.id if self.bank_account_ids[0].account_id else False
    #         for line in self.line_ids:
    #             line.account_id = account_id
    #             _logger.info('Line account ID set to: %s', line.account_id)
    #     _logger.info('Bank accounts onchange triggered with bank_account_ids: %s and account_id: %s', self.bank_account_ids, account_id)

   
    @api.depends('journal_id', 'date', 'move_type', 'payment_id', 'jenis_kegiatan_id')
    def _compute_new_sequence(self):
        for record in self:
            record.new_sequence = record._get_starting_sequence()

    def _get_starting_sequence(self):
        # Ensure only one record is being processed
        self.ensure_one()

        # Fetch the branch code
        user_branch_code = self.env.user.branch_id.code if self.env.user.branch_id else 'DEFAULT_BRANCH_CODE'

        # Fetch the journal code
        journal_code = self.journal_id.code if self.journal_id else 'DEFAULT_JOURNAL_CODE'
        # jenis_kegiatan_code = self.jenis_kegiatan_id.code if self.jenis_kegiatan_id else '-'
        year = self.date.year
        month = "%02d" % self.date.month
        day = "%02d" % self.date.day

        jenis_kegiatan_code = '-'
        context = self.env.context  # Pastikan context diambil dari self.env.context


        if context.get('active_model') == 'account.move':
            moves = self.env['account.move'].browse(context.get('active_ids', []))
            if moves and moves.jenis_kegiatan_id:
                jenis_kegiatan_code = moves.jenis_kegiatan_id.code
        
        elif self.jenis_kegiatan_id:
            jenis_kegiatan_code = self.jenis_kegiatan_id.code


        # Prepare the base format for the sequence
        base_sequence = "%s/%s/%s/%04d%s" % (journal_code, user_branch_code, jenis_kegiatan_code, year, month)

        _logger.info("Base Sequence: %s", base_sequence)

        # ini kalo error unkomen ajah 
        # helpers.get_next_sequence_number(base_sequence, is_payment, last_number)

        # def get_next_sequence_number(base_sequence, is_payment, last_number):
        #     new_number = last_number + 1
        #     new_sequence = "%s/%04d" % (base_sequence, new_number)

        #     # Add prefix based on refund or payment conditions
        #     if self.journal_id.refund_sequence and self.move_type in ('out_refund', 'in_refund'):
        #         new_sequence = "R" + new_sequence
        #     if self.journal_id.payment_sequence and is_payment:
        #         new_sequence = "P" + new_sequence

        #     _logger.info("New Sequence Generated: %s", new_sequence)
        #     return new_sequence

        # is_payment = self.payment_id or self._context.get('is_payment')

        # Get the last sequence number for this journal and period
        last_sequence = self.search([
            ('journal_id', '=', self.journal_id.id),
            # ('jenis_kegiatan_id', '=', self.jenis_kegiatan_id.code),
            ('name', 'like', base_sequence + "/%"),
            # ('date', '>=', fields.Date.to_string(self.date.replace(day=1))),
            # ('date', '<=', fields.Date.to_string(self.date))
        ], order='name desc', limit=1)

        last_number = 0  # Default if no previous sequence found
        if last_sequence:
            last_sequence_number = last_sequence.name.split('/')[-1]

            # Gunakan regex untuk memastikan hanya angka yang dikonversi ke int
            match = re.search(r'(\d+)$', last_sequence_number)
            if match:
                last_number = int(match.group(1))

        new_sequence = helpers.get_next_sequence_number(
            base_sequence=base_sequence,
            is_payment=self.payment_id or self._context.get('is_payment'),
            last_number=last_number,
            journal_id=self.journal_id,
            move_type=self.move_type
        )

        # Ensure the sequence is unique by checking and updating if necessary
        while self.search([
            ('journal_id', '=', self.journal_id.id),
            # ('jenis_kegiatan_id', '=', self.jenis_kegiatan_id.code),
            ('name', '=', new_sequence),
            # ('date', '>=', fields.Date.to_string(self.date.replace(day=1))),
            # ('date', '<=', fields.Date.to_string(self.date))
        ]):
            last_number += 1
            new_sequence = helpers.get_next_sequence_number(
                base_sequence=base_sequence,
                is_payment=self.payment_id or self._context.get('is_payment'),
                last_number=last_number,
                journal_id=self.journal_id,
                move_type=self.move_type
            )

        _logger.info("Final Sequence to Save: %s", new_sequence)

        # warning_message = "Generated Sequence: %s" % new_sequence, base_sequence
        # raise UserError(warning_message)
            
        return new_sequence



    @api.model
    def create(self, vals):
        if vals.get('name') == '/':
            temp_move = self.new(vals)
            base_sequence = temp_move._get_starting_sequence()

            vals['name'] = base_sequence  # Set sequence ke name

        return super(AccountMove, self).create(vals)


    def write(self, vals):
        for record in self:
            if record.name == '/' and 'name' not in vals:
                base_sequence = record._get_starting_sequence()

                vals['name'] = base_sequence

        return super(AccountMove, self).write(vals)

    
    def action_penyesuaian_journal(self):
        for rec in self.with_context(check_move_validity=False):
            if rec.move_type == 'in_invoice':
                to_delete = rec.line_ids.filtered(lambda x:x.display_type not in ['product'])
                # to_delete = rec.line_ids.filtered(lambda x:x.display_type in ['payment_term'] and x.account_id.id != x.product_id.product_tmpl_id.account_hutang_id.id)
                if to_delete:
                    lines_vals_list = []
                    for line in rec.invoice_line_ids:
                        if not line.product_id.product_tmpl_id.account_hutang_id:
                            raise UserError('Akun Hutang pada product tidak boleh kosong')
                        pajak = sum((line.quantity * line.price_unit) * tax.amount / 100 for tax in line.tax_ids)
                        balance = (line.quantity * line.price_unit) + pajak
                        lines_vals_list.append({
                            'name': '',
                            'move_id': rec.id,
                            'partner_id': rec.partner_id.id,
                            'product_id': False,
                            'product_uom_id': False,
                            'quantity': line.quantity,
                            # 'price_unit': -line.price_unit,
                            # 'amount_currency': line.price_subtotal,
                            'balance': -balance,
                            'account_id': line.product_id.product_tmpl_id.account_hutang_id.id,
                            'display_type': 'payment_term',
                            # 'tax_ids': line.tax_ids.ids,
                            'tax_ids': [],
                        })
                    self.env.cr.execute("""delete from account_move_line where id in %s""",[tuple(to_delete.ids)])
                    self.env.cr.commit()
                    self.env['account.move.line'].with_context(check_move_validity=False).create(lines_vals_list)
            elif rec.move_type == 'out_invoice':
                to_delete = rec.line_ids.filtered(lambda x:x.display_type not in ['product'])
                # to_delete = rec.line_ids.filtered(lambda x:x.display_type in ['payment_term'] and x.account_id.id != x.product_id.product_tmpl_id.account_piutang_id.id)
                if to_delete:
                    lines_vals_list = []
                    for line in rec.invoice_line_ids:
                        if not line.product_id.product_tmpl_id.account_piutang_id:
                            raise UserError('Akun Piutang pada product tidak boleh kosong')
                        pajak = sum((line.quantity * line.price_unit) * tax.amount / 100 for tax in line.tax_ids)
                        balance = (line.quantity * line.price_unit) + pajak
                        lines_vals_list.append({
                            'name': '',
                            'move_id': rec.id,
                            'partner_id': rec.partner_id.id,
                            'product_id': False,
                            'product_uom_id': False,
                            'quantity': line.quantity,
                            # 'price_unit': -line.price_unit,
                            # 'amount_currency': line.price_subtotal,
                            'balance': balance,
                            'account_id': line.product_id.product_tmpl_id.account_piutang_id.id,
                            'display_type': 'payment_term',
                            # 'tax_ids': line.tax_ids.ids,
                            'tax_ids': [],
                        })
                    self.env.cr.execute("""delete from account_move_line where id in %s""",[tuple(to_delete.ids)])
                    self.env.cr.commit()
                    self.env['account.move.line'].with_context(check_move_validity=False).create(lines_vals_list)

    
    def _check_lock_date(self):
        """Cek apakah transaksi melanggar lock date."""
        for move in self:
            lock_date = move.branch_id._get_user_fiscal_lock_date() if move.branch_id else move.company_id._get_user_fiscal_lock_date()
            if move.date <= lock_date:
                if self.user_has_groups('account.group_account_manager'):
                    message = _("You cannot modify entries prior to and inclusive of the lock date %s.", format_date(self.env, lock_date))
                else:
                    message = _("You cannot modify entries prior to and inclusive of the lock date %s. Check the company settings or ask someone with the 'Adviser' role.", format_date(self.env, lock_date))
                raise UserError(message)
            

    def write(self, vals):  
        """Cek lock date sebelum mengedit data."""
        self._check_lock_date()
        return super(AccountMove, self).write(vals)
    
    
    def button_draft(self):
        exchange_move_ids = set()
        if self:
            self.env['account.full.reconcile'].flush_model(['exchange_move_id'])
            self.env['account.partial.reconcile'].flush_model(['exchange_move_id'])
            self._cr.execute(
                """
                    SELECT DISTINCT sub.exchange_move_id
                    FROM (
                        SELECT exchange_move_id
                        FROM account_full_reconcile
                        WHERE exchange_move_id IN %s

                        UNION ALL

                        SELECT exchange_move_id
                        FROM account_partial_reconcile
                        WHERE exchange_move_id IN %s
                    ) AS sub
                """,
                [tuple(self.ids), tuple(self.ids)],
            )
            exchange_move_ids = set([row[0] for row in self._cr.fetchall()])

        for move in self:
            # 🔒 Validasi Lock Date

            company = move.company_id
            user = self.env.user
            if move.date:
                if company.fiscalyear_lock_date and move.date <= company.fiscalyear_lock_date:
                    raise UserError(_('Tidak bisa reset ke draft karena tanggal jurnal berada sebelum atau sama dengan Fiscal Year Lock Date: %s') % company.fiscalyear_lock_date)
                if not user.has_group('account.group_account_manager') and company.period_lock_date and move.date <= company.period_lock_date:
                    raise UserError(_('Tidak bisa reset ke draft karena tanggal jurnal berada sebelum atau sama dengan Period Lock Date: %s') % company.period_lock_date)

            if move.id in exchange_move_ids:
                raise UserError(_('You cannot reset to draft an exchange difference journal entry.'))
            if move.tax_cash_basis_rec_id or move.tax_cash_basis_origin_move_id:
                raise UserError(_('You cannot reset to draft a tax cash basis journal entry.'))
            if move.restrict_mode_hash_table and move.state == 'posted':
                raise UserError(_('You cannot modify a posted entry of this journal because it is in strict mode.'))
            
            # Hapus analytic line
            move.mapped('line_ids.analytic_line_ids').unlink()

        self.mapped('line_ids').remove_move_reconcile()
        self.write({'state': 'draft', 'is_move_sent': False})


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    jenis_kegiatan = fields.Selection([
        ('emkl', 'EMKL'),
        ('bongkar_muat', 'Bongkar Muat'),
        ('keagenan', 'Keagenan'),
        ('assist_tug', 'Assist Tug'),
        ('jetty_manajemen', 'Jetty Manajemen'),
        ('jasa_operasi_lainnya', 'Jasa Operasi Lainnya'),
        ('logistik', 'Logistik')
    ], string='Jenis Kegiatan', related='move_id.jenis_kegiatan', store=True)


    no_efaktur = fields.Char(related="move_id.no_efaktur", store=True, string="No. Efaktur")
    nomor_ref = fields.Char(related="move_id.nomor_ref", store=True, string="No. Ref")
    no_invoice = fields.Char(related="move_id.no_invoice", store=True, string="No. Invoice")
    nama_kapal = fields.Char(related="move_id.nama_kapal", store=True, string="Nama Kapal")
    note = fields.Char(related="move_id.note", store=True, string="Note")
    ta = fields.Date(related="move_id.ta", store=True, string="TA")
    td = fields.Date(related="move_id.td", store=True, string="TD")

    branch_id = fields.Many2one(
        'res.branch',
        string='Branch',
        related='move_id.branch_id',
        store=True,
        readonly=False  # Optional, kalau mau bisa diubah
    )

    user_branch_rk_id = fields.Many2one(
        'res.branch',
        string='User Branch RK',
        compute='_compute_user_branch_rk_id',
        store=False  # Tidak perlu disimpan di database
    )

    user_allowed_branch_ids = fields.Many2many(
        'res.branch',
        string='Include RK',
        compute='_compute_user_allowed_branch_ids',
        store=False
    )

    move_state = fields.Selection(related='move_id.state', store=True, readonly=True)
    deskripsi_tagihan = fields.Char(string='Deskripsi Tagihan')
    pajak_manual = fields.Float(string='Pajak Manual')

    @api.depends_context('uid')
    def _compute_user_branch_rk_id(self):
        user = self.env.user
        for record in self:
            record.user_branch_rk_id = user.branch_rk_id.id if user.branch_rk_id else False


    @api.depends_context('uid')
    def _compute_user_allowed_branch_ids(self):
        user = self.env.user
        branches = user.branch_ids
        if user.branch_rk_id and user.branch_rk_id not in branches:
            branches |= user.branch_rk_id
        for rec in self:
            rec.user_allowed_branch_ids = branches


    def action_duplicate_journal_item(self):
        for rec in self:
            rec = rec.with_context(check_move_validity=False)
            # line_ids = rec.copy()
            # for line in rec.move_id.line_ids:
            #     line_ids += line.copy()
            # rec.move_id.line_ids = False
            # rec.move_id.line_ids = line_ids
            rec.move_id.line_ids += rec.copy()


    # ===Fungsi Untuk Menampilkan Semua Akun R/K Berdasarkan Allowed Branch===
    # @api.model
    # def search(self, args, offset=0, limit=None, order=None, count=False):
    #     if self.env.context.get('filter_rk_by_branch_name'):
    #         branch_names = self.env.user.branch_ids.mapped('name')

    #         # Buat domain OR untuk nama cabang
    #         branch_domain = [('account_id.name', 'ilike', name) for name in branch_names]

    #         # Tambahkan "KANTOR PUSAT"
    #         branch_domain.append(('account_id.name', 'ilike', 'KANTOR PUSAT'))

    #         # Tambah juga syarat mengandung 'R/K'
    #         rk_filter = ('account_id.name', 'ilike', 'R/K')

    #         # Gabungkan semuanya: harus 'R/K' DAN (nama cabang OR kantor pusat)
    #         if len(branch_domain) > 1:
    #             combined_domain = ['|'] * (len(branch_domain) - 1) + branch_domain
    #         else:
    #             combined_domain = branch_domain

    #         # Final: R/K AND (cabang atau kantor pusat)
    #         args = [rk_filter, *combined_domain] + args

    #     return super(AccountMoveLine, self).search(args, offset=offset, limit=limit, order=order, count=count)


    # def get_rk_move_lines(self):
    #     query = """
    #         SELECT
    #             aml.id,
    #             aml.date,
    #             acc.name ->> 'en_US' AS account_name,
    #             aml.branch_id,
    #             rb.name AS branch_name,
    #             aml.debit,
    #             aml.credit
    #         FROM account_move_line aml
    #         JOIN account_account acc ON aml.account_id = acc.id
    #         LEFT JOIN res_branch rb ON aml.branch_id = rb.id
    #         WHERE acc.name ->> 'en_US' ILIKE '%R/K%' -- atau sesuai nama akun yang ingin dicari
    #         AND (aml.display_type IS NULL OR aml.display_type NOT IN ('line_section', 'line_note'));
    #     """

    #     self.env.cr.execute(query, ['%R/K%'])
    #     results = self.env.cr.fetchall()  # list of tuples [(id,), (id,), ...]
    #     line_ids = [r[0] for r in results]
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Journal Items R/K',
    #         'res_model': 'account.move.line',
    #         'view_mode': 'tree,form',
    #         'domain': [('id', 'in', line_ids)],
    #         'context': dict(self.env.context),
    #         'target': 'current',
    #     }

    # @api.model
    # def get_action_view_rk(self):
    #     line_ids = self.get_rk_move_lines()
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Journal Items R/K',
    #         'view_mode': 'tree,form',
    #         'res_model': 'account.move.line',
    #         'domain': [('id', 'in', line_ids.ids)],
    #         'context': dict(self.env.context),
    #     }
    
    
