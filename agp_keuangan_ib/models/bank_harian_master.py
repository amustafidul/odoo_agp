from odoo import models, fields, api, _
import babel.dates
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math


import base64
import io
import xlsxwriter


class BankHarianMaster(models.Model):
    _name = 'account.keuangan.bank.harian.master'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Bank Harian Master'

    name = fields.Char(string='Bank')