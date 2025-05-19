from odoo import models, fields, api, _


class NotaDinasDisposisiWizard(models.TransientModel):
    _name = 'nota.dinas.disposisi.wizard'
    _description = 'Wizard Input Disposisi Nota Dinas'

    nota_dinas_id = fields.Many2one('nota.dinas', string='Nota Dinas', readonly=True)
    disposisi_text = fields.Text(string='Disposisi', required=True)
    approval_level = fields.Selection([
        ('dirop', 'Direktur Operasional'),
        ('dirkeu', 'Direktur Keuangan'),
        ('dirut', 'Direktur Utama')
    ], string="Tingkat Persetujuan", readonly=True)

    def action_submit_disposisi(self):
        self.ensure_one()
        if self.nota_dinas_id:
            if self.approval_level == 'dirop':
                self.nota_dinas_id.write({
                    'disposisi_dirop_desc': self.disposisi_text
                })
                self.nota_dinas_id.action_approve_direktur_operasional()
            elif self.approval_level == 'dirkeu':
                self.nota_dinas_id.write({
                    'disposisi_dirkeu_desc': self.disposisi_text
                })
                self.nota_dinas_id.action_approve_direktur_keuangan()
            elif self.approval_level == 'dirut':
                self.nota_dinas_id.write({
                    'disposisi_dirut_desc': self.disposisi_text
                })
                self.nota_dinas_id.action_approve_direktur_utama()
        return {'type': 'ir.actions.act_window_close'}