from odoo import fields, models, api, tools, _
from odoo.exceptions import UserError
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
import babel


class AgingPosisiAPWizard(models.TransientModel):
    _name = 'aging.posisi.ap.wizard'

    periode = fields.Date(string='Periode', required=True)

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

        lines = []
        domain = [
            ('state', '=', 'posted'),
            ('move_type', '=', 'in_invoice'),
            ('payment_state', '!=', 'paid'),
        ]
        move = self.env['account.move'].search(domain)
        partner_ids = move.mapped('partner_id')
        for partner in partner_ids:
            total = sum(
                move.filtered(lambda x: x.partner_id.id == partner.id and x.invoice_date <= self.periode).mapped(
                    'amount_residual'))
            total1 = sum(move.filtered(
                lambda x: x.partner_id.id == partner.id and x.invoice_date >= self.periode and x.invoice_date <= (
                            self.periode + relativedelta(months=6))).mapped('amount_residual'))
            total2 = sum(move.filtered(lambda x: x.partner_id.id == partner.id and x.invoice_date >= (
                        self.periode + relativedelta(months=7)) and x.invoice <= (
                                                             self.periode + relativedelta(months=12))).mapped(
                'amount_residual'))
            total3 = sum(move.filtered(lambda x: x.partner_id.id == partner.id and x.invoice_date >= (
                        self.periode + relativedelta(months=13)) and x.invoice <= (
                                                             self.periode + relativedelta(months=24))).mapped(
                'amount_residual'))
            total4 = sum(move.filtered(lambda x: x.partner_id.id == partner.id and x.invoice_date >= (
                        self.periode + relativedelta(months=25)) and x.invoice <= (
                                                             self.periode + relativedelta(months=36))).mapped(
                'amount_residual'))
            total5 = sum(move.filtered(lambda x: x.partner_id.id == partner.id and x.invoice_date >= (
                        self.periode + relativedelta(months=36))).mapped('amount_residual'))
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
        data['lines'] = lines

        return self.env.ref('report_multi_branch.action_report_aging_posisi_ap').report_action(self, data=data)

    def action_xls(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/aging_posisi_ap/export/%s' % (self.id),
            'target': 'new',
        }