from odoo import models, fields, api, _
from num2words import num2words
import logging
_logger = logging.getLogger(__name__)
import mysql.connector
from datetime import datetime
from odoo.exceptions import UserError, ValidationError

class NotaDinas(models.Model):
    _name = 'account.keuangan.nota.dinas'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Nota Dinas'

    name = fields.Char(string='Nota Dinas Number', required=True, copy=False, readonly=True, default=lambda self: _('Nomor Nota Dinas akan terisi otomatis...'), tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
    ], default='draft', tracking=True)
    
    kepada = fields.Char(string='Kepada YTH.', tracking=True)
    pengirim = fields.Char(string='Pengirim', tracking=True)
    perihal = fields.Text(string='Perihal', tracking=True)
    kata_pengantar = fields.Text(
        string='Kata Pengantar',
        compute='_compute_kata_pengantar',
        store=True
    )

    tanggal_pengajuan = fields.Date(string='Tanggal Pengajuan', required=True, tracking=True, default=fields.Date.context_today)
    tembusan = fields.Char(string='Tembusan', tracking=True)
    keterangan = fields.Text(string='Keterangan', tracking=True)
    disposisi = fields.Text(string='Disposisi', tracking=True)
    
    nota_dinas_line_ids = fields.One2many('account.keuangan.nota.dinas.line', 'nota_dinas_id', string='Nota Dinas Lines')

    total = fields.Float(string='Total', compute='_compute_total', store=True, tracking=True)
    total_terbilang = fields.Char(string='Total Terbilang', compute='_compute_total_terbilang', tracking=True)

    # @api.depends('nota_dinas_line_ids.total_harga')
    # def _compute_total(self):
    #     for record in self:
    #         record.total = sum(line.total_harga for line in record.nota_dinas_line_ids)

    @api.depends('total')
    def _compute_total_terbilang(self):
        for record in self:
            total_terbilang = num2words(record.total, lang='id').title().replace('-', ' ')
            currency_name = "Rupiah"  # Ubah ke mata uang yang sesuai jika perlu
            record.total_terbilang = f"{total_terbilang} {currency_name}"


    # @api.model
    # def create(self, vals):
    #     if vals.get('name', _('New')) == _('New'):            
    #         # Get the date details
    #         date_str = vals.get('date', fields.Date.context_today(self))
    #         date_obj = fields.Date.from_string(date_str) if isinstance(date_str, str) else date_str
    #         year = date_obj.strftime('%Y')
    #         month = int(date_obj.strftime('%m'))
    #         roman_month = self._to_roman(month)
            
    #         # Get the default branch of the user
    #         user = self.env.user
    #         default_branch = user.branch_id[0] if user.branch_id else None
    #         branch_code = default_branch.code if default_branch else 'KOSONG'
            
    #         # Get the department code of the user
    #         # department_code = user.department_id.kode if user.department_id else 'NO_DEPT'
            
    #         # Generate the custom sequence number
    #         sequence_code = self.env['ir.sequence'].next_by_code('sequence.nota.dinas') or '0000'

    #         # Generate the custom sequence
    #         vals['name'] = f'{sequence_code}/ND-{branch_code}/{roman_month}/AGP-{year}'
        
    #     return super(NotaDinas, self).create(vals)

    # @staticmethod
    # def _to_roman(month):
    #     roman = {
    #         1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI',
    #         7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X', 11: 'XI', 12: 'XII'
    #     }
    #     return roman.get(month, '')

    # ========================================================
    # INTEGRATION AMS
    # ========================================================

    @api.model
    def create(self, vals):
        is_umum = vals.get('is_umum', False)

        # Tentukan suffix dan kode masalah berdasarkan jenis
        if is_umum:
            suffix = f"DIVSDM-{fields.Date.today().year}"
            kode_masalah = '109'
            like_suffix = 'DIVSDM'
        else:
            suffix = f"AGP-{fields.Date.today().year}"
            kode_masalah = '205'
            like_suffix = 'AGP'

        sql_config = self.env['ams.sql.config'].search([
            ('type', '=', 'direct_sql'),
            ('name', 'ilike', 'AGP')
        ], limit=1)

        if not sql_config:
            raise ValidationError("Konfigurasi AGP Odoo x AMS tidak dapat ditemukan! Silakan hubungi Administrator.")

        connection = None
        try:
            connection = mysql.connector.connect(
                host=sql_config.host,
                port=sql_config.port,
                user=sql_config.user,
                password=sql_config.password,
                database=sql_config.database
            )
            cursor = connection.cursor(dictionary=True)

            # Ambil no_agenda terakhir berdasarkan suffix tipe
            query = f"""
                SELECT buat_tgl, no_agenda, no_nd 
                FROM nota_dinas 
                WHERE no_nd LIKE '%%{like_suffix}%%'
                ORDER BY buat_tgl DESC 
                LIMIT 1
            """
            cursor.execute(query)
            result = cursor.fetchone()

            if result and result['no_agenda'] is not None:
                last_no_agenda = int(result['no_agenda'])
            else:
                last_no_agenda = 0

            next_no_agenda = last_no_agenda + 1
            current_date = fields.Date.today()
            roman_month = self._to_roman(current_date.month)
            year = current_date.year

            vals['name'] = f"{next_no_agenda:05d}/{kode_masalah}/{roman_month}/{suffix}"

        except mysql.connector.Error as err:
            raise ValidationError("Terjadi kesalahan saat menghubungi AMS. Silakan coba kembali dalam beberapa saat lagi.")
        finally:
            if connection and connection.is_connected():
                connection.close()

        # Create record
        record = super(NotaDinas, self).create(vals)

        # Simpan ke MySQL
        try:
            connection = mysql.connector.connect(
                host=sql_config.host,
                port=sql_config.port,
                user=sql_config.user,
                password=sql_config.password,
                database=sql_config.database
            )
            cursor = connection.cursor()
            insert_query = """
                INSERT INTO nota_dinas (buat_tgl, no_agenda, no_nd, kode_masalah)
                VALUES (NOW(), %s, %s, %s)
            """
            cursor.execute(insert_query, (next_no_agenda, record.name, kode_masalah))
            connection.commit()

        except mysql.connector.Error as err:
            raise ValidationError(f"Terjadi kesalahan saat mengirimkan nomor Nota Dinas ke AMS: {err}")
        finally:
            if connection and connection.is_connected():
                connection.close()

        # Nodin tahap dua
        if not record.is_umum:
            self.env['account.keuangan.nota.dinas.bod'].sudo().create({
                'tanggal_pengajuan': record.tanggal_pengajuan or fields.Date.today(),
                'keterangan': record.keterangan or '',
                'periode_kkhc': record.periode_kkhc or fields.Date.today(),
                'perihal': record.perihal or '',
                'kata_pengantar': record.kata_pengantar or '',
            })
            self.env.cr.commit()

        return record

    def _to_roman(self, num):
        roman_numerals = {
            1: 'I', 2: 'II', 3: 'III', 4: 'IV',
            5: 'V', 6: 'VI', 7: 'VII', 8: 'VIII',
            9: 'IX', 10: 'X', 11: 'XI', 12: 'XII'
        }
        return roman_numerals.get(num, '')
    
    # ========================================================

    @api.model
    def action_confirm(self):
        for nota_dinas in self:
            if nota_dinas.state == 'draft':
                # Change state to posted
                nota_dinas.state = 'posted'
                # Optionally, add any other logic here
                sequence_code = self.env['ir.sequence'].next_by_code('account.keuangan.nota.dinas.sequence') or '0000'
                nota_dinas.name = sequence_code  
        return True

    @api.model
    def action_print(self):
        return self.env.ref('agp_keuangan_ib.report_invoice').report_action(self)


