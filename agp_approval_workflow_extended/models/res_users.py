from odoo import models, fields, api

class ResUsersInheritAGP(models.Model):
    _inherit = 'res.users'

    level = fields.Selection([
        ('maker', 'Maker'),
        ('cabang', 'Approval Cabang'),
        ('usaha', 'Approval Usaha'),
        ('umum', 'Approval Umum & Admin'),
        ('anggaran', 'Approval Anggaran'),
        ('keuangan', 'Approval Keuangan'),
        ('bod', 'Approval BOD')
    ], string='Role Level', store=True)

    bod_level = fields.Selection([
        ('3', '3'),
        ('2', '2'),
        ('1', '1')
    ], string='Tingkatan Board of Director')

    def write(self, vals):
        """Override write() to manage user groups dynamically when level changes."""
        res = super(ResUsersInheritAGP, self).write(vals)

        if 'level' in vals:
            group_usaha = self.env.ref('agp_keuangan_dro.group_item_usaha', raise_if_not_found=False)
            group_umum = self.env.ref('agp_keuangan_dro.group_item_umum', raise_if_not_found=False)

            for user in self:
                if group_usaha and group_umum:
                    if user.level == 'usaha':
                        user.groups_id = [(4, group_usaha.id), (3, group_umum.id)]  
                    elif user.level == 'umum':
                        user.groups_id = [(4, group_umum.id), (3, group_usaha.id)]
                    else:
                        user.groups_id = [(3, group_usaha.id), (3, group_umum.id)]

        return res
