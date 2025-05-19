from odoo import api, models, _
from odoo.exceptions import UserError



class ReportLabaRugiSummary(models.AbstractModel):
    _name = 'report.report_multi_branch.report_laba_rugi_summary'
    _description = 'Laba Rugi Report'


    @api.model
    def _get_report_values(self, docids, data=None):
        active_model = self.env.context.get('active_model')
        docs = self.env[active_model].browse(self.env.context.get('active_id'))
        vals = {
            'docs': docs,
        }
        return vals