from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class OdooPayrollGrade(models.Model):
    _name = 'odoo.payroll.grade'
    _description = 'Payroll Grade'

    name = fields.Char(compute='_compute_name', store=True)
    grade = fields.Char('Grade', required=True)
    grade_type = fields.Selection([
        ('direktur_utama', 'Direktur Utama'),
        ('direktur', 'Direktur'),
        ('komisaris_utama', 'Komisaris Utama'),
        ('komisaris', 'Komisaris'),
        ('sekdekom', 'SekDekom'),
        ('komite_dekom', 'Komite Dekom'),
    ], string="Grade Type")
    inverse_grade = fields.Char('Inverse Grade', required=True)
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    grade_amount = fields.Monetary('Amount', required=True)
    amount_fasilitas_kendaraan_dinas = fields.Monetary(
        string="Fasilitas Kendaraan Dinas"
    )
    amount_tunjangan_komunikasi = fields.Monetary(
        string="Tunjangan Komunikasi"
    )
    amount_tunjangan_perumahan = fields.Monetary(
        string="Tunjangan Perumahan"
    )
    amount_tunjangan_transport_dekom = fields.Monetary(
        string="Tunjangan Transport Dekom"
    )
    subject_matter_expert_amount = fields.Monetary('Subject Matter Expert')
    asistensi_pajak = fields.Monetary('Asistensi Pajak')
    matter_expert_asistensi_pajak_amount = fields.Monetary('Subject Matter Expert dan Asistensi Pajak')
    tahun = fields.Char(compute='_compute_tahun')

    @api.depends('create_date')
    def _compute_tahun(self):
        for rec in self:
            if rec.create_date:
                dt = fields.Datetime.from_string(rec.create_date)
                rec.tahun = str(dt.year)
            else:
                rec.tahun = ''

    @api.depends('grade')
    def _compute_name(self):
        self.name = 'New'
        for rec in self:
            rec.name = 'Grade ' + rec.grade if rec.grade else 'New'