from odoo import models, fields, tools, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

import random
import logging
import pytz
import mysql.connector

_logger = logging.getLogger(__name__)


class HrEmployeeJabatanKomplit(models.Model):
    _name = 'hr.employee.jabatan.komplit'
    _description = 'Jabatan Komplit Employee'
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Nama Jabatan harus unik!'),
        ('code_uniq', 'unique(code)', 'Kode Jabatan harus unik!'),
    ]

    name = fields.Char(required=True, translate=True)
    code = fields.Char("Kode Jabatan", help="Kode unik untuk jabatan")
    description = fields.Text("Deskripsi")
    active = fields.Boolean("Aktif", default=True)
    department_id = fields.Many2one('hr.department', string="Department")


class HrSkTim(models.Model):
    _name = 'hr.sk.tim'
    _description = 'SK Tim'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Nama Peserta',
        required=True
    )
    no_sk = fields.Char("No. SK")
    upload_sk = fields.Binary("Upload SK")
    date_start = fields.Date("Tanggal Mulai")
    date_end = fields.Date("Tanggal Selesai")
    jabatan = fields.Char("Jabatan")


class PenilaianKinerja(models.Model):
    _name = 'penilaian.kinerja'
    _description = 'Penilaian Kinerja'

    employee_id = fields.Many2one(
        'hr.employee'
    )
    tahun = fields.Char("Tahun")
    semester = fields.Char("Semester")
    penilaian = fields.Char("Penilaian")


class HrEmployeeAssesment(models.Model):
    _name = 'hr.employee.assesment'
    _description = 'Employee Assesment'

    employee_id = fields.Many2one(
        'hr.employee'
    )
    date = fields.Date("Tanggal")
    hasil = fields.Char("Hasil")
    attachment_file = fields.Binary("Upload")


class HrSkTimPenugasan(models.Model):
    _name = 'hr.sk.tim.penugasan'
    _description = 'SK Tim Penugasan'

    employee_id = fields.Many2one('hr.employee', string='Nama Peserta', required=True)
    no_sk = fields.Char('No. SK')
    upload_sk = fields.Binary('Upload SK')
    name = fields.Char('Nama SK')
    date_start = fields.Date('Tanggal Mulai')
    date_end = fields.Date('Tanggal Selesai')
    jabatan = fields.Char('Jabatan')

    @api.model
    def create(self, vals):
        record = super(HrSkTimPenugasan, self).create(vals)
        if record.employee_id:
            record.employee_id.invalidate_cache(['sk_tim_ids'])
        return record

    def write(self, vals):
        result = super(HrSkTimPenugasan, self).write(vals)
        for rec in self:
            if rec.employee_id:
                rec.employee_id.invalidate_cache(['sk_tim_ids'])
        return result


class PeraturanPerusahaan(models.Model):
    _name = 'peraturan.perusahaan'
    _description = 'Peraturan Perusahaan'

    name = fields.Char()
    tahun_berlaku = fields.Char()
    attachment_file = fields.Binary('Upload')


class KeputusanDireksi(models.Model):
    _name = 'keputusan.direksi'
    _description = 'Keputusan Direksi'

    name = fields.Char('Nomor')
    keterangan = fields.Char('Keterangan')
    date = fields.Date('Tanggal')
    attachment_file = fields.Binary('Upload')


class SuratEdaranDireksi(models.Model):
    _name = 'surat.edaran.direksi'
    _description = 'Surat Edaran Direksi'

    name = fields.Char('Nomor')
    keterangan = fields.Char('Keterangan')
    date = fields.Date('Tanggal')
    attachment_file = fields.Binary('Upload')


class AgpNotaDinasCollective(models.Model):
    _name = 'agp.nota.dinas.collective'
    _auto = False
    _description = 'Collective Nota Dinas'

    name = fields.Char(string='Nota Number', readonly=True)
    date = fields.Date(string='Date', readonly=True)
    model_source = fields.Char(string='Source Model', readonly=True)

    @staticmethod
    def _refresh_collective_view(cr):
        tools.drop_view_if_exists(cr, 'agp_nota_dinas_collective')
        cr.execute("""
                CREATE OR REPLACE VIEW agp_nota_dinas_collective AS (
                    SELECT
                        (1000000 + id) AS id,
                        name,
                        tanggal_nota_dinas AS date,
                        'nota.dinas' AS model_source
                    FROM nota_dinas
                    UNION ALL
                    SELECT
                        (2000000 + id) AS id,
                        name,
                        tanggal_pengajuan AS date,
                        'account.keuangan.nota.dinas' AS model_source
                    FROM account_keuangan_nota_dinas
                    UNION ALL
                    SELECT
                        (3000000 + id) AS id,
                        name,
                        tanggal_pengajuan AS date,
                        'account.keuangan.nota.dinas.bod' AS model_source
                    FROM account_keuangan_nota_dinas_bod
                )
            """)

    @api.model
    def cron_refresh_collective_view(self):
        self._refresh_collective_view(self._cr)


