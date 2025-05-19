from odoo import models, fields, api, _
from odoo.exceptions import UserError

from . import helpers

import re
import logging
_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    rk_bank_account_id = fields.Many2one('account.account', string='R/K or Bank Account')
    jenis_kegiatan_id = fields.Many2one('jenis.kegiatan', string='Jenis Kegiatan', required=True)
    # jenis_kegiatan_name = fields.Char(string="Jenis Kegiatan Name", compute="_compute_jenis_kegiatan_name")
    
    new_sequence = fields.Char(string='New Sequence', readonly=True, compute='_compute_new_sequence')
    note = fields.Char(string='Note')
    nomor_ref = fields.Char(string='Nomor Reference') 
    invoice_ids = fields.Many2many('account.move', string="Invoices")

    @api.depends('journal_id', 'payment_type', 'payment_method_line_id','rk_bank_account_id')
    def _compute_outstanding_account_id(self):
        for pay in self:
            if pay.payment_type == 'inbound':
                pay.outstanding_account_id = (pay.payment_method_line_id.payment_account_id
                                              or pay.journal_id.company_id.account_journal_payment_debit_account_id)
            elif pay.payment_type == 'outbound':
                pay.outstanding_account_id = (pay.payment_method_line_id.payment_account_id
                                              or pay.journal_id.company_id.account_journal_payment_credit_account_id)
            elif pay.rk_bank_account_id:
                pay.outstanding_account_id = pay.rk_bank_account_id.id
            else:
                pay.outstanding_account_id = False


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
        if 'name' not in vals:
            # Set the name using new_sequence if it's not provided in vals
            if 'new_sequence' in vals:
                vals['name'] = vals['new_sequence']
            else:
                # Compute new_sequence if not in vals
                move = super(AccountPayment, self).create(vals)
                move.write({'name': move._get_starting_sequence()})
                return move
        return super(AccountPayment, self).create(vals)


    def write(self, vals):
        for record in self:
            if record.name == '/' and 'name' not in vals:
                base_sequence = record._get_starting_sequence()

                vals['name'] = base_sequence

        return super(AccountPayment, self).write(vals)

    
    # def _get_last_sequence_domain(self, relaxed=False):
    #     self.ensure_one()
    #     if not self.date or not self.journal_id:
    #         return "WHERE FALSE", {}

    #     user_branch_code = self.env.user.branch_id.code if self.env.user.branch_id else ''
    #     move_type_prefix = 'INV' if self.move_type == 'out_invoice' else 'BILLS' if self.move_type == 'in_invoice' else ''
        
    #     # Format pencarian berdasarkan format sequence baru
    #     where_string = "WHERE journal_id = %(journal_id)s AND name != '/' AND sequence_prefix LIKE %(prefix)s"
    #     param = {
    #         'journal_id': self.journal_id.id,
    #         'prefix': f"{move_type_prefix}/{user_branch_code}/%"
    #     }
    #     is_payment = self.payment_id or self._context.get('is_payment')

    #     if not relaxed:
    #         domain = [
    #             ('journal_id', '=', self.journal_id.id), 
    #             ('id', '!=', self.id or self._origin.id), 
    #             ('name', 'not in', ('/', '', False)),
    #             ('sequence_prefix', 'ilike', f"{move_type_prefix}/{user_branch_code}")
    #         ]
            
    #         if self.journal_id.refund_sequence:
    #             refund_types = ('out_refund', 'in_refund')
    #             domain += [('move_type', 'in' if self.move_type in refund_types else 'not in', refund_types)]
    #         if self.journal_id.payment_sequence:
    #             domain += [('payment_id', '!=' if is_payment else '=', False)]
            
    #         reference_move_name = self.search(domain + [('date', '<=', self.date)], order='date desc', limit=1).name
    #         if not reference_move_name:
    #             reference_move_name = self.search(domain, order='date asc', limit=1).name
            
    #         sequence_number_reset = self._deduce_sequence_number_reset(reference_move_name)
    #         date_start, date_end = self._get_sequence_date_range(sequence_number_reset)
    #         where_string += """ AND date BETWEEN %(date_start)s AND %(date_end)s"""
    #         param['date_start'] = date_start
    #         param['date_end'] = date_end
            
    #         # Sesuaikan regex untuk format baru jika diperlukan
    #         if sequence_number_reset in ('year', 'year_range'):
    #             param['anti_regex'] = re.sub(r"\?P<\w+>", "?:", self._sequence_monthly_regex.split('(?P<seq>')[0]) + '$'
    #         elif sequence_number_reset == 'never':
    #             param['anti_regex'] = re.sub(r"\?P<\w+>", "?:", self._sequence_yearly_regex.split('(?P<seq>')[0]) + '$'

    #         if param.get('anti_regex') and not self.journal_id.sequence_override_regex:
    #             where_string += " AND sequence_prefix !~ %(anti_regex)s "

    #     if self.journal_id.refund_sequence:
    #         if self.move_type in ('out_refund', 'in_refund'):
    #             where_string += " AND move_type IN ('out_refund', 'in_refund') "
    #         else:
    #             where_string += " AND move_type NOT IN ('out_refund', 'in_refund') "
    #     elif self.journal_id.payment_sequence:
    #         if is_payment:
    #             where_string += " AND payment_id IS NOT NULL "
    #         else:
    #             where_string += " AND payment_id IS NULL "

    #     return where_string, param

    # @api.model
    # def create(self, vals):
    #     if 'name' not in vals:
    #         # Set the name using new_sequence if it's not provided in vals
    #         if 'new_sequence' in vals:
    #             vals['name'] = vals['new_sequence']
    #         else:
    #             # Compute new_sequence if not in vals
    #             move = super(AccountPayment, self).create(vals)
    #             move.write({'name': move._get_starting_sequence()})
    #             return move
    #     return super(AccountPayment, self).create(vals)

    # def write(self, vals):
    #     for record in self:
    #         # Menambahkan log untuk memeriksa nilai sebelum update
    #         _logger.info("Before Save: New Sequence = %s", record.new_sequence)
    #         result = super(AccountPayment, self).write(vals)
    #         _logger.info("After Save: New Sequence = %s", record.new_sequence)
    #         return result