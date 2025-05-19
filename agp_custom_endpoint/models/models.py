# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class agp_custom_endpoint(models.Model):
#     _name = 'agp_custom_endpoint.agp_custom_endpoint'
#     _description = 'agp_custom_endpoint.agp_custom_endpoint'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
