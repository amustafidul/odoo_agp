from odoo import models, fields, api, _


class HrEmployeeStatusPajak(models.Model):
    _name = "hr.employee.status.pajak"
    _description = "Status Pajak PKWT Employee"

    name = fields.Char('Status Pajak', index='trigram')