from odoo import models, fields, api, _
from odoo.exceptions import UserError
import os
import base64
import tempfile
import pandas as pd

class WizardImportEmployee(models.TransientModel):
    _name = 'wizard.import.employee'
    _description = 'Wizard Import Data Pegawai + Histori Jabatan'

    file = fields.Binary(string="Upload File Excel", required=True)
    filename = fields.Char(string="File Name")

    def action_import(self):
        if not self.file:
            raise UserError(_("Silakan upload file Excel terlebih dahulu."))

        MAX_FILE_SIZE_MB = 5  # 5 MB
        MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

        file_content = base64.b64decode(self.file)

        if len(file_content) > MAX_FILE_SIZE_BYTES:
            message = _("File '%s' (%s MB) terlalu besar. Ukuran maksimal yang diizinkan adalah %sMB.") % \
                      (self.filename or 'Excel',
                       round(len(file_content) / (1024 * 1024), 2),
                       MAX_FILE_SIZE_MB)
            raise UserError(message)

        tmp_file_path = ""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
                tmp_file.write(file_content)
                tmp_file_path = tmp_file.name

            df = pd.read_excel(tmp_file_path)
        except Exception as e:
            raise UserError(_("Gagal membaca file Excel: %s") % str(e))
        finally:
            if tmp_file_path and os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)

        required_columns = ['name', 'histori_jabatan_ids/employment_type',
                            'histori_jabatan_ids/grade_id']
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            raise UserError(_("Kolom wajib berikut tidak ditemukan di file Excel: %s") % ", ".join(missing_cols))

        processed_count = 0
        error_count = 0
        error_messages = []

        for index, row in df.iterrows():
            try:
                name = str(row.get('name', '')).strip().upper()
                if not name:
                    continue

                employment_type = str(row.get('histori_jabatan_ids/employment_type', '')).strip().lower()
                nip_organik = str(row.get('nip_organik', '')).strip() if pd.notna(row.get('nip_organik')) else ''
                nip_pkwt = str(row.get('nip_pkwt', '')).strip() if pd.notna(row.get('nip_pkwt')) else ''
                work_email = str(row.get('work_email', '')).strip() if pd.notna(row.get('work_email')) else ''
                mobile_phone = str(row.get('mobile_phone', '')).strip() if pd.notna(row.get('mobile_phone')) else ''

                grade_name = str(row.get('histori_jabatan_ids/grade_id', '')).strip()
                tmt_date = pd.to_datetime(row.get('histori_jabatan_ids/tmt_date')).date() if pd.notna(
                    row.get('histori_jabatan_ids/tmt_date')) else None
                tanggal_pengangkatan = pd.to_datetime(
                    row.get('histori_jabatan_ids/tanggal_pengangkatan')).date() if pd.notna(
                    row.get('histori_jabatan_ids/tanggal_pengangkatan')) else None
                tanggal_selesai_kontrak = pd.to_datetime(
                    row.get('histori_jabatan_ids/tanggal_selesai_kontrak')).date() if pd.notna(
                    row.get('histori_jabatan_ids/tanggal_selesai_kontrak')) else None

                jabatan_name = str(row.get('histori_jabatan_ids/keterangan_jabatan_id', '')).strip() if pd.notna(
                    row.get('histori_jabatan_ids/keterangan_jabatan_id')) else ''
                fungsi_name = str(row.get('histori_jabatan_ids/fungsi_penugasan_id', '')).strip() if pd.notna(
                    row.get('histori_jabatan_ids/fungsi_penugasan_id')) else ''
                branch_name = str(row.get('histori_jabatan_ids/hr_branch_id', '')).strip() if pd.notna(
                    row.get('histori_jabatan_ids/hr_branch_id')) else ''

                grade = self.env['odoo.payroll.grade'].search([('name', '=ilike', grade_name)], limit=1)
                if not grade and grade_name:
                    error_messages.append(_("Baris %s: Grade '%s' tidak ditemukan.") % (index + 2, grade_name))
                    error_count += 1
                    continue

                jabatan = self.env['hr.employee.keterangan.jabatan'].search([('name', 'ilike', jabatan_name)],
                                                                            limit=1) if jabatan_name else False
                fungsi = self.env['hr.employee.fungsi.penugasan'].search([('name', 'ilike', fungsi_name)],
                                                                         limit=1) if fungsi_name else False
                branch = self.env['hr.branch'].search([('name', 'ilike', branch_name)],
                                                      limit=1) if branch_name else False

                employee_vals = {
                    'name': name,
                    'employment_type': employment_type,
                    'nip_organik': nip_organik,
                    'nip_pkwt': nip_pkwt,
                    'work_email': work_email,
                    'mobile_phone': mobile_phone,
                    'grade_id': grade.id if grade else False,
                }
                employee = self.env['hr.employee'].search([('name', '=', name)], limit=1)
                if not employee:
                    employee = self.env['hr.employee'].create(employee_vals)
                else:
                    employee.write(employee_vals)

                histori_vals = {
                    'employee_id': employee.id,
                    'employment_type': employment_type,
                    'keterangan_jabatan_id': jabatan.id if jabatan else False,
                    'fungsi_penugasan_id': fungsi.id if fungsi else False,
                    'hr_branch_id': branch.id if branch else False,
                    'grade_id': grade.id if grade else False,
                    'tmt_date': tmt_date,
                    'tanggal_pengangkatan': tanggal_pengangkatan,
                    'tanggal_selesai_kontrak': tanggal_selesai_kontrak,
                }
                self.env['hr.employee.histori.jabatan'].create(histori_vals)
                processed_count += 1

            except Exception as e:
                error_count += 1
                error_messages.append(_("Gagal memproses baris ke-%s (%s): %s") % (index + 2, name, str(e)))
                continue

        if error_count > 0:
            final_message = _("Proses import selesai. %s data berhasil diimport, %s data gagal.") % (processed_count,
                                                                                                     error_count)
            final_message += "\n\nDetail Kegagalan:\n" + "\n".join(error_messages[:5])  # Tampilkan 5 error pertama
            if error_count > 5:
                final_message += _("\n...dan %s kesalahan lainnya (cek log server untuk detail).") % (error_count - 5)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Import Selesai dengan Kesalahan'),
                    'message': final_message,
                    'type': 'warning',
                    'sticky': True,
                    'next': {'type': 'ir.actions.client', 'tag': 'reload'}
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Import Sukses'),
                    'message': _('Semua %s data karyawan dan histori jabatan berhasil diimport.') % processed_count,
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.client', 'tag': 'reload'}
                }
            }