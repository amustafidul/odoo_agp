from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    department_role = fields.Selection([
        ('manager', 'Kepala Department/Divisi'),
        ('manager_bidang', 'Manajer Bidang'),
        ('penanggung_jawab_1', 'Penanggung Jawab 1'),
        ('penanggung_jawab_2', 'Penanggung Jawab 2'),
    ])
    token = fields.Text()