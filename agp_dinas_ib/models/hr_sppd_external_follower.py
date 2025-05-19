from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class HrLeaveDinasExternalFollower(models.Model):
    _name = 'hr.leave.dinas.external.follower'
    _description = 'Pengikut Eksternal SPPD'
    _order = 'id asc'

    leave_dinas_id = fields.Many2one('hr.leave.dinas', string='SPPD', ondelete='cascade', required=True)
    name = fields.Char(string='Nama Pengikut', required=True)
    institution = fields.Char(string='Instansi / Lembaga')
    notes = fields.Text(string='Keterangan')