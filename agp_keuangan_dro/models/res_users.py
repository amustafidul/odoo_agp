from odoo import models, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def cron_assign_maker_common_groups(self):
        group_maker_id = self.env.ref('agp_keuangan_dro.group_budgetting_maker_branch', raise_if_not_found=False)
        if not group_maker_id:
            return

        users = self.search([])
        for user in users:
            if user.level == 'maker' or user.level == 'cabang':
                user.write({
                    'groups_id': [(4, group_maker_id.id)]
                })

    @api.model
    def cron_assign_bod_groups(self):
        group_bod_id = self.env.ref('agp_keuangan_dro.group_board_of_director', raise_if_not_found=False)
        if not group_bod_id:
            return

        users = self.search([])
        for user in users:
            if user.level == 'bod':
                user.write({
                    'groups_id': [(4, group_bod_id.id)]
                })
            
            elif user.level == 'umum':
                user.write({
                    'groups_id': [(3, group_bod_id.id)]
                })

    @api.model
    def cron_assign_usaha_groups(self):
        group_item_usaha_id = self.env.ref('agp_keuangan_dro.group_item_usaha', raise_if_not_found=False)
        if not group_item_usaha_id:
            return

        users = self.search([])
        for user in users:
            if user.level == 'usaha':
                user.write({
                    'groups_id': [(4, group_item_usaha_id.id)]
                })

    @api.model
    def cron_assign_umum_groups(self):
        group_item_umum_id = self.env.ref('agp_keuangan_dro.group_item_umum', raise_if_not_found=False)
        if not group_item_umum_id:
            return

        users = self.search([])
        for user in users:
            if user.level == 'umum':
                user.write({
                    'groups_id': [(4, group_item_umum_id.id)]
                })

    @api.model
    def cron_assign_kadiv_groups(self):
        group_kadiv_id = self.env.ref('agp_keuangan_dro.group_division_head', raise_if_not_found=False)
        if not group_kadiv_id:
            return

        users = self.search([])
        for user in users:
            if 'yulman' in user.login or 'parisia' in user.login:
                user.write({
                    'groups_id': [(4, group_kadiv_id.id)]
                })
