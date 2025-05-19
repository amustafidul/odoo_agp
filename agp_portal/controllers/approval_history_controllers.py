# -- coding: utf-8 --
from odoo import http
from odoo.http import request

class AgpPortal(http.Controller):
    @http.route('/rkap/approvals/<int:record_id>', auth='none', type='http', website=False)
    def rkap_approvals(self, record_id, **kw):
        record = request.env['account.keuangan.rkap'].sudo().browse(record_id)

        # if not record.exists():
        #     return request.not_found()

        return request.render('agp_portal.rkap_approvals_template', {
            'record': record,
            'approval_lines': record.history_approval_ids,
        })