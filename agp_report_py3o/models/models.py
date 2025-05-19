# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class agp_report_py3o(models.Model):
#     _name = 'agp_report_py3o.agp_report_py3o'
#     _description = 'agp_report_py3o.agp_report_py3o'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
