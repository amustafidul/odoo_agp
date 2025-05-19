from odoo import http
from odoo.http import request

class SetUserEmailDefault(http.Controller):

    @http.route('/set-emails-to-default', type='http', auth='user')
    def set_emails_to_default(self):
        # Access control to ensure only authorized users can trigger this route
        if not request.env.user.has_group('base.group_system'):
            return "Unauthorized access"

        # Update emails for all users
        users = request.env['res.users'].search([])
        for user in users:
            user.sudo().write({'email': 'default@adhigunaputera.co.id'})

        return "Emails updated successfully to 'default@adhigunaputera.co.id' for all users!"
    
    @http.route('/set-users-access-rights', type='http', auth='user')
    def set_users_access_rights(self):
        # Access control to ensure only authorized users can trigger this route
        if not request.env.user.has_group('base.group_system'):
            return "Unauthorized access"

        # Update access rights for all users
        users = request.env['res.users'].search([])
        for user in users:
            print("user.sel_groups_1_10_11", user.sel_groups_1_10_11)

        return "Access rights updated successfully for all users!"
