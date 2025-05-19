from odoo import models, api


class EmployeeReport(models.AbstractModel):
    _name = 'report.agp_employee_ib.employee_report_template'
    _description = 'Employee Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['hr.employee'].browse(docids)
        return {
            'doc_ids': docs.ids,
            'doc_model': 'hr.employee',
            'docs': docs,
            'data': data,
        }