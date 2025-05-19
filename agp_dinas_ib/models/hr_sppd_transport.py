from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class HrSppdTransport(models.Model):
    _name = "hr.sppd.transport"
    _description = "Transport SPPD"

    name = fields.Char('Transport', required=True)