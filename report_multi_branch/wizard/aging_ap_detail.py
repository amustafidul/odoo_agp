from odoo import fields, models, api, tools, _
from odoo.exceptions import UserError
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
import babel

class AgingAPDetailWizard(models.TransientModel):
    _name = 'aging.ap.detail.wizard'

    periode = fields.Date(string='Periode', required=True)
    jenis_kegiatan = fields.Selection([
        ('emkl', 'EMKL'),
        ('bongkar_muat', 'Bongkar Muat'),
        ('keagenan', 'Keagenan'),
        ('assist_tug', 'Assist Tug'),
        ('jetty_manajemen', 'Jetty Manajemen'),
        ('jasa_operasi_lainnya', 'Jasa Operasi Lainnya'),
        ('logistik', 'Logistik')
    ], string='Jenis Kegiatan')
    jenis_kegiatan_id = fields.Many2one('jenis.kegiatan', string='Jenis Kegiatan')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    partner_id = fields.Many2one('res.partner', string="Partner")

    def action_view(self):
        data = {}
        data['form'] = self.read()[0]
        periode = tools.ustr(
            babel.dates.format_date(
                date=datetime.combine(self.periode, time.min),
                format="d MMMM y",
                locale="id_ID",
            )
        )
        data['periode'] = periode.upper()

        res = {}
        mapping = [
            ('emkl', 'EMKL'),
            ('bongkar_muat', 'Bongkar Muat'),
            ('keagenan', 'Keagenan'),
            ('assist_tug', 'Assist Tug'),
            ('jetty_manajemen', 'Jetty Manajemen'),
            ('jasa_operasi_lainnya', 'Jasa Operasi Lainnya'),
            ('logistik', 'Logistik')
        ]
        for key, value in dict(mapping).items():
            res[key] = value
        # data['jenis_kegiatan'] = res[self.jenis_kegiatan].upper() if self.jenis_kegiatan else ''
        data['jenis_kegiatan'] = self.jenis_kegiatan_id.name.upper() if self.jenis_kegiatan_id else ''

        lines = []
        domain = [
            ('state', '=', 'posted'),
            ('move_type', '=', 'in_invoice'),
            ('invoice_date_due', '<=', self.periode),
            ('payment_state', '!=', 'paid'),
        ]
        
        if self.jenis_kegiatan_id:
            domain += [('jenis_kegiatan_id', '=', self.jenis_kegiatan_id.id)]
        if self.partner_id:
            domain += [('partner_id', '=', self.partner_id.id)]
            
        account_move = self.env['account.move'].search(domain, order='date asc')
        partner_id = self.partner_id or account_move.mapped('partner_id')
        
        for partner in partner_id:
            move_partner = account_move.filtered(lambda x: x.partner_id.id == partner.id)
            total = sum(move_partner.mapped('amount_residual'))

            for move in move_partner:

                total1 = total2 = total3 = total4 = total5 = 0.0

                age_id_days = int((self.periode - move.date).days)
                
                partial_reconciles = self.env['account.partial.reconcile'].search([
                    '|', ('debit_move_id.move_id', '=', move.id),
                    ('credit_move_id.move_id', '=', move.id),
                    ('create_date', '<=', self.periode)
                ])

                payment_ids = partial_reconciles.mapped('debit_move_id.move_id') + partial_reconciles.mapped('credit_move_id.move_id')
                payments = self.env['account.payment'].search([('move_id', 'in', payment_ids.ids), ('date', '<=', self.periode)])
                
                residual_amount = move.amount_total - sum(payments.mapped('amount'))

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
                    'name': move.name or '',
                    'transaction': move.transaction_ids[0].name if move.transaction_ids else '',
                    'date': move.date.strftime('%d/%m/%Y') or '',
                    'amount_total': move.amount_total or 0.0,
                    'payment_amount': payment_amounts or 0.0,
                    'payment_name': payment_names or '',
                    'payment_date': payment_dates or '',
                    'residual': residual_amount or 0.0,
                    'age': int(((self.periode - move.date).days / 365) * 12) or '',
                    'age_id_days': age_id_days or '',
                    'narration': move.narration or '',
                    'total': total,
                    'total1': total1,
                    'total2': total2,
                    'total3': total3,
                    'total4': total4,
                    'total5': total5,
                })

        # Proses data dari account.move.line yang tidak memiliki move_id
        domain_line = [
            '|',
            # ('move_id', '!=', move.id),
            ('move_id', '=', False),
            ('account_id.account_type', '=', 'liability_payable'),
            ('date', '<=', self.periode),
            '&',  # Kondisi AND untuk pengecualian nama-nama akun
            ('account_id.name', 'not ilike', 'Pajak'),
            ('account_id.name', 'not ilike', 'VAT'),
            ('account_id.name', 'not ilike', 'PPN'),
            ('account_id.name', 'not ilike', 'PPn')
        ]

        # Tambahkan filter untuk partner_id jika diisi
        if self.partner_id:
            domain_line.append(('partner_id', '=', self.partner_id.id))

        # Tambahkan filter untuk jenis_kegiatan jika diisi
        if self.jenis_kegiatan:
            domain_line.append(('account_id.name', 'ilike', self.jenis_kegiatan))

        move_lines = self.env['account.move.line'].search(domain_line)
        
        for line in move_lines:

            line_total1 = line_total2 = line_total3 = line_total4 = line_total5 = 0.0

            line_age_id_days = int((self.periode - line.date).days)

            if line_age_id_days <= 180:
                line_total1 = line.amount_residual
            elif 181 <= line_age_id_days <= 360:
                line_total2 = line.amount_residual
            elif 361 <= line_age_id_days <= 720:
                line_total3 = line.amount_residual
            elif 721 <= line_age_id_days <= 1080:
                line_total4 = line.amount_residual
            elif line_age_id_days > 1080:
                line_total5 = line.amount_residual

            lines.append({
                'branch': line.branch_id.name or '',
                'partner': line.partner_id.name or '',
                'name': line.name or '',
                'transaction': '',  # No transaction for lines without move_id
                'date': line.date.strftime('%d/%m/%Y') or '',
                'amount_total': 0.0,  # No total amount for lines without move_id
                'payment_amount': 0.0,  # No payment amount for lines without move_id
                'payment_name': '',  # No payment name for lines without move_id
                'payment_date': '',  # No payment date for lines without move_id
                'residual': line.amount_residual or 0.0,
                'age': int(((self.periode - line.date).days / 365) * 12) or '',
                'age_id_days': line_age_id_days or '',
                'narration': '',
                'total': 0.0,  # No total for lines without move_id
                'total1': line_total1,
                'total2': line_total2,
                'total3': line_total3,
                'total4': line_total3,
                'total5': line_total5,
            })

        data['lines'] = lines
        
        return self.env.ref('report_multi_branch.action_report_aging_ap_detail').report_action(self, data=data)
        
    
    def action_xls(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/aging_ap_detail/export/%s' % (self.id),
            'target': 'new',
        }