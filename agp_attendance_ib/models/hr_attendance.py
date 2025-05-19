from odoo import models, fields


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    x_keterangan_check_in = fields.Text(string='Keterangan Check In')