from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class AsuransiKaryawan(models.Model):
    _name = 'asuransi.karyawan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Asuransi Karyawan'

    name = fields.Char('Nama Asuransi', copy=False, readonly=True, default="New", help="Nomor unik internal untuk polis asuransi karyawan, terisi otomatis.")
    nomor_polis = fields.Char(required=True, help="Nomor polis resmi yang dikeluarkan oleh provider/perusahaan asuransi.")
    periode_polis = fields.Date(required=True, help="Tanggal akhir periode polis asuransi ini.")
    attachment_file = fields.Binary('Upload Polis', help="Unggah file scan dokumen polis asuransi di sini.")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('aktif', 'Aktif'),
        ('expired', 'Expired')
    ], string="Status", default='draft', tracking=True)
    jumlah_peserta = fields.Integer(string="Jumlah Peserta", compute="_compute_jumlah_peserta", store=True, help="Total jumlah karyawan yang terdaftar sebagai peserta dalam polis ini.")
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        readonly=True
    )
    total_biaya = fields.Monetary(string="Total Biaya", compute="_compute_total_biaya",
                                  currency_field='currency_id', store=True)
    company_id = fields.Many2one(
        'res.company', string="Company", required=True,
        default=lambda self: self.env.company
    )
    line_peserta_ids = fields.One2many('asuransi.karyawan.line.peserta', 'asuransi_karyawan_id', ondelete='cascade')
    line_invoice_ids = fields.One2many('asuransi.karyawan.line.invoice', 'asuransi_karyawan_id', ondelete='cascade')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('asuransi.karyawan') or 'New'
        return super(AsuransiKaryawan, self).create(vals)

    @api.constrains('nomor_polis')
    def _check_unique_polis(self):
        for rec in self:
            if self.search_count([('nomor_polis', '=', rec.nomor_polis), ('id', '!=', rec.id)]) > 0:
                raise ValidationError(_("Nomor Polis %s sudah digunakan!") % rec.nomor_polis)

    @api.depends('line_peserta_ids')
    def _compute_jumlah_peserta(self):
        for rec in self:
            rec.jumlah_peserta = len(rec.line_peserta_ids)

    @api.depends('line_invoice_ids.biaya')
    def _compute_total_biaya(self):
        for rec in self:
            rec.total_biaya = sum(rec.line_invoice_ids.mapped('biaya'))

    def action_confirm(self):
        for record in self:
            if not record.nomor_polis:
                raise UserError(
                    _("Nomor Polis belum diisi. Harap lengkapi terlebih dahulu sebelum mengaktifkan polis."))
            if not record.periode_polis:
                raise UserError(_("Periode Polis (tanggal) belum diisi. Harap lengkapi terlebih dahulu."))
            if not record.line_peserta_ids:
                raise UserError(_("Polis tidak bisa diaktifkan jika belum ada satu pun peserta terdaftar."))
            record.write({'state': 'aktif'})
        return True

    def action_expire(self):
        for rec in self:
            rec.state = 'expired'

    def action_set_to_draft(self):
        for rec in self:
            rec.state = 'draft'


class AsuransiKaryawanLinePeserta(models.Model):
    _name = 'asuransi.karyawan.line.peserta'
    _description = 'Line Peserta Asuransi Karyawan'

    employee_id = fields.Many2one('hr.employee', string='Peserta', domain=[('active','=',True),('direksi', '=', False)], help="Pilih karyawan yang menjadi peserta polis asuransi ini.")
    date = fields.Date('Tanggal', help="Tanggal pencatatan atau tanggal efektif peserta bergabung (jika berbeda dari 'Tanggal Efektif' polis).")
    email_from = fields.Char('Email dari')
    nomor_sertifikat = fields.Char(help="Nomor sertifikat individu untuk peserta ini (jika ada).")
    entity = fields.Char()
    cabang = fields.Char(related='employee_id.hr_branch_id.name', string='Cabang')
    nama_jabatan = fields.Char(related='employee_id.jabatan_komplit_id.name', string='Nama Jabatan')
    jenis_kelamin = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], related='employee_id.gender')
    tanggal_lahir = fields.Date(related='employee_id.date_of_birth')
    usia = fields.Char(string="Usia", related='employee_id.usia')
    tanggal_efektif = fields.Date()
    tanggal_berakhir = fields.Date()
    asuransi_karyawan_id = fields.Many2one('asuransi.karyawan', string='Asuransi Karyawan')


