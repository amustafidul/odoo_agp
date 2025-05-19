from odoo import models, fields, api, _

import logging

_logger = logging.getLogger(__name__)


class IrCron(models.Model):
    _inherit = 'ir.cron'