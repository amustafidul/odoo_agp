from odoo import models, fields


class TnaTrainingScope(models.Model):
    _name = 'tna.training.scope'
    _description = 'Master Data Lingkup Diklat/Training'
    _order = 'name'

    name = fields.Char(
        string='Nama Lingkup Diklat',
        required=True,
        copy=False,
        help="Contoh: Operasional, Keuangan, K3 Umum, Soft Skills, Leadership"
    )
    description = fields.Text(
        string='Deskripsi Tambahan'
    )

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Nama Lingkup Diklat harus unik!")
    ]