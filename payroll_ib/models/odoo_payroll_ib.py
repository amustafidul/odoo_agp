from odoo import models, fields, api, _
from datetime import timedelta
from odoo.exceptions import ValidationError

import logging
import io
import base64
import xlwt

_logger = logging.getLogger(__name__)


def get_first_day_of_month(date):
    return date.replace(day=1)


def get_last_day_of_month(date):
    if date.month == 12:
        next_month = date.replace(year=date.year + 1, month=1, day=1)
    else:
        next_month = date.replace(month=date.month + 1, day=1)
    last_day_of_month = next_month - timedelta(days=1)
    return last_day_of_month


class OdooPayrollMaster(models.Model):
    _name = 'odoo.payroll.master'
    _description = 'Master Payroll AGP'

    name = fields.Char('Nomor Penggajian', default=_('New'), compute='_compute_name')

    # informasi karyawan
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    employment_type = fields.Selection(related='employee_id.employment_type')
    grade_id = fields.Many2one('odoo.payroll.grade', string='Grade', compute='_compute_informasi_karyawan')
    jabatan_id = fields.Many2one('employee.position.payroll', string='Jabatan', compute='_compute_informasi_karyawan')
    region_id = fields.Many2one('umk.region', string='Wilayah/Cabang')
    umk_id = fields.Many2one('umk.master', string='UMK')

    # default currency & company
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

    # informasi pembayaran
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    jumlah_hari_kerja = fields.Char(compute='_compute_jumlah_hari_kerja')
    overtime_amount = fields.Monetary('Overtime', compute='_compute_overtime_amount')
    basic_salary_amount = fields.Monetary('Gaji Dasar', compute='_compute_basic_salary_amount')
    tunjangan_posisi_amount = fields.Monetary('Tunjangan Posisi', compute='_compute_tunjangan_posisi_amount')
    tunjangan_tad_amount = fields.Monetary('Tunjangan', compute='_compute_tunjangan_posisi_amount')
    koefisien_tad = fields.Float('Koefisien', compute='_compute_tunjangan_posisi_amount')
    delta_tad_amount = fields.Monetary('Delta')
    bpfp_amount = fields.Monetary('BPFP', compute='_compute_tunjangan_posisi_amount')
    tunjangan_kemahalan_amount = fields.Monetary('Tunjangan Kemahalan', compute='_compute_tunjangan_posisi_amount')
    salary_amount_total = fields.Monetary('Total Pembayaran', compute='_compute_salary_amount_total')
    tad_salary_amount_total = fields.Monetary('Total Gaji', compute='_compute_tad_salary_amount_total')

    # informasi potongan gaji
    bpjs_jht_amount = fields.Monetary('IP BPJS JHT', compute='_compute_bpjs')
    tad_bpjs_jht_amount = fields.Monetary('IP BPJS JHT', compute='_compute_tad_bpjs')
    tad_thr_amount = fields.Monetary('THR', compute='_compute_tad_thr_amount')
    tad_kompensasi_amount = fields.Monetary('Kompensasi', compute='_compute_tad_thr_amount')
    bpjs_jaminan_pensiun_amount = fields.Monetary('IP BPJS Jaminan Pensiun', compute='_compute_bpjs')
    bpjs_jaminan_kesehatan_amount = fields.Monetary('IP BPJS Jaminan Kesehatan', compute='_compute_bpjs')
    simpanan_wajib_koperasi_amount = fields.Monetary('Simpanan Wajib Koperasi')
    simpanan_pokok_amount = fields.Monetary('Simpanan Pokok')
    angsuran_pinjaman_koperasi_amount = fields.Monetary('Angsuran Pinjaman Koperasi')
    amount_total_potongan = fields.Monetary('Total Potongan', compute='_compute_amount_total_potongan')

    # nett salary
    nett_salary_amount = fields.Monetary('Total Penghasilan Bersih', compute='_compute_nett_salary_amount')

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to:
                if rec.date_from.day != 1:
                    raise ValidationError("Date From must be the first day of the month.")

                last_day_of_month = self._get_last_day_of_month(rec.date_to)
                if rec.date_to != last_day_of_month:
                    raise ValidationError("Date To must be the last day of the month.")

                if rec.date_from.month != rec.date_to.month or rec.date_from.year != rec.date_to.year:
                    raise ValidationError("Date From and Date To must be in the same month.")

    def _get_last_day_of_month(self, date):
        if date.month == 12:
            next_month = date.replace(year=date.year + 1, month=1, day=1)
        else:
            next_month = date.replace(month=date.month + 1, day=1)
        last_day_of_month = next_month - timedelta(days=1)
        return last_day_of_month

    @api.model
    def default_get(self, fields_list):
        res = super(OdooPayrollMaster, self).default_get(fields_list)
        today = fields.Date.today()
        first_day_of_month = get_first_day_of_month(today)
        last_day_of_month = get_last_day_of_month(today)

        res.update({
            'date_from': first_day_of_month,
            'date_to': last_day_of_month,
        })
        return res

    @api.depends('employee_id','date_from','date_to')
    def _compute_name(self):
        self.name = 'New'
        for rec in self:
            rec.name = 'Payroll for ' + rec.employee_id.name + ': ' + str(rec.date_from) + ' - ' + str(rec.date_to) \
                if rec.employee_id and rec.date_from and rec.date_to else 'New'

    @api.depends('date_from','date_to')
    def _compute_jumlah_hari_kerja(self):
        self.jumlah_hari_kerja = ''
        for rec in self:
            get_jumlah_hari_kerja = self.action_count_jumlah_hari_kerja(rec.date_from, rec.date_to)
            rec.jumlah_hari_kerja = str(get_jumlah_hari_kerja) + ' Hari'

    @api.depends('employee_id')
    def _compute_informasi_karyawan(self):
        self.grade_id = False
        self.jabatan_id = False
        for rec in self:
            rec.grade_id = rec.employee_id.grade_id.id
            if rec.employee_id.employment_type in ['organik', 'pkwt']:
                emp_jabatan_obj = self.env['employee.position.payroll'].search([('name','=',rec.employee_id.keterangan_jabatan_id.name)])
                for emp_jabatan in emp_jabatan_obj:
                    rec.jabatan_id = emp_jabatan.id
            elif rec.employee_id.employment_type == 'tad':
                emp_jabatan_obj = self.env['employee.position.payroll'].search([('name','=',rec.employee_id.fungsi_penugasan_id.name)])
                for emp_jabatan in emp_jabatan_obj:
                    rec.jabatan_id = emp_jabatan.id

    @api.depends('employee_id','date_from','date_to')
    def _compute_overtime_amount(self):
        self.overtime_amount = 0
        for rec in self:
            employee_overtime_obj = self.env['hr.leave.lembur'].search([('employee_id','=',rec.employee_id.id),
                                                                        ('state','in',['validate', 'approved']),
                                                                        ('new_date_field','>=',rec.date_from),
                                                                        ('new_date_field','<=',rec.date_to)])
            jumlah_total_jam_lembur = 0
            for employee_overtime in employee_overtime_obj:
                jumlah_total_jam_lembur += employee_overtime.duration_waktu_lembur_ori
            rec.overtime_amount = 30000 * jumlah_total_jam_lembur

    @api.depends('grade_id')
    def _compute_basic_salary_amount(self):
        self.basic_salary_amount = 0
        for rec in self:
            rec.basic_salary_amount = rec.grade_id.grade_amount

    @api.depends('jabatan_id')
    def _compute_tunjangan_posisi_amount(self):
        self.tunjangan_posisi_amount = 0
        self.bpfp_amount = 0
        self.tunjangan_kemahalan_amount = 0
        self.tunjangan_tad_amount = 0
        self.koefisien_tad = 0
        for rec in self:
            odoo_payroll_tunjangan = self.env['odoo.payroll.tunjangan'].search([('jabatan_id','=',rec.jabatan_id.id)])
            for tunjangan in odoo_payroll_tunjangan:
                rec.tunjangan_posisi_amount = tunjangan.amount_tunjangan
                rec.tunjangan_tad_amount = tunjangan.amount_tunjangan
                gaji_koef_percent = (rec.tunjangan_tad_amount * tunjangan.koef_kemahalan_percent / 100)
                gaji_koef = rec.tunjangan_tad_amount - gaji_koef_percent
                rec.koefisien_tad = gaji_koef
                rec.bpfp_amount = tunjangan.amount_bpfp
                rec.tunjangan_kemahalan_amount = tunjangan.amount_kemahalan

    @api.depends('employee_id', 'date_from', 'date_to', 'overtime_amount', 'basic_salary_amount',
                 'tunjangan_posisi_amount', 'bpfp_amount', 'tunjangan_kemahalan_amount')
    def _compute_salary_amount_total(self):
        self.salary_amount_total = 0
        for rec in self:
            previous_history = self.env['hr.employee.histori.jabatan'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('tanggal_pengangkatan', '<', rec.date_from)
            ], order='create_date desc', limit=1)

            join_date = rec.date_from
            if previous_history:
                join_date = previous_history.tmt_date

            resign_date = rec.employee_id.resign_date

            actual_days = self.get_actual_work_days(rec.date_from, rec.date_to)

            end_date = rec.date_to
            if resign_date and resign_date <= rec.date_to:
                end_date = resign_date

            total_days = (end_date - join_date).days + 1 if join_date <= end_date else 0
            prorate_factor = actual_days / total_days if total_days > 0 else 1

            salary_components = [
                rec.overtime_amount,
                rec.basic_salary_amount,
                rec.tunjangan_posisi_amount,
                rec.bpfp_amount,
                rec.tunjangan_kemahalan_amount
            ]

            valid_salary_components = [comp for comp in salary_components if comp != 0]

            is_new_employee = not previous_history

            is_resigning = bool(resign_date and resign_date <= rec.date_to)

            job_change_in_mid_month = False
            new_job_start_date = False
            old_job_end_date = False
            for history in rec.employee_id.histori_jabatan_ids.filtered(lambda h: h.id).sorted('id'):
                if history.tanggal_pengangkatan >= rec.date_from and history.tanggal_pengangkatan <= rec.date_to:
                    job_change_in_mid_month = True
                    new_job_start_date = history.tanggal_pengangkatan
                    old_job_end_date = new_job_start_date - timedelta(days=1)
                    break

            if is_new_employee or is_resigning:
                rec.salary_amount_total = sum(valid_salary_components) * prorate_factor
            elif job_change_in_mid_month:
                old_job_salary = sum(valid_salary_components) * prorate_factor
                new_job_salary = sum(valid_salary_components) * prorate_factor
                rec.salary_amount_total = old_job_salary + ((new_job_salary + old_job_salary) / 2 - old_job_salary)
            else:
                rec.salary_amount_total = sum(salary_components)

    @api.depends('tunjangan_tad_amount', 'koefisien_tad', 'delta_tad_amount')
    def _compute_tad_salary_amount_total(self):
        self.tad_salary_amount_total = 0
        for rec in self:
            rec.tad_salary_amount_total = rec.tunjangan_tad_amount + rec.koefisien_tad + rec.delta_tad_amount

    @api.depends('basic_salary_amount')
    def _compute_bpjs(self):
        self.bpjs_jht_amount = 0
        self.bpjs_jaminan_pensiun_amount = 0
        self.bpjs_jaminan_kesehatan_amount = 0
        for rec in self:
            rec.bpjs_jht_amount = (rec.basic_salary_amount * 2)/100
            rec.bpjs_jaminan_pensiun_amount = (rec.basic_salary_amount * 1)/100
            rec.bpjs_jaminan_kesehatan_amount = (rec.basic_salary_amount * 1)/100

    @api.depends('koefisien_tad')
    def _compute_tad_bpjs(self):
        self.tad_bpjs_jht_amount = 0
        for rec in self:
            rec.tad_bpjs_jht_amount = (rec.koefisien_tad * 11.74) / 100

    @api.depends('koefisien_tad')
    def _compute_tad_thr_amount(self):
        self.tad_thr_amount = 0
        self.tad_kompensasi_amount = 0
        for rec in self:
            rec.tad_thr_amount = rec.koefisien_tad / 12
            rec.tad_kompensasi_amount = rec.koefisien_tad / 12

    @api.depends('bpjs_jht_amount','bpjs_jaminan_pensiun_amount','bpjs_jaminan_kesehatan_amount')
    def _compute_amount_total_potongan(self):
        self.amount_total_potongan = 0
        for rec in self:
            rec.amount_total_potongan = rec.bpjs_jht_amount + rec.bpjs_jaminan_pensiun_amount + rec.bpjs_jaminan_kesehatan_amount

    @api.depends('salary_amount_total', 'amount_total_potongan')
    def _compute_nett_salary_amount(self):
        self.nett_salary_amount = 0
        for rec in self:
            rec.nett_salary_amount = rec.salary_amount_total - rec.amount_total_potongan

    def action_count_jumlah_hari_kerja(self, date_from, date_to):
        count_active_working_days = self.employee_id.get_active_working_days(date_from.year, date_to.month)
        return int(count_active_working_days)

    def get_actual_work_days(self, date_from, date_to):
        # Implementasi logika untuk menghitung jumlah hari kerja yang sebenarnya dilakukan
        # Misalnya, menggunakan data absensi karyawan
        actual_days = 0
        attendance_obj = self.env['hr.attendance'].search([
            ('employee_id', '=', self.employee_id.id),
            ('check_in', '>=', date_from),
            ('check_out', '<=', date_to)
        ])
        for attendance in attendance_obj:
            actual_days += 1
        return actual_days

    def get_absent_days(self, date_from, date_to):
        scheduled_days = self.action_count_jumlah_hari_kerja(date_from, date_to)
        actual_days = self.get_actual_work_days(date_from, date_to)
        absent_days = scheduled_days - actual_days
        return absent_days

    def action_count_jumlah_hari_masuk(self):
        date_from = self.date_from
        date_to = self.date_to

        scheduled_days = self.action_count_jumlah_hari_kerja(date_from, date_to)
        actual_days = self.get_actual_work_days(date_from, date_to)
        absent_days = self.get_absent_days(date_from, date_to)

    def action_export_to_excel(self):
        output = io.BytesIO()
        workbook = xlwt.Workbook()
        sheet = workbook.add_sheet('Penggajian')

        # Header kolom
        headers = [
            'Nama Karyawan', 'Gaji Dasar', 'Tunjangan Posisi', 'BPFP',
            'Total Potongan', 'Penghasilan Bersih'
        ]
        style_header = xlwt.easyxf('font: bold 1; align: wrap on, vert centre, horiz center; '
                                   'borders: top thin, bottom thin, left thin, right thin; '
                                   'pattern: pattern solid, fore_colour gray25;')
        for col, header in enumerate(headers):
            sheet.write(0, col, header, style_header)
            sheet.col(col).width = 256 * 20  # Set lebar kolom

        # Data penggajian
        row = 1
        num_format = '#,##0.00'  # Format angka dengan pemisah ribuan
        style_data = xlwt.easyxf('align: wrap on, vert centre, horiz right; '
                                 'borders: top thin, bottom thin, left thin, right thin;',
                                 num_format_str=num_format)  # Menggunakan num_format_str di sini

        for rec in self:
            sheet.write(row, 0, rec.employee_id.name or '', xlwt.easyxf('align: wrap on, vert centre, horiz left; '
                                                                        'borders: top thin, bottom thin, left thin, right thin;'))
            sheet.write(row, 1, rec.basic_salary_amount or 0, style_data)
            sheet.write(row, 2, rec.tunjangan_posisi_amount or 0, style_data)
            sheet.write(row, 3, rec.bpfp_amount or 0, style_data)
            sheet.write(row, 4, rec.amount_total_potongan or 0, style_data)
            sheet.write(row, 5, rec.nett_salary_amount or 0, style_data)
            row += 1

        workbook.save(output)
        output.seek(0)

        attachment = self.env['ir.attachment'].create({
            'name': 'penggajian.xls',
            'datas': base64.b64encode(output.read()),
            'mimetype': 'application/vnd.ms-excel'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }