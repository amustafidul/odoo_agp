from odoo import models, fields, api, _


class HrEmployeeFungsiPenugasan(models.Model):
    _name = "hr.employee.fungsi.penugasan"
    _description = "Fungsi Penugasan"

    name = fields.Char("Fungsi Penugasan", index='trigram', required=True)
    currency_id = fields.Many2one(
        'res.currency', string="Currency",
        default=lambda self: self.env.company.currency_id,
        readonly=True
    )
    nilai_koefisien = fields.Float(required=True)
    nilai_tunjangan = fields.Monetary()