from odoo import api, models, _
from odoo.exceptions import UserError



class ReportAgingAPDetail(models.AbstractModel):
    _name = 'report.report_multi_branch.report_aging_ap_detail'
    _description = 'Aging AP Detail Report'


    @api.model
    def _get_report_values(self, docids, data=None):
        active_model = self.env.context.get('active_model')
        docs = self.env[active_model].browse(self.env.context.get('active_id'))
        periode = data['periode']
        lines = data['lines']
        vals = {
            'docs': docs,
            'periode': periode,
            'lines': lines,
        }
        return vals