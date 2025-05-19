# -*- coding: utf-8 -*-
from odoo import models, fields, api

class Wika_Activity(models.Model):
    _inherit = 'mail.activity'

    status = fields.Selection([
        ('todo', 'To Upload'), 
        ('to_approve', 'To Approve'), 
        ('approved', 'Approved')
    ], string='Act Status')
    state = fields.Selection([
        ('overdue', 'Overdue'),
        ('today', 'Today'),
        ('planned', 'Planned')
    ], 'State', compute='_compute_state', store=True)
    is_expired = fields.Boolean(string='Is Expired', compute='_compute_is_expired')
    
    @api.depends('date_deadline')
    def _compute_is_expired(self):
        for record in self:
            if record.date_deadline and record.date_deadline < fields.Date.today():
                record.is_expired = True
            else:
                record.is_expired = False