class NotaDinasSummary(models.Model):
    _name = 'nota.dinas.summary'
    _description = 'Nota Dinas Summary'

    name = fields.Char()
    nodin_collective_id = fields.Many2one('agp.nota.dinas.collective', string='Nomor Nota Dinas')
    nama_nodin = fields.Char()
    date = fields.Date('Tanggal')
    attachment_file = fields.Binary('Upload')


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def redirect_to_simkp(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/redirect_to_simkp_post?employee_id={self.id}',
            'target': 'new',
        }

    EMPLOYMENT_TYPE_MAPPING = {
        'tad': 'TAD',
        'pkwt': 'PKWT',
        'organik': 'Organik',
        'direksi': 'Direksi',
        'jajaran_dekom': 'Dekom & Perangkat Dekom',
        'konsultan_individu': 'Konsultan Individu',
    }

    is_editor_employee_data = fields.Boolean(compute='_compute_is_editor_employee_data')
    employment_type = fields.Selection(selection=[
        ('tad', 'TAD'),
        ('pkwt', 'PKWT'),
        ('organik', 'Organik'),
        ('direksi', 'Direksi'),
        ('jajaran_dekom', 'Dekom & Perangkat Dekom'),
        ('konsultan_individu', 'Konsultan Individu'),
    ], string="Jenis Pegawai", index=True)
    employment_type_related = fields.Selection(related='employment_type', string="Employment Type", store=True)
    histori_jabatan_ids = fields.One2many('hr.employee.histori.jabatan', 'employee_id', string="Histori Jabatan")
    family_ids = fields.One2many('hr.employee.family', 'employee_id', string="Family")
    hr_employee_ijazah_ids = fields.One2many('hr.employee.ijazah', 'employee_id', string="Ijazah")
    hr_employee_hukuman_ids = fields.One2many('hr.employee.hukuman', 'employee_id', string="Hukuman")
    hr_employee_sertifikasi_pelatihan_ids = fields.One2many('hr.employee.sertifikasi.pelatihan', 'employee_id', string="Sertifikasi & Pelatihan")
    hr_employee_unit_id = fields.Many2one('hr.employee.unit', string="Unit", index=True, tracking=True)
    keterangan_jabatan = fields.Char('Keterangan Jabatan')
    keterangan_jabatan_id = fields.Many2one('hr.employee.keterangan.jabatan', string='Jabatan', index=True, help="Pilih keterangan jabatan struktural atau umum.")
    jabatan = fields.Char('Jabatan')
    jabatan_komplit_id = fields.Many2one('hr.employee.jabatan.komplit', string='Jabatan Komplit')

    @api.onchange('keterangan_jabatan_id', 'fungsi_penugasan_id', 'hr_employee_unit_id')
    def _onchange_field_jabatan(self):
        for rec in self:
            if rec.employment_type in ['organik','pkwt']:
                rec.jabatan = (rec.keterangan_jabatan_id.name or '') + ' ' + (rec.hr_employee_unit_id.name or '')
            else:
                rec.jabatan = (rec.fungsi_penugasan_id.name or '') + ' ' + (rec.hr_employee_unit_id.name or '')

    jenis_jabatan = fields.Selection(
                        [
                            ('plt', 'Pelaksana Tugas (PLT)'),
                            ('reguler', 'Reguler'),
                        ],
                        string='Status Jabatan',
                        default='reguler'
                    )

    date_of_birth = fields.Date('Tanggal lahir', tracking=True)
    place_of_birth = fields.Char('Tempat lahir')
    usia = fields.Char('Usia', compute='_compute_field_usia')
    perkiraan_tanggal_pensiun = fields.Date(
        string='Perkiraan Tanggal Pensiun',
        compute='_compute_perkiraan_tanggal_pensiun',
        store=True
    )
    alamat = fields.Char("Alamat", compute="_compute_alamat")
    alamat_ktp = fields.Text("Alamat KTP", compute='_compute_alamat_ktp')
    alamat_domisili = fields.Text("Alamat Domisili", compute='_compute_alamat_domisili', inverse='_inverse_alamat_domisili')
    marital_status_custom = fields.Selection(
        [
            ('nikah_resmi', 'Nikah Resmi'),
            ('lajang', 'Lajang'),
            ('janda_duda_cerai_mati', 'Janda/Duda Cerai Mati'),
            ('janda_duda_cerai_hidup', 'Janda/Duda Cerai Hidup'),
        ],
        string="Status Pernikahan",
        default='lajang'
    )
    buku_nikah_attachment = fields.Binary(string="Upload Buku Nikah")
    pendidikan_terakhir = fields.Char('Pendidikan terakhir')
    pendidikan_terakhir_description = fields.Text('Keterangan')
    masa_kerja = fields.Char('Masa Kerja', compute='_compute_masa_kerja')
    kelompok_umur_id = fields.Many2one('hr.employee.kelompok.umur', string='Kelompok Umur')
    gender = fields.Selection(
                        [
                            ('male', 'Male'),
                            ('female', 'Female'),
                        ],
                        string='Jenis Kelamin'
                    )
    agama = fields.Selection([
            ('islam', 'Islam'),
            ('kristen', 'Kristen Protestan'),
            ('katolik', 'Katolik'),
            ('hindu', 'Hindu'),
            ('buddha', 'Buddha'),
            ('konghucu', 'Konghucu'),
            ('lainnya', 'Lainnya')
        ], string="Agama")
    attachment_doc_kk = fields.Binary('Upload KK')
    kk_name = fields.Char('kk_name', compute='_compute_kk_name')
    attachment_doc_ktp = fields.Binary('Upload KTP')
    ktp_name = fields.Char('ktp_name', compute='_compute_ktp_name')
    cabang_kerja_id = fields.Many2one('res.branch')
    sub_cabang_kerja_id = fields.Many2one('sub.branch')
    hr_branch_id = fields.Many2one('hr.branch', compute='_compute_hr_branch_id', string='Penempatan', readonly=True, store=True, tracking=True)
    sub_branch_id = fields.Many2one('hr.employee.unit.penempatan')
    alamat_sub_cabang = fields.Text('Alamat')

    show_alamat_sub_cabang = fields.Boolean(compute='_compute_show_alamat_sub_cabang', store=False)

    @api.depends('sub_cabang_kerja_id')
    def _compute_show_alamat_sub_cabang(self):
        for record in self:
            record.show_alamat_sub_cabang = bool(record.sub_cabang_kerja_id)

    # salary information
    bank_account_ids = fields.One2many(
        related='address_home_id.bank_ids',
        string='Rekening Bank',
        readonly=False
    )
    salary_amount = fields.Monetary('Salary')
    amount_tunjangan = fields.Monetary('Tunjangan')
    bpjs_kesehatan_no = fields.Char('Nomor BPJS Kesehatan')
    bpjs_ketenagakerjaan_no = fields.Char('Nomor BPJS Ketenagakerjaan')
    kis_attachment = fields.Binary('Unggah KIS')
    jamsostek_attachment = fields.Binary('Unggah BPJS Ketenagakerjaan')
    npwp = fields.Char('NPWP')
    npwp_attachment = fields.Binary('Unggah kartu NPWP')
    nomor_rekening = fields.Char('Nomor Rekening')
    nama_rekening = fields.Char()
    nama_bank = fields.Char()
    insurance_collective = fields.Char(
        string="Kepesertaan Asuransi",
        compute="_compute_insurance_collective",
        store=False
    )
    nomor_polis = fields.Char()

    def _compute_insurance_collective(self):
        emp_ids = self.ids

        ak_lines = self.env['asuransi.karyawan.line.peserta'].search([('employee_id', 'in', emp_ids)])
        ad_lines = self.env['asuransi.direksi.line.peserta'].search([('employee_id', 'in', emp_ids)])

        ak_group = {}
        for line in ak_lines:
            emp_id = line.employee_id.id
            if line.asuransi_karyawan_id and line.asuransi_karyawan_id.name:
                ak_group.setdefault(emp_id, []).append(line.asuransi_karyawan_id.name)

        ad_group = {}
        for line in ad_lines:
            emp_id = line.employee_id.id
            if line.asuransi_direksi_id and line.asuransi_direksi_id.name:
                ad_group.setdefault(emp_id, []).append(line.asuransi_direksi_id.name)

        for emp in self:
            names = set(ak_group.get(emp.id, []) + ad_group.get(emp.id, []))
            emp.insurance_collective = ", ".join(names)
    #

    # SK Tim
    sk_tim_ids = fields.One2many(
        'hr.sk.tim.penugasan',
        'employee_id',
        string='Penugasan Tim',
        compute='_compute_sk_tim_ids',
        store=False
    )

    def _compute_sk_tim_ids(self):
        tim_records = self.env['hr.sk.tim.penugasan'].search([('employee_id', 'in', self.ids)])
        groups = {}
        for record in tim_records:
            groups.setdefault(record.employee_id.id, self.env['hr.sk.tim.penugasan'])
            groups[record.employee_id.id] |= record
        for employee in self:
            employee.sk_tim_ids = groups.get(employee.id, self.env['hr.sk.tim.penugasan'])
    #

    # penilaian kinerja
    penilaian_kerja_ids = fields.One2many('penilaian.kinerja', 'employee_id')
    #

    # Assesment
    assesment_ids = fields.One2many('hr.employee.assesment', 'employee_id')
    #

    fungsi_penugasan_id = fields.Many2one('hr.employee.fungsi.penugasan', string='Jabatan TAD', index=True)
    unit_penempatan_id = fields.Many2one('hr.employee.unit.penempatan', string='Unit Penempatan', index=True)
    unit_penempatan_cabang_organik_pkwt_id = fields.Many2one('hr.employee.unit.penempatan.cabang', string='Cabang', index=True)
    nip_organik = fields.Char('NIP', help="Nomor Induk Pegawai untuk karyawan organik.")
    nip_pkwt = fields.Char('NIP', help="Nomor Induk Pegawai untuk karyawan PKWT.")
    status_pajak_pkwt_id = fields.Many2one('hr.employee.status.pajak', string='Status Pajak')
    edit_lock_status = fields.Selection([
        ('locked', 'Locked for Editing'),
        ('to_approve', 'Waiting for Approval'),
        ('approved', 'Approved'),
    ],
        string='Status ubah record',
        default='locked',
    )
    vendor_tad_id = fields.Many2one('agp.vendor.tad', string="Vendor TAD")
    keterangan_vendor_tad = fields.Text('Keterangan Vendor')
    is_can_edit = fields.Boolean(string='Is can edit?',
        compute='_compute_is_can_edit')
    is_non_hr_admin = fields.Boolean(string='Is non hr admin?', compute='_compute_is_non_hr_admin')
    direksi = fields.Selection([
        ('dir1', 'Direksi 1'),
        ('dir2', 'Direksi 2'),
        ('dir3', 'Direksi 3'),
        ('dir4', 'Direksi 4'),
    ],
        string='Direksi'
    )
    employment_type_temp = fields.Char(compute='_compute_employment_type_temp')
    koperasi_ids = fields.One2many('hr.employee.koperasi', 'employee_id', string='Koperasi')
    grade_id = fields.Many2one('odoo.payroll.grade', string='Grade', required=False)

    ## seragam
    jenis_atasan = fields.Selection([
        ('shirt', 'Shirt'),
        ('jacket', 'Jacket'),
    ], string='Jenis Atasan', compute='_compute_uniform_details', store=True)

    ukuran_atasan = fields.Selection([
        ('xs', 'XS'),
        ('s', 'S'),
        ('m', 'M'),
        ('l', 'L'),
        ('xl', 'XL'),
        ('xxl', 'XXL'),
        ('xxxl', 'XXXL'),
    ], string='Ukuran Atasan', compute='_compute_uniform_details', store=True)

    jenis_bawahan = fields.Selection([
        ('rok', 'Rok'),
        ('celana', 'Celana'),
    ], string='Jenis Bawahan', compute='_compute_uniform_details', store=True)

    ukuran_bawahan = fields.Selection([
        ('xs', 'XS'),
        ('s', 'S'),
        ('m', 'M'),
        ('l', 'L'),
        ('xl', 'XL'),
        ('xxl', 'XXL'),
        ('xxxl', 'XXXL'),
    ], string='Ukuran Bawahan', compute='_compute_uniform_details', store=True)

    def _compute_uniform_details(self):
        employee_ids = self.ids
        uniform_records = self.env['selected.employee.uniform'].search([
            ('employee_id', 'in', employee_ids)
        ], order='create_date desc')
        latest_uniform_by_employee = {}
        for uniform in uniform_records:
            emp_id = uniform.employee_id.id
            if emp_id not in latest_uniform_by_employee:
                latest_uniform_by_employee[emp_id] = uniform

        for employee in self:
            latest_uniform = latest_uniform_by_employee.get(employee.id)
            if latest_uniform:
                employee.jenis_atasan = latest_uniform.uniform_id.uniform_type
                employee.ukuran_atasan = latest_uniform.ukuran_atasan
                employee.jenis_bawahan = latest_uniform.jenis_bawahan_pakaian
                employee.ukuran_bawahan = latest_uniform.ukuran_bawahan
            else:
                employee.jenis_atasan = False
                employee.ukuran_atasan = False
                employee.jenis_bawahan = False
                employee.ukuran_bawahan = False
    ##

    def _compute_masa_kerja(self):
        today = fields.Date.today()
        for employee in self:
            masa_kerja = "0 tahun 0 bulan"
            if employee.histori_jabatan_ids:
                sorted_histories = employee.histori_jabatan_ids.sorted(key=lambda h: h.create_date or today)
                first_histori = sorted_histories[0]
                if first_histori.tmt_date:
                    start_date = fields.Date.from_string(first_histori.tmt_date)
                    delta = today - start_date
                    years = delta.days // 365
                    months = (delta.days % 365) // 30
                    masa_kerja = f"{years} tahun {months} bulan"

            employee.masa_kerja = masa_kerja

    @api.depends('user_id')
    def _compute_is_editor_employee_data(self):
        self.is_editor_employee_data = self.env.user.has_group('agp_employee_ib.group_can_edit_employee')

    def _compute_employment_type_temp(self):
        self.employment_type_temp = ''
        employment_type_temp_ = ''
        for rec in self:
            for histori in rec.histori_jabatan_ids.filtered(lambda h: h.id).sorted('id', reverse=True)[:1]:
                employment_type_temp_ = histori.employment_type
            rec.employment_type_temp = employment_type_temp_

    @api.depends('name')
    def _compute_kk_name(self):
        for employee in self:
            name = '_' + employee.name.replace(' ', '_') if employee.name else ''
            employee.kk_name = "KK%s" % (name)

    @api.depends('name')
    def _compute_ktp_name(self):
        for employee in self:
            name = '_' + employee.name.replace(' ', '_') if employee.name else ''
            employee.ktp_name = "KTP%s" % (name)

    @api.depends('address_home_id', 'address_home_id.street', 'address_home_id.street2', 'address_home_id.zip',
                 'address_home_id.city', 'address_home_id.state_id', 'address_home_id.country_id')
    def _compute_alamat_ktp(self):
        for employee in self:
            if employee.address_home_id:
                parts = [
                    employee.address_home_id.street,
                    employee.address_home_id.street2,
                    employee.address_home_id.city,
                    employee.address_home_id.zip,
                    employee.address_home_id.state_id.name if employee.address_home_id.state_id else None,
                    employee.address_home_id.country_id.name if employee.address_home_id.country_id else None,
                ]
                employee.alamat_ktp = ", ".join(filter(None, parts))
            else:
                employee.alamat_ktp = False

    @api.depends('address_home_id', 'address_home_id.x_alamat_domisili')
    def _compute_alamat_domisili(self):
        for employee in self:
            if employee.address_home_id and employee.address_home_id.x_alamat_domisili:
                employee.alamat_domisili = employee.address_home_id.x_alamat_domisili
            else:
                employee.alamat_domisili = False

    def _inverse_alamat_domisili(self):
        for employee in self:
            if employee.address_home_id:
                employee.address_home_id.x_alamat_domisili = employee.alamat_domisili

    @api.depends('user_id')
    def _compute_is_can_edit(self):
        for record in self:
            user = self.env.user
            is_admin_user = user.has_group('hr.group_hr_manager')
            if is_admin_user:
                record.is_can_edit = True
            else:
                if hasattr(record, 'x_approval_status') and record.x_approval_status:

                    status_selection = record.fields_get(allfields=['x_approval_status'])['x_approval_status'][
                        'selection']

                    if len(status_selection) >= 3:
                        last_status = status_selection[-1][0]

                        if record.x_approval_status == last_status:
                            record.is_can_edit = True
                        else:
                            record.is_can_edit = False
                    else:
                        record.is_can_edit = False
                else:
                    record.is_can_edit = True

    @api.depends('user_id')
    def _compute_is_non_hr_admin(self):
        for record in self:
            user = self.env.user
            is_admin_user = user.has_group('hr.group_hr_manager')
            if not is_admin_user:
                record.is_non_hr_admin = True
            else:
                record.is_non_hr_admin = False

    @api.depends('histori_jabatan_ids.hr_branch_id')
    def _compute_hr_branch_id(self):
        for emp in self:
            all_histories = emp.histori_jabatan_ids.filtered(lambda h: h.tmt_date)
            if all_histories:
                latest = all_histories.sorted(key=lambda h: h.tmt_date, reverse=True)[0]
                emp.hr_branch_id = latest.hr_branch_id
            else:
                emp.hr_branch_id = False

    @api.depends('date_of_birth')
    def _compute_field_usia(self):
        today = date.today()
        for record in self:
            if record.date_of_birth:
                born = record.date_of_birth

                age_years = today.year - born.year
                age_months = today.month - born.month
                age_days = today.day - born.day

                if age_months < 0 or (age_months == 0 and age_days < 0):
                    age_years -= 1
                    age_months += 12

                if age_days < 0:
                    previous_month = (today.month - 1) if today.month > 1 else 12
                    age_months -= 1
                    if age_months < 0:
                        age_months += 12
                        age_years -= 1

                record.usia = f"{age_years} tahun {age_months} bulan"
            else:
                record.usia = '-'

    def name_get(self):
        res = []
        use_sppd = self.env.context.get('use_sppd_get')
        for rec in self:
            name = rec.name
            if use_sppd:
                name = f"{rec.name} - {rec.keterangan_jabatan_id.name or ''}"
            res.append((rec.id, name))
        return res

    @api.constrains('birthday')
    def _check_birthday_valid(self):
        for employee in self:
            if employee.birthday:
                if employee.birthday > fields.Date.today():
                    raise ValidationError(_("Employee's birthday cannot be in the future."))
                min_age = 17
                today = fields.Date.today()
                age = relativedelta(today, employee.birthday).years
                if age < min_age:
                    raise ValidationError(_("Employee must be at least %d years old.") % min_age)

    @api.constrains(
        'first_contract_date')
    def _check_hire_date_valid(self):
        for employee in self:
            if employee.first_contract_date and employee.first_contract_date > fields.Date.today():
                raise ValidationError(_("Hire date cannot be in the future."))

    @api.constrains('first_contract_date', 'departure_date')
    def _check_departure_date_after_hire_date(self):
        for employee in self:
            if employee.first_contract_date and employee.departure_date and employee.departure_date < employee.first_contract_date:
                raise ValidationError(_("Departure date cannot be earlier than hire date."))

    def cron_assign_kelompok_umur(self):
        """
        Cron job untuk memetakan setiap employee (hanya organik & pkwt) ke kelompok umur
        yang sesuai berdasarkan tanggal lahirnya.
        """
        today = fields.Date.today()
        groups = self.env['hr.employee.kelompok.umur'].search([])
        employees = self.search([('employment_type', 'in', ['organik', 'pkwt'])])
        for emp in employees:
            if not emp.date_of_birth:
                emp.kelompok_umur_id = False
                continue

            age = today.year - emp.date_of_birth.year
            try:
                birthday_this_year = emp.date_of_birth.replace(year=today.year)
            except ValueError:
                birthday_this_year = emp.date_of_birth.replace(year=today.year, day=28)
            if today < birthday_this_year:
                age -= 1

            matching_group = groups.filtered(lambda g: g.min_age <= age <= g.max_age)
            if matching_group:
                emp.kelompok_umur_id = matching_group[0].id
                _logger.info("Employee %s assigned to age group %s", emp.name, matching_group[0].name)
            else:
                emp.kelompok_umur_id = False
                _logger.info("Employee %s does not match any age group", emp.name)

        return True

    @api.depends('date_of_birth', 'employment_type')
    def _compute_perkiraan_tanggal_pensiun(self):
        for rec in self:
            if rec.date_of_birth and rec.employment_type in ['organik', 'tad']:
                try:
                    rec.perkiraan_tanggal_pensiun = rec.date_of_birth.replace(
                        year=rec.date_of_birth.year + 56
                    )
                except ValueError:
                    # fallback untuk yang lahir di 29 Februari
                    rec.perkiraan_tanggal_pensiun = rec.date_of_birth.replace(
                        year=rec.date_of_birth.year + 56,
                        day=28
                    )
            else:
                rec.perkiraan_tanggal_pensiun = False

    @api.depends(
        'address_home_id.street',
        'address_home_id.street2',
        'address_home_id.city',
        'address_home_id.state_id',
        'address_home_id.zip'
    )
    def _compute_alamat(self):
        for rec in self:
            if rec.address_home_id:
                parts = []
                if rec.address_home_id.street:
                    parts.append(rec.address_home_id.street)
                if rec.address_home_id.street2:
                    parts.append(rec.address_home_id.street2)
                if rec.address_home_id.city:
                    parts.append(rec.address_home_id.city)
                if rec.address_home_id.state_id:
                    parts.append(rec.address_home_id.state_id.name)
                if rec.address_home_id.zip:
                    parts.append(rec.address_home_id.zip)
                rec.alamat = ", ".join(parts)
            else:
                rec.alamat = ""

    is_first_status = fields.Boolean(
        string="Is First Status?",
        compute='_compute_is_first_status'
    )

    def _compute_is_first_status(self):
        for record in self:
            if hasattr(record, 'x_approval_status') and record.x_approval_status:

                status_selection = record.fields_get(allfields=['x_approval_status'])['x_approval_status']['selection']
                if len(status_selection) >= 1:
                    first_status = status_selection[0][0]
                    record.is_first_status = (record.x_approval_status == first_status)
                else:
                    record.is_first_status = False
            else:
                record.is_first_status = False

    is_admin_user = fields.Boolean(compute='_compute_is_admin_user')
    is_hr_admin_user = fields.Boolean(compute='_compute_is_hr_admin_user')

    @api.depends('user_id')
    def _compute_is_admin_user(self):
        for record in self:
            record.is_admin_user = self.env.user._is_admin

    @api.depends('user_id')
    def _compute_is_hr_admin_user(self):
        for record in self:
            record.is_hr_admin_user = self.env.user.has_group('hr.group_hr_manager')

    is_second_status = fields.Boolean(
        string="Is Second Status?",
        compute='_compute_is_second_status'
    )

    def _compute_is_second_status(self):
        for employee in self:
            if hasattr(employee, 'x_approval_status') and employee.x_approval_status:

                status_selection = self.fields_get(allfields=['x_approval_status'])['x_approval_status']['selection']

                if len(status_selection) >= 3:
                    second_status = status_selection[1][0]
                    if employee.x_approval_status == second_status:
                        employee.is_second_status = True
                    else:
                        employee.is_second_status = False
                else:
                    employee.is_second_status = False
            else:
                employee.is_second_status = False

    def get_active_working_days(self, year, month):
        calendar = self.resource_calendar_id
        if not calendar:
            return 0

        # Get the user's timezone or use UTC as default
        tz_name = self.env.context.get('tz') or 'UTC'
        local_tz = pytz.timezone(tz_name)

        start_date = datetime(year, month, 1)
        end_date = (start_date.replace(day=1) + relativedelta(months=1)) - relativedelta(days=1)

        # Convert to datetime with timezone
        start_dt = local_tz.localize(datetime.combine(start_date, datetime.min.time()))
        end_dt = local_tz.localize(datetime.combine(end_date, datetime.max.time()))

        working_days = calendar.get_work_hours_count(start_dt, end_dt)
        return working_days / calendar.hours_per_day

    def get_number_of_workdays(self, start_date, end_date):
        calendar = self.resource_calendar_id
        if not calendar:
            return 0

        # Get the user's timezone or use UTC as default
        tz_name = self.env.context.get('tz') or 'UTC'
        local_tz = pytz.timezone(tz_name)

        # Convert to datetime with timezone
        start_dt = local_tz.localize(datetime.combine(start_date, datetime.min.time()))
        end_dt = local_tz.localize(datetime.combine(end_date, datetime.max.time()))

        working_duration = calendar.get_work_duration_data(start_dt, end_dt, compute_leaves=False, domain=None)
        return working_duration

    def _update_contract_grade(self):
        for employee in self:
            if employee.employment_type in ['organik', 'pkwt'] and employee.keterangan_jabatan_id:
                contract_name = self.EMPLOYMENT_TYPE_MAPPING.get(employee.employment_type,
                                                                 'Contract').upper() + ' ' + employee.keterangan_jabatan_id.name.upper()
            elif employee.fungsi_penugasan_id:
                contract_name = self.EMPLOYMENT_TYPE_MAPPING.get(employee.employment_type,
                                                                 'Contract').upper() + ' ' + employee.fungsi_penugasan_id.name.upper()
            else:
                contract_name = self.EMPLOYMENT_TYPE_MAPPING.get(employee.employment_type, 'Contract').upper()
            contracts = self.env['hr.contract'].search([
                ('employee_id', '=', employee.id),
                ('name', '=', contract_name),
            ])
            for contract in contracts:
                contract.grade_id = employee.grade_id.id

    @api.model
    def create(self, vals):
        if 'name' in vals and vals.get('name'):
            vals['name'] = vals['name'].title()
        record = super(HrEmployee, self).create(vals)
        record.action_fetch_penilaian_kinerja()
        return record

    def write(self, vals):
        if 'name' in vals and vals.get('name'):
            vals['name'] = vals['name'].title()
        trigger_fetch = False
        if 'nip_organik' in vals or 'nip_pkwt' in vals:
            trigger_fetch = True
        res = super(HrEmployee, self).write(vals)
        if res:
            if trigger_fetch:
                for rec in self:
                    rec.action_fetch_penilaian_kinerja()
            for rec in self:
                message = _("Perubahan pada data karyawan '%s' berhasil disimpan.") % rec.name
                self.env['bus.bus']._sendone(
                    (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                        'simple_notification',
                        {
                            'type': 'success',
                            'title': _('Sukses'),
                            'message': message,
                            'sticky': False,
                        }
                    )
        return res

    def action_fetch_penilaian_kinerja(self):
        """Ambil data dari DB eksternal (tabel kpikar) di SIMKP AGP dan mapping ke penilaian.kinerja."""
        self.ensure_one()

        if self.employment_type in ['organik', 'pkwt']:
            host = 'adhigunaputera.co.id'
            port = 3306
            user = 'adhigun1_odoo'
            password = 'Kartini@2425?'
            database = 'adhigun1_simkp'

            query = None

            if self.employment_type == 'organik':
                query = f"SELECT * FROM kpikar WHERE nip = '{self.nip_organik}'"
            elif self.employment_type == 'pkwt':
                query = f"SELECT * FROM kpikar WHERE nip = '{self.nip_pkwt}'"

            conn = None
            cursor = None
            rows = []
            try:
                conn = mysql.connector.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=database
                )
                cursor = conn.cursor(dictionary=True)
                cursor.execute(query)
                rows = cursor.fetchall()
            except Exception as e:
                pass
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()

            for row in rows:
                # Misalnya row punya struktur:
                # { 'nip': 'P-20.0173.003',
                #   'smt': '2 - 2023',  (contoh semester 2, tahun 2023)
                #   'hasilkuan': 'Baik',
                #   'hasilkua': 'Memuaskan',
                #   ... dll }
                smt_value = row.get('smt', '')  # e.g. "2 - 2023"
                hasilkuan = row.get('hasilkuan', '')
                hasilkua = row.get('hasilkua', '')

                semester_val = ''
                tahun_val = ''
                if ' - ' in smt_value:
                    semester_val, tahun_val = smt_value.split(' - ', 1)

                penilaian_val = (hasilkuan + ' ' + hasilkua).strip()

                existing = self.env['penilaian.kinerja'].search([
                    ('employee_id', '=', self.id),
                    ('tahun', '=', tahun_val),
                    ('semester', '=', semester_val)
                ], limit=1)

                if not existing:
                    self.env['penilaian.kinerja'].create({
                        'employee_id': self.id,
                        'tahun': tahun_val,
                        'semester': semester_val,
                        'penilaian': penilaian_val
                    })

            return True

        else:
            return True

    def request_for_edit(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        email_batch = []
        notifications = []

        for record in self:
            if hasattr(record, 'x_x_hr_employee_line_ids'):
                approval_lines = record.x_x_hr_employee_line_ids.filtered(lambda line: line.x_approver_id).sorted(
                    key=lambda line: line.x_sequence)

                if not approval_lines:
                    continue

                for approval_line in approval_lines:
                    approver = approval_line.x_approver_id
                    if approver:
                        record_url = f"{base_url}/web#id={record.id}&model={record._name}&view_type=form"
                        email_subject = f"Request for Edit HR Document (Employee: {record.name})"
                        email_body = f"""
                        <p>Dear {approver.name},</p>
                        <p>The HR document for <strong>{record.name}</strong> is awaiting your approval for editing.</p>
                        <p>You can review the document by clicking on the following link:</p>
                        <p><a href="{record_url}">Review HR Document</a></p>
                        <p>Best regards,<br/>Your HR Team</p>
                        """
                        email_from = self.env['ir.mail_server'].sudo().search([],
                                                                              limit=1).smtp_user or self.env.user.email

                        email_batch.append({
                            'email_from': email_from,
                            'email_to': approver.email,
                            'subject': email_subject,
                            'body_html': email_body,
                        })

                        notifications.append({
                            'partner_id': approver.partner_id.id,
                            'message': f"Ada permintaan edit record data employee yang perlu di-approve: a/n. {record.name}. Mohon cek email untuk link approval.",
                        })

                        break

                record.x_approval_status = 'Waiting for Approve'

        if email_batch:
            self.env['mail.mail'].sudo().create(email_batch)

        for notif in notifications:
            self.env['bus.bus']._sendone(
                (self._cr.dbname, 'res.partner', notif['partner_id']),
                'simple_notification',
                {
                    'title': "Permintaan Persetujuan",
                    'message': notif['message'],
                    'type': 'warning',
                    'sticky': True,
                }
            )

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        context = self.env.context

        is_admin = self.env.user.has_group('base.group_erp_manager')

        if context.get('show_only_own_employee') and not is_admin:
            args += [('user_id', '=', self.env.uid)]

        return super(HrEmployee, self).search(args, offset=offset, limit=limit, order=order, count=count)

    def cek_duplikasi(self):
        messages = []

        for rec in self:
            name_stripped = rec.name.strip()

            duplikat = rec.search([('name', '=', name_stripped), ('id', '!=', rec.id)])

            if duplikat:
                messages.append(f"Duplikasi ditemukan untuk: {rec.name}")
            else:
                messages.append(f"Tidak ada duplikasi untuk: {rec.name}")

        formatted_message = "\n".join(messages)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Hasil Pengecekan Duplikasi',
                'message': formatted_message,
                'type': 'warning' if any('Duplikasi' in msg for msg in messages) else 'success',
                'sticky': True,
            }
        }

    def _action_open_update_histori_jabatan_wizard(self):
        return {
                'name': 'Update Histori Jabatan',
                'type': 'ir.actions.act_window',
                'res_model': 'hr.employee.history.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_employee_ids': self.ids},
            }

    @api.model
    def cron_contract_expiration_reminder(self):
        today = fields.Date.today()
        reminder_date = today + timedelta(days=30)

        query = """
                SELECT id FROM hr_employee_histori_jabatan
                WHERE tanggal_selesai_kontrak = %s
                AND employment_type != %s
                AND employee_id IS NOT NULL
                """
        self.env.cr.execute(query, (reminder_date, 'organik'))
        result_ids = self.env.cr.fetchall()
        record_ids = [r[0] for r in result_ids]

        if not record_ids:
            return

        records = self.env['hr.employee.histori.jabatan'].browse(record_ids)
        records.read(['employee_id', 'tanggal_selesai_kontrak'])

        email_batch = []

        for record in records:
            employee = record.employee_id
            if employee.work_email:
                subject = f"Peringatan: Kontrak Anda Akan Berakhir untuk {employee.name}"
                body = f"""
                            Yth. {employee.name},<br/><br/>
                            Ini adalah pengingat bahwa kontrak kerja Anda akan berakhir pada tanggal {record.tanggal_selesai_kontrak}.<br/><br/>
                            Mohon pastikan untuk melakukan proses perpanjangan atau tindakan lainnya sesuai kebutuhan sebelum tanggal tersebut.<br/><br/>
                            Hormat kami,<br/>
                            Departemen HR
                        """
                email_batch.append({
                    'subject': subject,
                    'body_html': body,
                    'email_to': employee.work_email,
                    'email_from': self.env.user.email or 'hr@example.com',
                })
            else:
                _logger.warning(f"Employee {employee.name} does not have a valid work_email. Email not sent.")

        if email_batch:
            self.env['mail.mail'].sudo().create(email_batch)

    @api.model
    def cron_sertification_training_expiration_reminder(self):
        today = fields.Date.today()
        reminder_date = today + timedelta(days=30)

        query = """
                SELECT id FROM hr_employee_sertifikasi_pelatihan
                WHERE certification_end_date = %s
                AND employee_id IS NOT NULL
                """
        self.env.cr.execute(query, (reminder_date,))
        result_ids = self.env.cr.fetchall()
        record_ids = [r[0] for r in result_ids]

        if not record_ids:
            return

        records = self.env['hr.employee.sertifikasi.pelatihan'].browse(record_ids)
        records.read(['employee_id', 'certification_end_date'])

        email_batch = []

        for record in records:
            employee = record.employee_id
            if employee.work_email:
                subject = f"Peringatan: Sertifikasi Pelatihan Anda Akan Berakhir untuk {employee.name}"
                body = f"""
                    Yth. {employee.name},<br/><br/>
                    Ini adalah pengingat bahwa sertifikasi pelatihan Anda akan berakhir pada tanggal {record.certification_end_date}.<br/><br/>
                    Mohon pastikan untuk melakukan proses perpanjangan atau tindakan lainnya sesuai kebutuhan sebelum tanggal tersebut.<br/><br/>
                    Hormat kami,<br/>
                    Departemen HR
                """
                email_batch.append({
                    'subject': subject,
                    'body_html': body,
                    'email_to': employee.work_email,
                    'email_from': self.env.user.email or 'hr@example.com',
                })
            else:
                _logger.warning(
                    f"Pegawai {employee.name} tidak memiliki work_email yang valid. Email tidak dikirim."
                )

        if email_batch:
            self.env['mail.mail'].sudo().create(email_batch)

    @api.model
    def notify_upcoming_53(self):
        """Notify employees nearing age 53"""
        today = date.today()
        target_date = today + timedelta(days=90)  # 3 months from now
        employees = self.search([
            ('date_of_birth', '!=', False),
            ('employment_type', 'in', ['organik', 'tad']),
        ])

        for emp in employees:
            if emp.date_of_birth:
                try:
                    target_age_date = emp.date_of_birth.replace(year=emp.date_of_birth.year + 53)

                except ValueError:
                    target_age_date = emp.date_of_birth.replace(
                        year=emp.date_of_birth.year + 53,
                        day=28
                    )

                if target_date >= target_age_date > today:
                    mail_values = {
                        'subject': "Pemberitahuan: Usia Mendekati 53 Tahun",
                        'email_to': emp.work_email or 'hr@example.com',
                        'body_html': f"""
                            <p>Dear <strong>{emp.name}</strong>,</p>
                            <p>Dalam 3 bulan, Anda akan memasuki usia 53 tahun.</p>
                            <p>Silakan persiapkan dokumen atau tindakan yang diperlukan.</p>
                            <p>Hormat kami,</p>
                            <p>Tim HR</p>
                            """,
                        'auto_delete': True,
                    }
                    self.env['mail.mail'].create(mail_values)

    @api.model
    def notify_upcoming_5_year_contract(self):
        today = date.today()
        target_date = today + timedelta(days=60)  # H-2 bulan dari hari ini

        employees = self.search([('histori_jabatan_ids', '!=', False)])
        if not employees:
            return

        histories = self.env['hr.employee.histori.jabatan'].search([
            ('employee_id', 'in', employees.ids)
        ])

        histories_by_employee = {}
        for history in histories:
            histories_by_employee.setdefault(history.employee_id.id, []).append(history)

        for emp in employees:
            emp_histories = histories_by_employee.get(emp.id, [])
            for history in emp_histories:
                if history.employment_type == 'pkwt' and history.tanggal_selesai_kontrak:
                    contract_end_date = history.tanggal_selesai_kontrak
                    start_date = history.tmt_date
                    if start_date:
                        duration = contract_end_date - start_date
                        if duration.days >= (5 * 365):  # 5 tahun perkiraan (365 hari per tahun)
                            # Jika kontrak mendekati habis dalam H-2 bulan
                            if target_date >= contract_end_date > today:
                                email_to = emp.work_email or 'hr@example.com'
                                if not emp.work_email:
                                    _logger.warning(
                                        f"Karyawan {emp.name} tidak memiliki email. Menggunakan email default."
                                    )
                                mail_values = {
                                    'subject': "Pemberitahuan: Kontrak Mendekati Masa 5 Tahun",
                                    'email_to': email_to,
                                    'body_html': f"""
                                        <p>Dear <strong>{emp.name}</strong>,</p>
                                        <p>Dalam 2 bulan, kontrak Anda akan memasuki masa 5 tahun.</p>
                                        <p>Mohon mempersiapkan langkah yang diperlukan terkait kontrak kerja Anda.</p>
                                        <p>Hormat kami,</p>
                                        <p>Tim HR</p>
                                    """,
                                    'auto_delete': True,
                                }
                                try:
                                    self.env['mail.mail'].create(mail_values)
                                    _logger.info(
                                        f"Email notifikasi kontrak hampir 5 tahun dikirim ke {emp.name} ({email_to})."
                                    )
                                except Exception as e:
                                    _logger.error(f"Gagal mengirim email ke {emp.name}: {str(e)}")

    def create_historic_records(self):
        employees = self.search([])
        current_year = datetime.now().year
        current_month = datetime.now().month

        for employee in employees:
            if not employee.histori_jabatan_ids:
                employment_type = employee.employment_type
                tmt_date = datetime(current_year, random.randint(1, min(3, current_month)), random.randint(1, 28))
                masa_jabatan = str(random.choice(["1 bulan", "3 bulan", "6 bulan", "1 tahun"]))

                history_values = {
                    'employment_type': employment_type,
                    'tmt_date': tmt_date,
                    'masa_jabatan_bulan': masa_jabatan,
                    'tanggal_pengangkatan': tmt_date,
                    'tanggal_selesai_kontrak': None if employment_type == 'organik' else tmt_date + timedelta(days=365),
                    'employee_id': employee.id
                }

                self.env['hr.employee.histori.jabatan'].create(history_values)

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields, attributes)
        hide_list = [
            'cabang_kerja',
            'employee_type',
            'employment_type_related',
            'histori_jabatan_ids',
            'hr_employee_ijazah_ids',
            'hr_employee_hukuman_ids',
            'hr_employee_sertifikasi_pelatihan_ids',
            'hr_employee_unit_id',
            'keterangan_jabatan',
            'jabatan',
            'cabang_kerja',
            'cabang_kerja_id',
            'keterangan_vendor_tad',
            'id_attachment_id',
            'message_attachment_count',
            'message_main_attachment_id',
            'passport_attachment_id',
            'image_1024',
            'image_128',
            'image_1920',
            'image_256',
            'image_512',
            'id_expiry_date',
            'passport_expiry_date',
            'date_of_birth',
            'employee_skill_ids',
            'nip_organik',
            'nip_pkwt',
            'skill_ids',
            'active',
            'message_needaction',
            'message_needaction_counter',
            'activity_ids',
            'activity_calendar_event_id',
            'activity_date_deadline',
            'activity_exception_decoration',
            'activity_exception_icon',
            'activity_state',
            'activity_summary',
            'activity_type_icon',
            'activity_type_id',
            'activity_user_id',
            'last_activity',
            'last_activity_time',
            'my_activity_date_deadline',
            'work_permit_scheduled_activity',
            'lang',
        ]
        for field in hide_list:
            if res.get(field):
                res[field]['searchable'] = False
        return res

    def _bulk_upload_helper(self, attachment_ids, field_name, model_name=None, field_type='binary'):
        """
        Generic function for handling bulk file uploads.

        Args:
            - attachment_ids (list): List of attachments being uploaded.
            - field_name (str): The target field name where attachments will be saved.
            - model_name (str, optional): Model name if the field belongs to a related model.
            - field_type (str, optional): Type of field ('binary' or 'many2many'). Default is 'binary'.
        """
        if not attachment_ids:
            raise UserError(_("No files uploaded."))

        MAX_FILE_SIZE_MB = 5
        MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

        for attachment in attachment_ids:
            if attachment.file_size > MAX_FILE_SIZE_BYTES:
                message = _("File '%s' (%s MB) terlalu besar. Ukuran maksimal yang diizinkan adalah %sMB.") % \
                          (attachment.name,
                           round(attachment.file_size / (1024 * 1024), 2),
                           MAX_FILE_SIZE_MB)
                raise UserError(message)

            name, _ = attachment.name.rsplit('.', 1) if '.' in attachment.name else (attachment.name, '')
            employee = self.env['hr.employee'].search([('name', '=ilike', name)], limit=1)

            if not employee:
                _logger.warning(f"Employee not found for {attachment.name}, skipping upload.")
                continue

            if model_name:
                record = self.env[model_name].search([('employee_id', '=', employee.id)], limit=1)
                if not record:
                    record = self.env[model_name].create({'employee_id': employee.id})
                target_obj = record
            else:
                target_obj = employee

            # Save attachment based on field type
            if field_type == 'many2many':
                target_obj.write({field_name: attachment.ids})
            else:  # Default to Binary
                target_obj.write({field_name: attachment.datas})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'Attachments uploaded successfully for {field_name}.',
                'sticky': False,
            }
        }

    def bulk_upload_ijazah(self, attachment_ids):
        return self._bulk_upload_helper(attachment_ids, 'ijazah_attachment_id', 'hr.employee.ijazah', field_type='many2many')

    def bulk_upload_kk(self, attachment_ids):
        return self._bulk_upload_helper(attachment_ids, 'attachment_doc_kk', field_type='binary')

    def bulk_upload_ktp(self, attachment_ids):
        return self._bulk_upload_helper(attachment_ids, 'attachment_doc_ktp', 'hr.employee.family', field_type='binary')

    def bulk_upload_sertifikat(self, attachment_ids):
        return self._bulk_upload_helper(attachment_ids, 'certificate_attachment_id', 'hr.employee.sertifikasi.pelatihan', field_type='many2many')

    def bulk_upload_npwp(self, attachment_ids):
        return self._bulk_upload_helper(attachment_ids, 'npwp_attachment', field_type='binary')

    def bulk_upload_kis(self, attachment_ids):
        return self._bulk_upload_helper(attachment_ids, 'kis_attachment', field_type='binary')

    def bulk_upload_foto(self, attachment_ids):
        return self._bulk_upload_helper(attachment_ids, 'image_1920', field_type='binary')