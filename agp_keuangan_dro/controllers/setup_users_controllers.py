# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class ControllerSetupUserApprovalAnggaran(http.Controller):

    @http.route('/api/set-all-approval-anggaran', methods=['GET'], auth='public', type='http')
    def set_all_approval_anggaran(self):
        target_levels = [False, 'maker', 'cabang', 'anggaran', 'keuangan', 'bod', None]

        users = request.env['res.users'].sudo().search([
            ('level', 'in', target_levels),
            ('id', 'not in', [1, 2])
        ])
        
        group_xml_ids = [
            'agp_keuangan_dro.group_rkap_header',
            'agp_keuangan_dro.group_kkhc_header',
        ]
        
        groups = []
        for xml_id in group_xml_ids:
            try:
                group = request.env.ref(xml_id).sudo()
                if group:
                    groups.append(group)
            except ValueError:
                continue

        for user in users:
            user.sudo().write({'groups_id': [(4, group.id) for group in groups]})
        
        # return {'status': 'success', 'message': 'Groups assigned successfully', 'updated_users': len(users)}
        return f"Groups assigned successfully! Updated_users': {len(users)}."
