from odoo import models, fields, api, _


class HrLeavePaidTimeOffType(models.Model):
    _name = "hr.leave.paid.timeoff.type"
    _description = "Paid Time Off Type"

    name = fields.Char("Jenis Cuti", index='trigram')