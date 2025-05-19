from odoo import fields, api, models, tools, _
from datetime import datetime, time
import babel.dates
import logging

_logger = logging.getLogger(__name__)

class KartuNeracaWizard(models.TransientModel):
    _name = "kartu.neraca.wizard"
    _description = "Kartu Neraca Wizard"

    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    jenis_kegiatan = fields.Selection([
        ('emkl', 'EMKL'),
        ('bongkar_muat', 'Bongkar Muat'),
        ('keagenan', 'Keagenan'),
        ('assist_tug', 'Assist Tug'),
        ('jetty_manajemen', 'Jetty Manajemen'),
        ('jasa_operasi_lainnya', 'Jasa Operasi Lainnya'),
        ('logistik', 'Logistik')
    ], string='Jenis Kegiatan')
    partner_id = fields.Many2one('res.partner', string="Partner")
    account_id = fields.Many2one('account.account', string="Account", required=True, domain="[('account_type', 'not in', ['income', 'income_other', 'expense', 'expense_depreciation', 'expense_direct_cost', 'off_balance'])]")
    report_type = fields.Selection([
            ('summary', 'Summary'),
            ('detail', 'Detail')
        ], string='Report Type', required=True, default='detail')
    jenis_kegiatan_id = fields.Many2one('jenis.kegiatan', string='Jenis Kegiatan')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)


    def action_view(self):
        data = {}
        data['form'] = self.read()[0]
        
        # Format start_date and end_date
        start_date_formatted = tools.ustr(
            babel.dates.format_date(
                date=datetime.combine(self.start_date, time.min),
                format="d MMMM y",
                locale="id_ID",
            )
        )
        end_date_formatted = tools.ustr(
            babel.dates.format_date(
                date=datetime.combine(self.end_date, time.min),
                format="d MMMM y",
                locale="id_ID",
            )
        )

        data['start_date'] = start_date_formatted.upper()
        data['end_date'] = end_date_formatted.upper()
        data['account_id'] = self.account_id.code

        # Mapping untuk jenis kegiatan
        mapping = [
            ('emkl', 'EMKL'),
            ('bongkar_muat', 'Bongkar Muat'),
            ('keagenan', 'Keagenan'),
            ('assist_tug', 'Assist Tug'),
            ('jetty_manajemen', 'Jetty Manajemen'),
            ('jasa_operasi_lainnya', 'Jasa Operasi Lainnya'),
            ('logistik', 'Logistik')
        ]
        res = {key: value for key, value in mapping}
        # data['jenis_kegiatan'] = res[self.jenis_kegiatan].upper() if self.jenis_kegiatan else ''
        data['jenis_kegiatan'] = self.jenis_kegiatan_id.name.upper() if self.jenis_kegiatan_id else ''

        lines = []
        domain = [
            ('move_id.state', '=', 'posted'),
            ('move_id.move_type', 'in', ['in_invoice', 'out_invoice']),
            ('move_id.invoice_date_due', '<=', self.end_date),
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date),
        ]

        if self.jenis_kegiatan_id:
            domain += [('move_id.jenis_kegiatan_id', '=', self.jenis_kegiatan_id.id)]
        if self.partner_id:
            domain += [('move_id.partner_id', '=', self.partner_id.id)]
        if self.account_id:
            domain += [('account_id', '=', self.account_id.id)]

        # Get account.move.lines based on domain
        account_move_lines = self.env['account.move.line'].search(domain, order='date asc')
        partners = account_move_lines.mapped('move_id.partner_id')
        
        if self.report_type == 'summary':
            for partner in partners:
                total = total1 = total2 = total3 = total4 = total5 = 0.0
                
                # Filter account moves related to the partner
                move_partner = self.env['account.move'].search([
                    ('partner_id', '=', partner.id),
                    ('move_type', 'in', ['in_invoice', 'out_invoice']),
                    ('invoice_date_due', '<=', self.end_date),
                    ('date', '>=', self.start_date),
                    ('date', '<=', self.end_date),
                ])
                
                total = sum(move_partner.mapped('amount_residual'))
                for move in move_partner:
                    age = int(((self.end_date - move.date).days / 365) * 12)
                    if age < 6:
                        total1 += move.amount_residual
                    elif age >= 6 and age <= 12:
                        total2 += move.amount_residual
                    elif age >= 13 and age <= 24:
                        total3 += move.amount_residual
                    elif age >= 25 and age <= 36:
                        total4 += move.amount_residual
                    elif age > 37:
                        total5 += move.amount_residual

                lines.append({
                    'code': partner.x_vendor_code,
                    'name': partner.name,
                    'total': total,
                    'total1': total1,
                    'total2': total2,
                    'total3': total3,
                    'total4': total4,
                    'total5': total5,
                })

        else:
            for partner in partners:
                move_lines = account_move_lines.filtered(lambda l: l.move_id.partner_id.id == partner.id)
                if self.account_id:
                    move_lines = move_lines.filtered(lambda l: l.account_id.id == self.account_id.id)

                total = sum(move_lines.mapped('balance'))

                for line in move_lines:
                    move = line.move_id
                    total1 = total2 = total3 = total4 = total5 = 0.0

                    age_id_days = int((self.end_date - move.date).days)

                    partial_reconciles = self.env['account.partial.reconcile'].search([
                        '|', ('debit_move_id.move_id', '=', move.id),
                        ('credit_move_id.move_id', '=', move.id),
                        ('create_date', '<=', self.end_date)
                    ])

                    payment_ids = partial_reconciles.mapped('debit_move_id.move_id') + partial_reconciles.mapped('credit_move_id.move_id')
                    payments = self.env['account.payment'].search([('move_id', 'in', payment_ids.ids), ('date', '<=', self.end_date)])

                    residual_amount = line.balance - sum(payments.mapped('amount'))

                    if age_id_days <= 180:
                        total1 = residual_amount
                    elif 181 <= age_id_days <= 360:
                        total2 = residual_amount
                    elif 361 <= age_id_days <= 720:
                        total3 = residual_amount
                    elif 721 <= age_id_days <= 1080:
                        total4 = residual_amount
                    elif age_id_days > 1080:
                        total5 = residual_amount

                    payment_names = ', '.join(payment.name for payment in payments)
                    payment_amounts = sum(payment.amount for payment in payments)
                    payment_dates = ', '.join(payment.date.strftime('%d/%m/%Y') for payment in payments)

                    lines.append({
                        'branch': move.branch_id.name or '',
                        'partner': move.partner_id.name or '',
                        'account': line.account_id.name or '',
                        'name': move.name or '',
                        'transaction': move.transaction_ids[0].name if move.transaction_ids else '',
                        'date': move.date.strftime('%d/%m/%Y') or '',
                        'amount_total': move.amount_total or 0.0,
                        'payment_amount': payment_amounts or 0.0,
                        'payment_name': payment_names or '',
                        'payment_date': payment_dates or '',
                        'residual': residual_amount or 0.0,
                        'age': int(((self.end_date - move.date).days / 365) * 12) or '',
                        'age_id_days': age_id_days or '',
                        'narration': move.narration or '',
                        'total': total,
                        'total1': total1,
                        'total2': total2,
                        'total3': total3,
                        'total4': total4,
                        'total5': total5,
                    })

        data['lines'] = lines  

        if self.report_type == 'summary':
            return self.env.ref('report_multi_branch.action_report_kartu_neraca_summary').report_action(self, data=data)
        else:
            return self.env.ref('report_multi_branch.action_report_kartu_neraca_detail').report_action(self, data=data)
        
    def action_xls(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/kartu_neraca/export/%s' % (self.id),
            'target': 'new',
        }
