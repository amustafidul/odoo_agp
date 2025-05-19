from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

import datetime
import calendar


class HrEmployeeKoperasi(models.Model):
    _name = 'hr.employee.koperasi'
    _description = 'Koperasi Employee'

    name = fields.Char('Deskripsi')
    jenis_koperasi = fields.Selection([
        ('one_time', 'One Time'),
        ('recurring', 'Recurring'),
        ('periodic', 'Periodic')
    ], string='Jenis Koperasi', required=True)
    jenis_simpanan = fields.Selection([
        ('sp', 'Simpanan Pokok'),
        ('sw', 'Simpanan Wajib'),
        ('pinjaman_koperasi', 'Pinjaman Koperasi')
    ], string='Jenis Simpanan', required=True)
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    amount = fields.Monetary('Amount', required=True)
    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date('End Date')

    employee_id = fields.Many2one('hr.employee', string='Employee', ondelete='cascade')
    agunan_ids = fields.One2many('hr.employee.koperasi.agunan', 'koperasi_id', string="Agunan")

    @api.onchange('start_date', 'end_date', 'jenis_simpanan')
    def _compute_auto_generate_agunan(self):
        for rec in self:
            if rec.jenis_simpanan == 'pinjaman_koperasi' and rec.start_date and rec.end_date:
                rec.agunan_ids.unlink()
                start = rec.start_date
                end = rec.end_date

                agunan_vals = []
                while start <= end:
                    agunan_vals.append((0, 0, {
                        'name': start.strftime('%B %Y'),
                        'amount': 0.0
                    }))
                    start += relativedelta(months=1)

                rec.update({'agunan_ids': agunan_vals})


class HrEmployeeKoperasiAgunan(models.Model):
    _name = 'hr.employee.koperasi.agunan'
    _description = 'Agunan Koperasi Employee'

    name = fields.Char('Bulan', required=True)
    start_date = fields.Date('Start Date', compute='_compute_date_range', store=True)
    end_date = fields.Date('End Date', compute='_compute_date_range', store=True)
    amount = fields.Monetary('Amount', default=0.0)
    koperasi_id = fields.Many2one('hr.employee.koperasi', string="Koperasi", ondelete='cascade')
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='koperasi_id.currency_id',
        readonly=True
    )

    @api.constrains('amount')
    def _check_total_agunan_amount(self):
        for rec in self:
            if rec.koperasi_id:
                total_agunan = sum(rec.koperasi_id.agunan_ids.mapped('amount'))
                if total_agunan > rec.koperasi_id.amount:
                    raise ValidationError(_("Total jumlah agunan tidak boleh melebihi amount pada koperasi!"))

    @api.depends('name')
    def _compute_date_range(self):
        for rec in self:
            try:
                dt = datetime.datetime.strptime(rec.name, '%B %Y')
                rec.start_date = dt.date().replace(day=1)
                last_day = calendar.monthrange(dt.year, dt.month)[1]
                rec.end_date = dt.date().replace(day=last_day)
            except Exception:
                rec.start_date = False
                rec.end_date = False