class AsuransiKaryawanLineInvoice(models.Model):
    _name = 'asuransi.karyawan.line.invoice'
    _description = 'Line Invoice Asuransi Karyawan'

    name = fields.Char()
    invoice_date = fields.Date('Tanggal Invoice')
    invoice_id = fields.Many2one('account.move', domain=[('move_type', '=', 'out_invoice')])
    keterangan = fields.Char('Keterangan')
    biaya = fields.Float('Biaya')
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        readonly=True
    )
    asuransi_karyawan_id = fields.Many2one('asuransi.karyawan', string='Asuransi Karyawan')


class AsuransiDireksi(models.Model):
    _name = 'asuransi.direksi'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Asuransi Direksi'

    name = fields.Char('Nama Asuransi', copy=False, readonly=True, default="New")
    nomor_polis = fields.Char(required=True)
    periode_polis = fields.Date(required=True)
    attachment_file = fields.Binary('Upload Polis')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('aktif', 'Aktif'),
        ('expired', 'Expired')
    ], string="Status", default='draft', tracking=True)
    jumlah_peserta = fields.Integer(string="Jumlah Peserta", compute="_compute_jumlah_peserta", store=True)
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        readonly=True
    )
    total_biaya = fields.Monetary(string="Total Biaya", compute="_compute_total_biaya",
                                  currency_field='currency_id', store=True)
    company_id = fields.Many2one(
        'res.company', string="Company", required=True,
        default=lambda self: self.env.company
    )
    line_peserta_ids = fields.One2many('asuransi.direksi.line.peserta', 'asuransi_direksi_id', ondelete='cascade')
    line_invoice_ids = fields.One2many('asuransi.direksi.line.invoice', 'asuransi_direksi_id', ondelete='cascade')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('asuransi.direksi') or 'New'
        return super(AsuransiDireksi, self).create(vals)

    @api.constrains('nomor_polis')
    def _check_unique_polis(self):
        for rec in self:
            if self.search_count([('nomor_polis', '=', rec.nomor_polis), ('id', '!=', rec.id)]) > 0:
                raise ValidationError(_("Nomor Polis %s sudah digunakan!") % rec.nomor_polis)

    @api.depends('line_peserta_ids')
    def _compute_jumlah_peserta(self):
        for rec in self:
            rec.jumlah_peserta = len(rec.line_peserta_ids)

    @api.depends('line_invoice_ids.biaya')
    def _compute_total_biaya(self):
        for rec in self:
            rec.total_biaya = sum(rec.line_invoice_ids.mapped('biaya'))

    def action_confirm(self):
        for rec in self:
            rec.state = 'aktif'

    def action_expire(self):
        for rec in self:
            rec.state = 'expired'

    def action_set_to_draft(self):
        for rec in self:
            rec.state = 'draft'


class AsuransiDireksiLinePeserta(models.Model):
    _name = 'asuransi.direksi.line.peserta'
    _description = 'Line Peserta Asuransi Direksi'

    employee_id = fields.Many2one('hr.employee', string='Peserta', domain=[('active','=',True),('direksi', 'in', ['dir1', 'dir2', 'dir3', 'dir4'])])
    date = fields.Date('Tanggal')
    email_from = fields.Char('Email dari')
    nomor_sertifikat = fields.Char()
    entity = fields.Char()
    cabang = fields.Char(related='employee_id.hr_branch_id.name', string='Cabang')
    nama_jabatan = fields.Char(related='employee_id.jabatan_komplit_id.name', string='Nama Jabatan')
    jenis_kelamin = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], related='employee_id.gender')
    tanggal_lahir = fields.Date(related='employee_id.date_of_birth')
    usia = fields.Char(string="Usia", related='employee_id.usia')
    tanggal_efektif = fields.Date()
    tanggal_berakhir = fields.Date()

    asuransi_direksi_id = fields.Many2one('asuransi.direksi', string='Asuransi Direksi')


class AsuransiDireksiLineInvoice(models.Model):
    _name = 'asuransi.direksi.line.invoice'
    _description = 'Line Invoice Asuransi Direksi'

    name = fields.Char()
    invoice_date = fields.Date('Tanggal Invoice')
    invoice_id = fields.Many2one('account.move', domain=[('move_type', '=', 'out_invoice')])
    keterangan = fields.Char('Keterangan')
    biaya = fields.Float('Biaya')
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        readonly=True
    )
    asuransi_direksi_id = fields.Many2one('asuransi.direksi', string='Asuransi Direksi')