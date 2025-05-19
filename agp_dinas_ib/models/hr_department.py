from odoo import models, fields, api


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    penanggung_jawab_ids = fields.Many2many('hr.employee', string='Penanggung Jawab')
    department_type = fields.Selection([
        ('divisi', 'Divisi'),
        ('bidang', 'Bidang'),
        ('subbidang', 'Sub Bidang')
    ], string="Jenis Department")
    biaya_sppd_role = fields.Selection([
        ('mb_umum', 'MB Umum'),
        ('kadiv_sdm_umum', 'Kadiv SDM dan Umum'),
        ('mb_keuangan', 'MB Keuangan'),
        ('kadiv_keuangan', 'Kadiv Keuangan'),
    ], string="SPPD Role Configuration")