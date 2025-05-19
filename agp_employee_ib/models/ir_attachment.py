from odoo import models, fields, api, _


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    related_record_id = fields.Many2one('hr.employee.histori.jabatan', string='Related Record')