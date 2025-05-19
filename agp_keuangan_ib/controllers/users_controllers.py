from odoo import http
from odoo.http import request, Response
import json

class UserLevelController(http.Controller):

    @http.route('/api/anggaran/user_level', type='json', auth="public", methods=['POST'], website=True)
    def get_user_level(self, **kwargs):
        request_body = request.get_json_data()
        if request_body:
            try:
                uid = request_body['uid']
                # req_type = data.get('req_type')  # Can be logged or used later if needed

                if not uid:
                    return Response(json.dumps({'error': 'UID not provided'}), status=400, content_type='application/json')

                user = request.env['res.users'].sudo().browse(uid)
                
                if not user.exists():
                    return Response(json.dumps({'error': 'User not found'}), status=500, content_type='application/json')

                res = {
                    'status': 200,
                    'message': "Your request is valid and successfully processed!",
                    # 'level': user.level
                    'data': {
                        'name': user.name,
                        'id': user.id,
                        'NIP': user.login,
                        'branch_id': user.branch_id.id,
                        'branch_name': user.branch_id.name,
                        'level': user.level
                    }
                }
                # return Response(json.dumps(res), status=200, content_type='application/json')
                # return json.dumps(res)
                return res

            except Exception as e:
                return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')
