from odoo import http
from odoo.http import request

class UserInfoController(http.Controller):

    @http.route('/api/user/groups', type='json', auth='user')
    def get_user_groups(self):
        user = request.env.user

        is_eligible_for_konsolidasi = False
        groups = user.groups_id
        if groups:
            for group in groups:
                if 'Board of Director' in group.name:
                    is_eligible_for_konsolidasi = True

        return {
            'id': user.id,
            'name': user.name,
            'groups_id': user.groups_id.mapped('name'),
            'is_eligible': is_eligible_for_konsolidasi,
        }
