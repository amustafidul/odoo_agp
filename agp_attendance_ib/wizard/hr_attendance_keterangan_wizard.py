from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class HrAttendanceKeteranganWizard(models.TransientModel):
    _name = 'hr.attendance.keterangan.wizard'
    _description = 'Wizard Keterangan Check In/Out'

    keterangan = fields.Text(string='Keterangan', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    # Bisa ditambahkan field untuk menandai apakah ini untuk Check In atau Check Out jika wizardnya generik
    # attendance_action_type = fields.Selection([('check_in', 'Check In'), ('check_out', 'Check Out')], string="Tipe Aksi", readonly=True)

    def action_confirm_attendance_with_keterangan(self):
        self.ensure_one()

        employee_to_process = self.employee_id
        if not employee_to_process:
            # Jika employee_id tidak ada di wizard (seharusnya sudah diisi dari context)
            # Coba ambil dari context lagi atau dari user yang login
            employee_id_from_context = self.env.context.get('active_id') or self.env.context.get('default_employee_id')
            if not employee_id_from_context:
                 # Jika tombol di dashboard/my attendance, employee adalah user saat ini
                current_user_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
                if not current_user_employee:
                    raise UserError(_("Karyawan tidak teridentifikasi untuk melanjutkan Check In."))
                employee_to_process = current_user_employee
            else:
                employee_to_process = self.env['hr.employee'].browse(employee_id_from_context)

        if not employee_to_process:
             raise UserError(_("Tidak bisa menemukan Karyawan untuk Check In."))

        # Panggil metode _attendance_action_change dari hr.employee
        # dengan menyertakan keterangan yang diinput melalui context.
        action_date = fields.Datetime.now() # Waktu check-in aktual

        # Memanggil metode _attendance_action_change yang sudah di-override (lihat Langkah 3)
        # Keterangan akan diambil dari context di dalam _attendance_action_change
        attendance_record = employee_to_process.with_context(
            new_check_in_keterangan=self.keterangan
        )._attendance_action_change()

        _logger.info("Karyawan %s berhasil Check In dengan keterangan: %s", employee_to_process.name, self.keterangan)

        # Mengembalikan action yang akan me-refresh UI Attendance (misalnya My Attendances atau dashboard)
        # 'hr_attendance.hr_attendance_action_my_attendances' adalah XML ID untuk action client "My Attendances"
        # Jika tombol ada di dashboard custom, mungkin perlu action tag yang berbeda.

        return {'type': 'ir.actions.client', 'tag': 'reload'}