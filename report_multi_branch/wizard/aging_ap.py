from odoo import fields, models, api, tools, _
from odoo.exceptions import UserError
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
import babel

class AgingAPWizard(models.TransientModel):
    _name = 'aging.ap.wizard'

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
            ('payment_state', '!=', 'paid'),
        ]
        
        if self.jenis_kegiatan_id:
            domain += [('jenis_kegiatan_id', '=', self.jenis_kegiatan_id.id)]
        
        account_move = self.env['account.move'].search(domain, order='partner_id')
        partner_ids = account_move.mapped('partner_id')
        for partner in partner_ids:
            total = total1 = total2 = total3 = total4 = total5 = 0.0
            
            move_partner = account_move.filtered(lambda x:x.partner_id.id == partner.id)
            total = sum(move_partner.mapped('amount_residual'))
            for move in move_partner:
                age = int(((self.periode - move.date).days / 365) * 12)
                if age < 6:
                    total1 += move.amount_residual
                elif age >= 7 and age <= 12:
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


        domain_line = [
            '|',
            ('move_id', '=', False),
            ('account_id.account_type', '=', 'liability_payable'),
            ('date', '<=', self.periode),
            '&',
            ('account_id.name', 'not ilike', 'Pajak'),
            ('account_id.name', 'not ilike', 'VAT'),
            ('account_id.name', 'not ilike', 'PPN'),
            ('account_id.name', 'not ilike', 'PPn')
        ]

        if self.jenis_kegiatan:
            domain_line.append(('account_id.name', 'ilike', self.jenis_kegiatan))

        move_lines = self.env['account.move.line'].search(domain_line)

        lines_by_partner = {}

        for line in move_lines:
            partner_id = line.partner_id.id
            if partner_id not in lines_by_partner:
                lines_by_partner[partner_id] = {
                    'code': line.partner_id.x_vendor_code or '',
                    'name': line.partner_id.name or '',
                    'total': 0.0,
                    'total1': 0.0,
                    'total2': 0.0,
                    'total3': 0.0,
                    'total4': 0.0,
                    'total5': 0.0,
                }

            line_age_days = int((self.periode - line.date).days)

            lines_by_partner[partner_id]['total'] += line.amount_residual
            if line_age_days <= 180:
                lines_by_partner[partner_id]['total1'] += line.amount_residual
            elif 181 <= line_age_days <= 360:
                lines_by_partner[partner_id]['total2'] += line.amount_residual
            elif 361 <= line_age_days <= 720:
                lines_by_partner[partner_id]['total3'] += line.amount_residual
            elif 721 <= line_age_days <= 1080:
                lines_by_partner[partner_id]['total4'] += line.amount_residual
            elif line_age_days > 1080:
                lines_by_partner[partner_id]['total5'] += line.amount_residual

        for partner_data in lines_by_partner.values():
            lines.append(partner_data)

        data['lines'] = lines
        
        return self.env.ref('report_multi_branch.action_report_aging_ap').report_action(self, data=data)
        
    
    def action_xls(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/aging_ap/export/%s' % (self.id),
            'target': 'new',
        }