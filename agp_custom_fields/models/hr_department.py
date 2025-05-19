from odoo import models, fields

class HrDepartment(models.Model):
    _inherit = 'hr.department'
    
    kode = fields.Char(string='Kode Department')
