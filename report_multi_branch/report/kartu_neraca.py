from odoo import api, models, _

class KartuNeracaSummary(models.AbstractModel):
    _name = 'report.report_multi_branch.report_kartu_neraca_summary'
    _description = 'Kartu Neraca'


    @api.model
    def _get_report_values(self, docids, data=None):
        active_model = self.env.context.get('active_model')
        docs = self.env[active_model].browse(self.env.context.get('active_id'))
        lines = data['lines']
        start_date = data['start_date']
        end_date = data['end_date']
        vals = {
            'docs': docs,
            'start_date': start_date,
            'end_date': end_date,
            'lines': lines,
        }
        return vals

class KartuNeracaDetail(models.AbstractModel):
    _name = 'report.report_multi_branch.report_kartu_neraca_detail'
    _description = 'Kartu Neraca'


    @api.model
    def _get_report_values(self, docids, data=None):
        active_model = self.env.context.get('active_model')
        docs = self.env[active_model].browse(self.env.context.get('active_id'))
        lines = data['lines']
        start_date = data['start_date']
        end_date = data['end_date']
        vals = {
            'docs': docs,
            'start_date': start_date,
            'end_date': end_date,
            'lines': lines,
        }
        return vals
