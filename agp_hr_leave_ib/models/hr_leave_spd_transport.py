from odoo import models, fields, api, _


class HrLeaveSpdTransport(models.Model):
    _name = "hr.leave.spd.transport"
    _description = "Transport for SPD Leave"

    name = fields.Char("Transport", index='trigram')