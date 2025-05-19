from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrEmployeeHukuman(models.Model):
    _name = "hr.employee.hukuman"
    _description = "Employee (Hukuman)"

    sequence = fields.Integer('Seq')
    name = fields.Char('NIK')
    nip = fields.Char('NIP')
    employee_name = fields.Char('Nama Pegawai')
    sk_doc_attachment = fields.Binary('SK Document', attachment=True)
    sk_attachment_id = fields.Many2many('ir.attachment', string='SK Document', attachment=True)
    sk_number = fields.Char('No. SK')
    sk_filename = fields.Char('Filename SK')
    date_start = fields.Datetime('Tanggal Mulai')
    date_end = fields.Datetime('Tanggal Selesai')
    masa_hukuman = fields.Char('Masa Hukuman', compute='_compute_masa_hukuman', store=True)

    @api.depends('date_start', 'date_end')
    def _compute_masa_hukuman(self):
        for record in self:
            if record.date_start and record.date_end:
                start_datetime = fields.Datetime.from_string(record.date_start)
                end_datetime = fields.Datetime.from_string(record.date_end)
                duration = (end_datetime - start_datetime).total_seconds()

                days = duration // (24 * 3600)
                hours = (duration % (24 * 3600)) // 3600
                minutes = (duration % 3600) // 60
                seconds = duration % 60

                if days >= 0:
                    parts = []
                    if days > 0:
                        parts.append(f"{int(days)} hari")
                    if hours > 0:
                        parts.append(f"{int(hours)} jam")
                    if minutes > 0:
                        parts.append(f"{int(minutes)} menit")
                    if seconds > 0:
                        parts.append(f"{int(seconds)} detik")

                    record.masa_hukuman = ', '.join(parts) if parts else "0 detik"
                else:
                    record.masa_hukuman = ""
            else:
                record.masa_hukuman = ""

    description = fields.Char('Keterangan')
    employee_id = fields.Many2one('hr.employee')

    @api.constrains('date_start', 'date_end')
    def _check_date_start_end(self):
        for record in self:
            if record.date_start and record.date_end:
                if record.date_start > record.date_end:
                    raise ValidationError("Tanggal Mulai tidak boleh lebih besar dari Tanggal Selesai.")