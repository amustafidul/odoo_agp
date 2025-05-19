from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime
import pytz

class CustomSequence(models.Model):
    _inherit = 'ir.sequence'

    jenis_kegiatan_id = fields.Many2one('jenis.kegiatan', string="Jenis Kegiatan")
    jenis_kegiatan_code = fields.Char(string="Jenis Kegiatan Code", compute='_compute_jenis_kegiatan_code')

    @api.depends('jenis_kegiatan_id')
    def _compute_jenis_kegiatan_code(self):
        for record in self:
            record.jenis_kegiatan_code = record.jenis_kegiatan_id.code if record.jenis_kegiatan_id else ''
    

    @api.model
    def _get_prefix_suffix(self, date=None, date_range=None):
        def _interpolate(s, d):
            return (s % d) if s else ''

        def _interpolation_dict():
            now = range_date = effective_date = datetime.now(pytz.timezone(self._context.get('tz') or 'UTC'))
            if date or self._context.get('ir_sequence_date'):
                effective_date = fields.Datetime.from_string(date or self._context.get('ir_sequence_date'))
            if date_range or self._context.get('ir_sequence_date_range'):
                range_date = fields.Datetime.from_string(date_range or self._context.get('ir_sequence_date_range'))

            # Membuat dictionary sequences
            sequences = {
                'year': '%Y', 'month': '%m', 'day': '%d', 'y': '%y', 'doy': '%j', 'woy': '%W',
                'weekday': '%w', 'h24': '%H', 'h12': '%I', 'min': '%M', 'sec': '%S'
            }

            # Ambil branch_code dari user yang login
            branch_code = self.env.user.branch_id.code if self.env.user.branch_id else 'N/A'

            # Ambil jenis_kegiatan_code dari record yang sedang dibuka
            jenis_kegiatan_code = self.jenis_kegiatan_id.code if hasattr(self, 'jenis_kegiatan_id') and self.jenis_kegiatan_id else 'N/A'

            # Tambahkan ke dictionary sequences
            sequences['branch_code'] = branch_code
            sequences['jenis_kegiatan_code'] = jenis_kegiatan_code

            # Format sequences untuk interpolasi
            res = {}
            for key, format in sequences.items():
                res[key] = effective_date.strftime(format) if key not in ['branch_code', 'jenis_kegiatan_code'] else sequences[key]
                res['range_' + key] = range_date.strftime(format) if key not in ['branch_code', 'jenis_kegiatan_code'] else sequences[key]
                res['current_' + key] = now.strftime(format) if key not in ['branch_code', 'jenis_kegiatan_code'] else sequences[key]

            return res

        self.ensure_one()
        d = _interpolation_dict()
        try:
            # Melakukan interpolasi prefix dan suffix
            interpolated_prefix = _interpolate(self.prefix, d)
            interpolated_suffix = _interpolate(self.suffix, d)
        except ValueError:
            raise UserError(_('Invalid prefix or suffix for sequence \'%s\'') % self.name)
        return interpolated_prefix, interpolated_suffix




