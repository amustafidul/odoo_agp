from odoo import fields, api, models, tools, _
from odoo.exceptions import ValidationError
from datetime import datetime, time
import babel

class HutangPiutangWizard(models.Model):
    _name = "hutang.piutang.wizard"
    _description = "Kartu Hutang/Piutang Wizard"
    
    jenis_kartu = fields.Selection([
        ('hutang', 'Hutang'),
        ('piutang', 'Piutang')
    ], string='Jenis Kartu', required=True)
    partner_ids = fields.Many2many('res.partner', string="Partner")
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
        data['jenis_kartu'] = self.jenis_kartu
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
        # today = date.now()
        domain = [
            ('state', '=', 'posted'),
            ('move_type', '=', 'out_invoice' if self.jenis_kartu == 'piutang' else 'in_invoice'),
            ('payment_state', '!=', 'paid'),
        ]
        
        if self.jenis_kegiatan_id:
            domain += [('jenis_kegiatan_id', '=', self.jenis_kegiatan_id.id)]
        if self.partner_ids:
            domain += [('partner_id', 'in', self.partner_ids.ids)]
        
        account_move = self.env['account.move'].search(domain, order='partner_id')
        partner_ids = self.partner_ids or account_move.mapped('partner_id')
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
                    'branch': move.branch_id.name or '',
                    'partner': move.partner_id.name or '',
                    'name': move.name or '',
                    'transaction': move.transaction_ids[0].name if move.transaction_ids else '',
                    'date': move.date.strftime('%d/%m/%Y') or '',
                    'amount_total': move.amount_total or 0.0,
                    'payment_amount': move.payment_ids.mapped('amount') or 0.0,
                    'payment_name': move.payment_ids.mapped('name') or '',
                    'payment_date': move.payment_ids.mapped('date') or '',
                    'residual': move.amount_residual or 0.0,
                    'narration': move.narration or '',
                    'total': total,
                    'total1': total1,
                    'total2': total2,
                    'total3': total3,
                    'total4': total4,
                    'total5': total5,
                })
        data['lines'] = lines
        
        return self.env.ref('report_multi_branch.action_report_hutang_piutang').report_action(self, data=data)

    def action_xls(self):
        if not self.jenis_kartu:
            raise ValidationError(_("Mohon pilih jenis kartu terlebih dahulu."))
        
        return {
            'type': 'ir.actions.act_url',
            'url': '/hutang_piutang/export/%s' % (self.id),
            'target': 'new',
        }