class NotaDinasLines(models.Model):
    _name = 'account.keuangan.nota.dinas.line'
    _description = 'Nota Dinas Lines'

    nota_dinas_id = fields.Many2one('account.keuangan.nota.dinas', string='Nota Dinas', required=True)
    kode_anggaran_id = fields.Many2one( 
        'account.keuangan.kode.anggaran',
        string='Kode Anggaran',
        required=True,
    )
    # Field untuk menampilkan deskripsi berdasarkan Kode Anggaran yang dipilih
    deskripsi = fields.Text(string='Deskripsi Anggaran', readonly=True)

     # Field untuk menampilkan Account Code berdasarkan Kode Anggaran yang dipilih
    account_code_id = fields.Many2one('account.account', string='Account Code', readonly=True)

    branch_ids = fields.Many2one('res.branch', string='Cabang Terkait')
    uraian = fields.Text(string='Uraian Kebutuhan')
    total_harga = fields.Float(string='Total Harga', store=True)
    #total_terbilang = fields.Char(string='Total Terbilang', compute='_compute_total_terbilang')
    
    @api.onchange('kode_anggaran_id')
    def _onchange_kode_anggaran_id(self):
        if self.kode_anggaran_id:
            # Mengisi deskripsi dan account_code_id dari Kode Anggaran yang dipilih
            self.deskripsi = self.kode_anggaran_id.deskripsi
            self.account_code_id = self.kode_anggaran_id.account_code_id
            # self.unit_penempatan_id = self.kode_anggaran_id.unit_penempatan_id
        else:
            # Kosongkan field jika tidak ada Kode Anggaran yang dipilih
            self.deskripsi = False
            self.account_code_id = False
            # self.unit_penempatan_id = False


    @api.model
    def create(self, vals):
        if vals.get('kode_anggaran_id'):
            kode_anggaran = self.env['account.keuangan.kode.anggaran'].browse(vals['kode_anggaran_id'])
            vals.update({
                'deskripsi': kode_anggaran.deskripsi,
                'account_code_id': kode_anggaran.account_code_id.id,
            })
        return super(NotaDinasLines, self).create(vals)


    def write(self, vals):
        if vals.get('kode_anggaran_id'):
            kode_anggaran = self.env['account.keuangan.kode.anggaran'].browse(vals['kode_anggaran_id'])
            vals.update({
                'deskripsi': kode_anggaran.deskripsi,
                'account_code_id': kode_anggaran.account_code_id.id,
                # 'unit_penempatan_id': kode_anggaran.unit_penempatan_id.id
            })
        return super(NotaDinasLines, self).write(vals)