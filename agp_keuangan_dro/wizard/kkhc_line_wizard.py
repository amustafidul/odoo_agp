from odoo import fields, models
from odoo.exceptions import ValidationError


class KkhcLineWizard(models.TransientModel):
    _name = 'account.keuangan.kkhc.line.wizard'
    _description = 'Approve KKHC Item by KaDiv'

    kkhc_line_ids = fields.Many2many(
        'account.keuangan.kkhc.line',
        'kkhc_line_wizard_rel',
        'wizard_id', 'line_id',
        string="KKHC Lines"
    )

    def action_approve_item_kkhc_kepala_divisi(self):
        if self.env.user.level not in ['usaha', 'umum']:
            raise ValidationError('Anda tidak berwenang untuk meng-approve Item KKHC sebagai Kepala Divisi!')
        
        kkhc_line_ids = self.env.context.get('default_kkhc_line_ids')
        if kkhc_line_ids:
            kkhc_ids = set()

            for line in self.env['account.keuangan.kkhc.line'].browse(kkhc_line_ids):
                line.write({'is_approved_by_divs': True})
                if line.kkhc_id:
                    kkhc_ids.add(line.kkhc_id.id)

            kkhc_records = self.env['account.keuangan.kkhc'].browse(list(kkhc_ids))
            for kkhc in kkhc_records:
                kkhc.create_monitoring_lines()

        return {'type': 'ir.actions.act_window_close'}