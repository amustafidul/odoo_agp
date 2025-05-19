from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import math

_logger = logging.getLogger(__name__)


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def _attendance_action(self, next_action_xmlid, latitude=None, longitude=None, altitude=None, accuracy=None):
        # Langsung panggil _attendance_action_change, pass semua parameter via context
        ctx = dict(self.env.context)
        if latitude:
            ctx["latitude"] = latitude
        if longitude:
            ctx["longitude"] = longitude
        return self.with_context(ctx)._attendance_action_change()

    def _attendance_action_change(self):
        # Step 1: Validasi Lokasi
        latitude = self.env.context.get("latitude", False)
        longitude = self.env.context.get("longitude", False)
        keterangan_check_in_from_context = self.env.context.get('new_check_in_keterangan')

        # Validasi hanya saat CHECK-IN
        if self.attendance_state == 'checked_out':
            param_sudo = self.env['ir.config_parameter'].sudo()
            # try:
            office_lat_str = param_sudo.get_param('agp.office_latitude')
            office_lon_str = param_sudo.get_param('agp.office_longitude')
            allowed_radius_str = param_sudo.get_param('agp.office_allowed_radius', '100.0')
            print()
            print('office_lat_str', office_lat_str, office_lon_str, allowed_radius_str)
            print()
            if not office_lat_str or not office_lon_str:
                _logger.warning("Koordinat kantor belum diset.")
            else:
                office_lat = float(office_lat_str)
                office_lon = float(office_lon_str)
                allowed_radius = float(allowed_radius_str)
                if not latitude or not longitude:
                    raise UserError(_("Lokasi tidak terdeteksi. Pastikan GPS aktif & izinkan akses lokasi."))
                user_lat = float(latitude)
                user_lon = float(longitude)
                _logger.warning("Koordinat user: %s %s", user_lat, user_lon)
                distance = haversine(office_lat, office_lon, user_lat, user_lon)
                if distance > allowed_radius:
                    raise UserError(_("Jarak Anda %.2f meter dari kantor. Max radius: %.0f meter.") % (distance,
                                                                                                       allowed_radius))
            # except ValueError:
            #     raise UserError(_("Konfigurasi lokasi kantor salah. Hubungi Admin."))
            # except Exception as e:
            #     _logger.error("Error validasi radius: %s", str(e))
            #     raise UserError(_("Error saat validasi lokasi. Hubungi Admin."))

            # Step 2: Tampilkan Wizard
            action = self.env['ir.actions.actions']._for_xml_id(
                'agp_attendance_ib.action_hr_attendance_keterangan_wizard_act')
            action['context'] = {
                'default_employee_id': self.id,
                'active_id': self.id,
                'default_latitude': latitude,
                'default_longitude': longitude,
            }
            return {'action': action}

        # Jika state BUKAN check-in (berarti CHECK-OUT / lainnya), langsung lanjut proses attendance standar
        res = super()._attendance_action_change()
        if latitude and longitude:
            if self.attendance_state == "checked_in":
                res.write(
                    {
                        "x_keterangan_check_in": keterangan_check_in_from_context,
                        "check_in_latitude": latitude,
                        "check_in_longitude": longitude,
                    }
                )
            else:
                res.write(
                    {
                        "check_out_latitude": latitude,
                        "check_out_longitude": longitude,
                    }
                )
        return res