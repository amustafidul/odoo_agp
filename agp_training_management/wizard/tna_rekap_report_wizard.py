from odoo import models, fields, api


class TnaRekapReportWizard(models.TransientModel):
    _name = 'tna.rekap.report.wizard'
    _description = 'Wizard Laporan Rekapitulasi TNA'

    period_id = fields.Many2one(
        'tna.period',
        string='Periode TNA',
        required=True,
        help="Pilih periode TNA yang ingin direkap."
    )
    branch_ids = fields.Many2many(
        'res.branch',
        string='Cabang',
        help="Pilih cabang tertentu atau biarkan kosong untuk semua cabang."
    )
    department_ids = fields.Many2many(
        'hr.department',
        string='Divisi',
        help="Pilih divisi tertentu atau biarkan kosong untuk semua divisi."
    )
    # status_proposed_training = fields.Selection([
    #     ('approved', 'Disetujui'),
    #     ('realized', 'Sudah Direalisasi')
    # ], string="Status Usulan Training", default='realized')


    def action_print_xlsx_report(self):
        self.ensure_one()
        data = {
            'period_id': self.period_id.id,
            'branch_ids': self.branch_ids.ids,
            'department_ids': self.department_ids.ids,
            # 'status_proposed_training': self.status_proposed_training,
        }
        return self.env.ref('agp_training_management.action_report_tna_rekap_xlsx').report_action(self, data=data)