# -*- coding: utf-8 -*-
# from odoo import http


# class AgpApi(http.Controller):
#     @http.route('/agp_api/agp_api', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/agp_api/agp_api/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('agp_api.listing', {
#             'root': '/agp_api/agp_api',
#             'objects': http.request.env['agp_api.agp_api'].search([]),
#         })

#     @http.route('/agp_api/agp_api/objects/<model("agp_api.agp_api"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('agp_api.object', {
#             'object': obj
#         })
