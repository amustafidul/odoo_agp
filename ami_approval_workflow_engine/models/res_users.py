from odoo import models, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def cron_assign_maker_groups(self):
        group_admin = self.env.ref('ami_approval_workflow_engine.group_approval_admin', raise_if_not_found=False)
        group_viewer = self.env.ref('ami_approval_workflow_engine.group_approval_viewer', raise_if_not_found=False)

        if not (group_admin and group_viewer):
            return

        users = self.search([])
        for user in users:
            if user.level:
                user.write({
                    'groups_id': [(4, group_admin.id), (4, group_viewer.id)]
                })
            else:
                user.write({
                    'groups_id': [(3, group_admin.id), (3, group_viewer.id)]
                })