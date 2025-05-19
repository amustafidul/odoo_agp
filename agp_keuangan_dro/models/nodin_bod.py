from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from num2words import num2words 
import logging
_logger = logging.getLogger(__name__)
import mysql.connector

class AccountKeuanganNotaDinasBoD(models.Model):
    _name = 'account.keuangan.nota.dinas.bod'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Nota Dinas BoD'

    name = fields.Char(string='Nota Dinas Number', required=True, copy=False, readonly=True, default=lambda self: _('New'), tracking=True)
    kepada = fields.Char(string='Kepada YTH.', tracking=True)
    pengirim = fields.Char(string='Pengirim', tracking=True)
    perihal = fields.Text(string='Perihal', tracking=True)
    kata_pengantar = fields.Text(string='Kata Pengantar', compute='_compute_kata_pengantar')
    tanggal_pengajuan = fields.Date(string='Tanggal Pengajuan', required=True, tracking=True)
    tembusan = fields.Char(string='Tembusan', tracking=True)
    keterangan = fields.Text(string='Keterangan', tracking=True)
    total = fields.Float(string='Total', compute='_compute_total', store=True, tracking=True)
    # total_terbilang = fields.Char(string='Total Terbilang', compute='_compute_total_terbilang', tracking=True)
    total_terbilang = fields.Char(string='Total Terbilang', store=True, tracking=True)
    periode_kkhc = fields.Date(string='Tanggal Awal Periode KKHC Terkait')
    kkhc_ids = fields.Many2many(
        'account.keuangan.kkhc', 
        string="KKHC",
        domain="[('is_convertible_to_nodin', '=', True), ('periode_kkhc_start', '=', periode_kkhc)]"
    )
    history_approval_ids = fields.One2many('nodin.approval.line', 'nodin_bod_id', string='List Riwayat Approval')
    document_ids = fields.One2many('nodin.document.line', 'nodin_bod_id', string='List Dokumen Terkait')
    approval_step = fields.Integer(string='Approval Step')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('on_review', 'On Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft')
    amount_total_jumlah_biaya = fields.Float(string='Total Biaya Dinas', compute='_compute_amount_total_jumlah_biaya', store=True)
    monitored_kkhc_ids = fields.One2many('account.keuangan.monitor.kkhc.line', 'nodin_bod_id', string='KKHC Lines', domain=[('is_rejected', '=', False)])
    rejected_monitored_kkhc_ids = fields.One2many('account.keuangan.monitor.kkhc.line', 'nodin_bod_id', string='KKHC Lines', domain=[('is_rejected', '=', True)])
    sifat_nodin = fields.Selection([
        ('prioritas', 'Prioritas'),
        ('non_prioritas', 'Non Prioritas')
    ], string='Sifat', default='non_prioritas')
    tipe_nodin = fields.Selection([
        ('business', 'Usaha'),
        ('common', 'Umum'),
        ('not_set', 'Not Set')
    ], string='Tipe Akun COA Dinas', default='not_set', compute='_compute_tipe_nodin', store=True)
    # kode_masalah_id = fields.Many2one('agp.kode.masalah', string='Kode Masalah', )
    is_not_activity_user = fields.Boolean(string='Not Eligible', compute='_compute_is_not_activity_user', store=True)
    disposisi_pertama = fields.Text(string='Disposisi Usaha ke Dir Ops', tracking=True)
    disposisi_kedua = fields.Text(string='Disposisi Dir Ops ke Dir Keu', tracking=True)
    kepada_id = fields.Many2one('hr.employee.keterangan.jabatan', string='Kepada', tracking=True, compute='_compute_kepada_pengirim', store=True)
    pengirim_id = fields.Many2one('hr.employee.keterangan.jabatan', string='Pengirim', tracking=True, compute='_compute_kepada_pengirim', store=True)
    tembusan_id = fields.Many2one('hr.employee.keterangan.jabatan', string='Tembusan', tracking=True)
    is_tahap_satu = fields.Boolean(string='Tahap Satu?', default=False, store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env['res.currency'].search([('name', '=', 'IDR')], limit=1))
    amount_total_jumlah_biaya_reject = fields.Monetary(string='Total Nota Dinas Reject', compute='_compute_amount_total_jumlah_biaya_reject', store=True, currency_field='currency_id')
    terbilang = fields.Char(string='Terbilang', compute='_compute_rupiah_terbilang')

    def action_check_lines(self):
        if self.monitored_kkhc_ids:
            for line in self.monitored_kkhc_ids:
                print("#========== BEGIN CHECK LINES ==========#")
                print('KKHC No', line.kkhc_id.name)
                print('Cabang', line.branch_id.name)
                print('Kode', line.kode_anggaran_id.kode_anggaran)
                print('COA', line.account_code_id.code)
                print('Subtotal', line.nominal_final)
                print("#========== END CHECK LINES ==========#")
        else:
            monitoreds = self.env['account.keuangan.monitor.kkhc.line'].sudo().search([])
            if monitoreds:
                for line in monitoreds:
                    if line.nodin_bod_id and line.nodin_bod_id.name == self.name:
                        print('self.monitored_kkhc_ids', len(self.monitored_kkhc_ids))
                        print('self.rejected_monitored_kkhc_ids', len(self.rejected_monitored_kkhc_ids))
                    else:
                        pass

    @api.depends('amount_total_jumlah_biaya')
    def _compute_rupiah_terbilang(self):
        for record in self:
            if record.amount_total_jumlah_biaya:
                total_int = int(record.amount_total_jumlah_biaya)
                terbilang = num2words(total_int, lang='id') + " rupiah"
                record.terbilang = terbilang.capitalize()
            else:
                record.terbilang = ""

    @api.depends('tipe_nodin')
    def _compute_kata_pengantar(self):
        for record in self:
            if record.tipe_nodin == 'common':
                record.kata_pengantar = """Sehubungan dengan permintaan KKHC (Kebutuhan Kas Harian Cabang), dengan ini disampaikan agar permintaan KKHC dibawah untuk Biaya Administrasi dan Umum dapat dipenuhi sebagai berikut:"""
            else:
                record.kata_pengantar = """Sehubungan dengan permintaan KKHC (Kebutuhan Kas Harian Cabang), dengan ini disampaikan agar permintaan KKHC dibawah untuk Biaya Usaha dapat dipenuhi sebagai berikut:"""

    def _compute_kepada_pengirim(self):
        for record in self:
            try:
                record.kepada_id = self.env.ref('agp_keuangan_dro.hr_jabatan_dir_keu').id
                record.pengirim_id = self.env.ref('agp_keuangan_dro.hr_jabatan_dir_ops').id
            except ValueError:
                _logger.warning("Ref jabatan tidak ditemukan, cek apakah XML record tersedia di modul yang benar.")

    def action_submit(self):
        if self.name:
            page_number = self.name[:5]
            page_number_int = int(page_number)
            previous_page_number_int = page_number_int - 1
            previous_page_number = str(previous_page_number_int).zfill(len(page_number))

            nodin_id = self.env['account.keuangan.nota.dinas'].sudo().search([
                ('name', 'ilike', previous_page_number)
            ])
            if nodin_id:
                if nodin_id.state != 'approved':
                    raise ValidationError(f'Nota Dinas Tahap Satu atas Nota Dinas Tahap Dua ini belum diverifikasi oleh Kepala Divisi {self.tipe_nodin} terkait. Silakan cek kembali!')

        if not self.monitored_kkhc_ids:
            raise ValidationError('List Nota Dinas tidak boleh kosong. Mohon isi terlebih dahulu!')
        
        for record in self:
            # Enhanced document_ids checking
            if len(record.document_ids) > 1:
                # Keep only the first document and unlink the others
                documents_to_keep = record.document_ids[0]
                documents_to_remove = record.document_ids[1:]
                documents_to_remove.unlink()
            
            # Force state to 'uploaded' if it's 'waiting' and document exists
            if record.document_ids and record.document_ids[0].state == 'waiting':
                record.document_ids[0].write({'state': 'uploaded'})
            
            # if not record.document_ids or any(line.state != 'uploaded' for line in record.document_ids):
            #     raise ValidationError('Dokumen Nota Dinas yang diperlukan belum di-upload, silakan cek terlebih dahulu!')
      
        for record in self:
            if any(line.state == 'rejected' for line in record.document_ids):
                raise ValidationError('Dokumen Nota Dinas belum dirubah setelah di-reject, silakan cek terlebih dahulu!')        

        cek = False
        nodin_model_id = self.env['ir.model'].search([('model', '=', 'account.keuangan.nota.dinas.bod')], limit=1)
        # approval_id = self.env['approval.workflow'].sudo().search([
        #     ('name', '=', 'Nota Dinas BoD'),
        #     ('res_model', '=', nodin_model_id.id)
        # ], limit=1)

        if self.tipe_nodin == 'business':
            approval_id = self.env['approval.workflow'].sudo().search([
                ('name', '=', 'Nota Dinas BOD Usaha'),
                ('res_model', '=', nodin_model_id.id)
            ], limit=1)
        elif self.tipe_nodin == 'common':
            approval_id = self.env['approval.workflow'].sudo().search([
                ('name', '=', 'Nota Dinas BOD Umum'),
                ('res_model', '=', nodin_model_id.id)
            ], limit=1)

        if not approval_id:
            raise ValidationError('Approval setting untuk Nota Dinas BoD tidak ditemukan. Silakan hubungi Administrator.')

        approval_line_id = self.env['approval.workflow.line'].search([
            ('sequence', '=', 1),
            ('workflow_id', '=', approval_id.id),
        ], limit=1)

        if approval_line_id.user_id.id == self._uid:
            cek = True
        else:
            raise ValidationError('Role berjenjang untuk approval Nota Dinas belum di-setting. Silakan hubungi Administrator.')

        if cek == True:
            first_user = False
            if self.activity_ids:
                for x in self.activity_ids.filtered(lambda x: x.status != 'approved'):
                    if x.user_id.id == self._uid:
                        x.status = 'approved'
                        x.action_done()
                self.state = 'on_review'
                self.approval_step += 1
                level = self.env.user.level
                level_val = dict(self.env['res.users']._fields['level'].selection).get(level, level)
                self.env['nodin.approval.line'].sudo().create({
                    'user_id': self._uid,
                    'date': datetime.now(),
                    'note': f'Data Nota Dinas telah di-submit oleh {self.env.user.name} {level_val}.',
                    'nodin_bod_id': self.id
                })

                approval_line = self.env['approval.workflow.line'].search([
                    ('workflow_id', '=', approval_id.id),
                    ('sequence', '=', self.approval_step + 1),
                    ('level', '=', self.env.user.level)
                ], limit=1)
                user_id_next = approval_line.user_id
                if user_id_next:
                    first_user = user_id_next.id

                    if first_user:
                        self.env['mail.activity'].sudo().create({
                            'activity_type_id': 4,
                            'res_model_id': self.env['ir.model'].sudo().search([('model', '=', 'account.keuangan.nota.dinas.bod')], limit=1).id,
                            'res_id': self.id,
                            'user_id': first_user,
                            'date_deadline': fields.Date.today() + timedelta(days=2),
                            'state': 'planned',
                            'status': 'to_approve',
                            'summary': """Harap segera meng-approve data Nota Dinas BoD."""
                        })

        else:
            raise ValidationError('Hak akses user Anda tidak berhak untuk submit.')
    
    def action_approve(self):
        cek = False
        nodin_model_id = self.env['ir.model'].search([('model', '=', 'account.keuangan.nota.dinas.bod')], limit=1)

        if self.tipe_nodin == 'business':
            approval_id = self.env['approval.workflow'].sudo().search([
                ('name', '=', 'Nota Dinas BOD Usaha'),
                ('res_model', '=', nodin_model_id.id)
            ], limit=1)
        elif self.tipe_nodin == 'common':
            approval_id = self.env['approval.workflow'].sudo().search([
                ('name', '=', 'Nota Dinas BOD Umum'),
                ('res_model', '=', nodin_model_id.id)
            ], limit=1)

        if not approval_id:
            raise ValidationError('Approval setting untuk menu Nota Dinas BoD tidak ditemukan. Silakan hubungi Administrator.')

        approval_line_id = self.env['approval.workflow.line'].search([
            ('sequence', '=', self.approval_step),
            ('workflow_id', '=', approval_id.id),
            ('level', '=', self.env.user.level)
        ], limit=1)

        user_id = approval_line_id.user_id
        if user_id:
            if self._uid == user_id.id:
                cek = True

        if cek == True:
            if approval_id.total_approve == self.approval_step:
                level = self.env.user.level
                level_val = dict(self.env['res.users']._fields['level'].selection).get(level, level)
                level_bod = self.env.user.bod_level
                level_val_bod = dict(self.env['res.users']._fields['bod_level'].selection).get(level_bod, level_bod)
                if level == 'bod':
                    self.env['nodin.approval.line'].create({
                        'user_id': self._uid,
                        'date': datetime.now(),
                        'note': f'Diverifikasi dan di-approve oleh {self.env.user.name} sebagai {level_val} {level_val_bod}.',
                        'nodin_bod_id': self.id
                    })
                else:
                    self.env['nodin.approval.line'].create({
                        'user_id': self._uid,
                        'date': datetime.now(),
                        'note': f'Diverifikasi dan di-approve oleh {self.env.user.name} sebagai {level_val}.',
                        'nodin_bod_id': self.id
                    })

                for doc in self.document_ids.filtered(lambda x: x.state in ('uploaded','rejected')):
                    doc.state = 'verified'

                if self.activity_ids:
                    for x in self.activity_ids.filtered(lambda x: x.status != 'approved'):
                        if x.user_id.id == self._uid:
                            x.status = 'approved'
                            x.sudo().action_done()
                            
            else:
                first_user = False
                user_line_next = self.env['approval.workflow.line'].search([
                    ('sequence', '=', self.approval_step + 1),
                    ('workflow_id', '=', approval_id.id),
                ], limit=1)

                user_id_next = user_line_next.user_id
                if user_id_next:
                    first_user = user_id_next.id 
 
                    if first_user:
                        self.approval_step += 1 
                        self.env['mail.activity'].sudo().create({ 
                            'activity_type_id': 4, 
                            'res_model_id': self.env['ir.model'].sudo().search([('model', '=', 'account.keuangan.nota.dinas.bod')], limit=1).id, 
                            'res_id': self.id, 
                            'user_id': first_user,  
                            'date_deadline': fields.Date.today() + timedelta(days=2), 
                            'state': 'planned', 
                            'status': 'to_approve', 
                            'summary': """Harap segera meng-approve data Nota Dinas BoD.""" 
                        }) 
                        level = self.env.user.level
                        level_val = dict(self.env['res.users']._fields['level'].selection).get(level, level)
                        self.env['nodin.approval.line'].create({ 
                            'user_id': self._uid, 
                            'date': datetime.now(),
                            'note': f'Di-approve oleh {self.env.user.name} sebagai {level_val}', 
                            'nodin_bod_id': self.id 
                        })
                        if self.activity_ids:
                            for x in self.activity_ids.filtered(lambda x: x.status != 'approved'):
                                if x.user_id.id == self._uid:
                                    x.status = 'approved'
                                    x.sudo().action_done()
                    else:
                        raise ValidationError('User role untuk approval Nota Dinas selanjutnya belum di-setting, silakan hubungi Administrator.')

        else:
            raise ValidationError('Hak akses user anda tidak berhak untuk approve.')

    def assign_todo_first_bod(self):
        model_model = self.env['ir.model'].sudo()
        document_setting_model = self.env['approval.workflow.document.setting'].sudo()
        nodin_bod_model_id = model_model.search([('model', '=', 'account.keuangan.nota.dinas.bod')], limit=1)
        nodin_model_id = model_model.search([('model', '=', 'account.keuangan.nota.dinas')], limit=1)
        for res in self:
            res.approval_step = 1
            first_user = False
            approval_id = self.env['approval.workflow'].sudo().search([('res_model', '=', nodin_bod_model_id.id)], limit=1)
            approval_line_id = self.env['approval.workflow.line'].search([
                ('sequence', '=', 1),
                ('workflow_id', '=', approval_id.id),
                # ('level', '=', self.env.user.level)
            ], limit=1)
                                
            if approval_line_id:
                first_user = approval_line_id.user_id.id

            if first_user:
                self.env['mail.activity'].sudo().create({
                    'activity_type_id': 4,
                    'res_model_id': nodin_bod_model_id.id,
                    'res_id': res.id,
                    'user_id': first_user,
                    'date_deadline': fields.Date.today() + timedelta(days=2),
                    'state': 'planned',
                    'summary': "Harap segera men-submit data Nota Dinas Tahap Dua."
                })

            document_list = []
            doc_setting_id = document_setting_model.search([('model_id', '=', nodin_model_id.id)])

            if doc_setting_id:
                for document_line in doc_setting_id:
                    document_list.append((0, 0, {
                        'nodin_bod_id': res.id,
                        'document_id': document_line.id,
                        'state': 'waiting'
                    }))
                res.document_ids = document_list
            else:
                raise ValidationError("Settingan untuk approval dan/atau dokumen belum dikonfigurasi. Silakan hubungi Administrator.")

    # ------------------
    # OLD NODIN BOD
    # ------------------
    # @api.model
    # def create(self, vals):
    #     if vals.get('name', _('New')) == _('New'):            
    #         date_str = vals.get('date', fields.Date.context_today(self))
    #         date_obj = fields.Date.from_string(date_str) if isinstance(date_str, str) else date_str
    #         year = date_obj.strftime('%Y')
    #         month = int(date_obj.strftime('%m'))
    #         roman_month = self._to_roman(month)
            
    #         user = self.env.user
    #         default_branch = user.branch_id[0] if user.branch_id else None
    #         branch_code = default_branch.code if default_branch else 'KOSONG'
    #         sequence_code = self.env['ir.sequence'].next_by_code('sequence.nota.dinas.bod') or '0000'

    #         vals['name'] = f'{sequence_code}/ND-{branch_code}/{roman_month}/AGP-{year}'
        
    #     nodin = super(AccountKeuanganNotaDinasBoD, self).create(vals)
    #     if nodin:
    #         nodin.assign_todo_first_bod()

    #     return nodin
    
    # -------------------
    # NEW NODIN BOD x AMS
    # -------------------
    @api.model
    def create(self, vals):
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

            # Update LIKE ke AGP
            query = """
                SELECT buat_tgl, no_agenda, no_nd 
                FROM nota_dinas 
                WHERE no_nd LIKE '%AGP%' 
                ORDER BY buat_tgl DESC 
                LIMIT 1
            """
            cursor.execute(query)
            result = cursor.fetchone()

            if result:
                last_no_agenda = int(result['no_agenda'])
            else:
                last_no_agenda = 0

            next_no_agenda = last_no_agenda + 1

            masalah_record = self.env['agp.kode.masalah'].search([('uraian', '=', 'Anggaran')], limit=1)
            masalah_kode = masalah_record.kode_masalah if masalah_record else '201'

            current_date = fields.Date.today()
            roman_month = self._to_roman(current_date.month)
            year = current_date.year
            suffix = f"AGP-{year}"

            # Generate nomor
            while True:
                proposed_name = f"{next_no_agenda:05d}/{masalah_kode}/{roman_month}/{suffix}"

                existing = self.env['account.keuangan.nota.dinas.bod'].search([
                    ('name', '=', proposed_name)
                ], limit=1)

                if not existing:
                    vals['name'] = proposed_name
                    break

                next_no_agenda += 1

        except mysql.connector.Error as err:
            raise ValidationError("Terjadi kesalahan saat menghubungi AMS. Silakan coba kembali dalam beberapa saat lagi.")

        finally:
            if connection and connection.is_connected():
                connection.close()

        # Create record
        record = super(AccountKeuanganNotaDinasBoD, self).create(vals)

        # Insert ke AMS
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
            cursor.execute(insert_query, (next_no_agenda, record.name, masalah_kode))
            connection.commit()

        except mysql.connector.Error as err:
            raise ValidationError(f"Terjadi kesalahan saat mengirimkan nomor Nota Dinas ke AMS: {err}")

        finally:
            if connection and connection.is_connected():
                connection.close()

        # Setup approval
        record.assign_todo_first_bod()

        return record
    @api.depends('monitored_kkhc_ids.nominal_pengajuan')
    def _compute_total(self):
        for record in self:
            record.total = sum(line.nominal_pengajuan for line in record.monitored_kkhc_ids)

    @staticmethod
    def _to_roman(month):
        roman = {
            1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI',
            7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X', 11: 'XI', 12: 'XII'
        }
        return roman.get(month, '')

    @api.depends(
        'monitored_kkhc_ids.nominal_final'
    )    
    def _compute_amount_total_jumlah_biaya(self):
        for record in self:
            total = 0.0
            for line in record.monitored_kkhc_ids:
                if line.nominal_final != 0.0:
                    total += line.nominal_final
            record.amount_total_jumlah_biaya = total

    @api.depends(
        'rejected_monitored_kkhc_ids.nominal_final'
    )    
    def _compute_amount_total_jumlah_biaya_reject(self):
        for record in self:
            total = 0.0
            for line in record.rejected_monitored_kkhc_ids:
                if line.nominal_final != 0.0:
                    total += line.nominal_final
            record.amount_total_jumlah_biaya_reject = total

    def read(self, fields=None, load='_classic_read'):
        records = super(AccountKeuanganNotaDinasBoD, self).read(fields, load)

        if not fields or 'amount_total_jumlah_biaya' in fields or 'monitored_kkhc_ids' in fields:
            for record_dict in records:
                record = self.browse(record_dict['id'])
                record._compute_amount_total_jumlah_biaya()
                record._compute_amount_total_jumlah_biaya_reject()
                record._compute_rupiah_terbilang()
                
                _logger.info("---> DEBUG - BoD: Computed amount_total_jumlah_biaya: %s", record.amount_total_jumlah_biaya)

                monitored_kkhc_ids = record_dict.get('monitored_kkhc_ids', [])
                if monitored_kkhc_ids:
                    monitored_lines = self.env['account.keuangan.monitor.kkhc.line'].browse(monitored_kkhc_ids)

                    for line in monitored_lines:
                        _logger.info("---> DEBUG - Line BoD: %s", line.nominal_pengajuan)

        if not fields or 'state' in fields:
            for record_dict in records:
                record = self.browse(record_dict['id'])
                if not record.activity_user_id:
                    record.assign_todo_first_bod()

        if fields:
            for record_dict in records:
                record = self.browse(record_dict['id'])
                record._compute_kepada_pengirim()
                    
        return records

    @api.depends('monitored_kkhc_ids.kode_anggaran_id')
    def _compute_tipe_nodin(self):
        for record in self:
            if not record.monitored_kkhc_ids:
                record.tipe_nodin = 'not_set'
                continue

            all_start_with_5 = all(line.kode_anggaran_id.kode_anggaran.startswith('5') for line in record.monitored_kkhc_ids)
            all_start_with_6 = all(line.kode_anggaran_id.kode_anggaran.startswith('6') for line in record.monitored_kkhc_ids)

            if all_start_with_5:
                record.tipe_nodin = 'business'
            elif all_start_with_6:
                record.tipe_nodin = 'common'
            else:
                record.tipe_nodin = 'not_set'

    @api.depends('activity_user_id')
    def _compute_is_not_activity_user(self):
        for record in self:
            if record.activity_user_id is not self._uid:
                record.is_not_activity_user = True
            else:
                record.is_not_activity_user = False
