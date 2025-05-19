from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class UMKRegion(models.Model):
    _name = 'umk.region'
    _description = 'Wilayah/Cabang UMK'

    name = fields.Char(string="Nama Wilayah/Cabang", required=True)
    company_id = fields.Many2one('res.company', string="Company", required=True)


class UMKMaster(models.Model):
    _name = 'umk.master'
    _description = 'Master Data UMK'

    def _get_year_selection(self):
        """Menghasilkan pilihan tahun dari tahun 2023 hingga 15 tahun mendatang."""
        start_year = 2023
        return [(str(year), str(year)) for year in range(start_year, start_year + 16)]

    name = fields.Char(compute='_compute_name', store=True)
    hr_branch_id = fields.Many2one('hr.branch', string='Keterangan', required=True)
    region_id = fields.Many2one('umk.region')
    sub_region_id = fields.Many2one('hr.employee.unit.penempatan', string="Wilayah/Cabang")
    province_id = fields.Many2one('umk.province', string='Provinsi', required=True)
    year_from = fields.Selection(selection='_get_year_selection', string="Tahun Dari", required=True)
    year_to = fields.Selection(selection='_get_year_selection', string="Tahun Sampai", required=True)
    umk_amount_from = fields.Float(string="UMK Sebelumnya", required=True, currency_field='currency_id')
    umk_amount_to = fields.Float(string="UMK Saat Ini", required=True, currency_field='currency_id')
    increase_amount = fields.Float(string="Kenaikan (Rp)", compute="_compute_increase", currency_field='currency_id')
    increase_percentage = fields.Float(string="Kenaikan (%)", compute="_compute_increase")
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', related='region_id.company_id', string="Company", readonly=True)

    @api.depends('hr_branch_id')
    def _compute_name(self):
        self.name = ''
        for rec in self:
            rec.name = rec.hr_branch_id.name

    @api.depends('umk_amount_from', 'umk_amount_to')
    def _compute_increase(self):
        for rec in self:
            rec.increase_amount = 0.0
            rec.increase_percentage = 0.0
            if rec.umk_amount_from and rec.umk_amount_to:
                rec.increase_amount = rec.umk_amount_to - rec.umk_amount_from
                rec.increase_percentage = (rec.increase_amount / rec.umk_amount_from) * 100 if rec.umk_amount_from else 0

    @api.constrains('year_from', 'year_to')
    def _check_year_range(self):
        for record in self:
            if record.year_from > record.year_to:
                raise ValidationError(
                    "Kesalahan pada Periode (Tahun):\n"
                    "Mohon pastikan bahwa tahun awal periode lebih kecil atau sama dengan tahun akhir."
                )


class Province(models.Model):
    _name = 'umk.province'
    _description = 'Provinsi'

    name = fields.Char('Provinsi', required=True)

    @api.constrains('name')
    def _check_unique_name(self):
        names = {}
        for record in self:
            names.setdefault(record.name, []).append(record.id)
        for name, rec_ids in names.items():
            existing_records = self.search([
                ('name', 'ilike', name),
                ('id', 'not in', rec_ids)
            ])
            if existing_records:
                raise ValidationError(f'Provinsi "{name}" sudah ada. Harap gunakan nama yang berbeda.')