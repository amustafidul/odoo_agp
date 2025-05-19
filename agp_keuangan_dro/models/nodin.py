from odoo import models, fields, api
import logging
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)
import re
import pytz
from num2words import num2words

class NotaDinasInheritDro(models.Model):
    _inherit = 'account.keuangan.nota.dinas'

    periode_kkhc = fields.Date(string='Periode KKHC Terkait', default=lambda self: self._default_periode_kkhc())
    kkhc_ids = fields.Many2many(
        'account.keuangan.kkhc', 
        string="KKHC",
        domain="[('is_convertible_to_nodin', '=', True), ('periode_kkhc_start', '=', periode_kkhc)]"
    )
    history_approval_ids = fields.One2many('nodin.approval.line', 'nodin_id', string='List Riwayat Approval')
    document_ids = fields.One2many('nodin.document.line', 'nodin_id', string='List Dokumen Terkait')
    approval_step = fields.Integer(string='Approval Step')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('on_review', 'On Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status')
    amount_total_jumlah_biaya = fields.Monetary(string='Total Nota Dinas', compute='_compute_amount_total_jumlah_biaya', store=True)
    monitored_kkhc_ids = fields.One2many('account.keuangan.monitor.kkhc.line', 'nodin_id', string='KKHC Lines', domain=[('is_rejected', '=', False)])
    rejected_monitored_kkhc_ids = fields.One2many('account.keuangan.monitor.kkhc.line', 'nodin_id', string='KKHC Lines', domain=[('is_rejected', '=', True)])
    sifat_nodin = fields.Selection([
        ('prioritas', 'Prioritas'),
        ('non_prioritas', 'Non Prioritas')
    ], string='Sifat', default='non_prioritas')
    tipe_nodin = fields.Selection([
        ('business', 'Usaha'),
        ('common', 'Umum'),
        ('not_set', 'Belum Ditetapkan Oleh Divisi')
    ], string='Tipe Akun COA Dinas', default='not_set', compute='_compute_tipe_nodin', store=True)
    is_not_activity_user = fields.Boolean(string='Not Eligible', compute='_compute_is_not_activity_user', store=True)
    button_class = fields.Char(compute="_compute_button_class", store=False)
    notes = fields.Text(string='Notes')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env['res.currency'].search([('name', '=', 'IDR')], limit=1))
    kepada_id = fields.Many2one('hr.employee.keterangan.jabatan', string='Kepada', tracking=True, compute='_compute_kepada_pengirim', store=True)
    pengirim_id = fields.Many2one('hr.employee.keterangan.jabatan', string='Pengirim', tracking=True, compute='_compute_kepada_pengirim', store=True)
    tembusan_id = fields.Many2one('hr.employee.keterangan.jabatan', string='Tembusan', tracking=True)
    is_tahap_satu = fields.Boolean(string='Tahap Satu?', default=True, store=True)
    disposisi_kedua = fields.Char('Disp. Kedua')
    is_umum = fields.Boolean(string='Nota Dinas Divisi Umum', required=True, store=True)
    amount_total_jumlah_biaya_reject = fields.Monetary(string='Total Nota Dinas Reject', compute='_compute_amount_total_jumlah_biaya_reject', store=True, currency_field='currency_id')
    terbilang = fields.Char(string='Terbilang', compute='_compute_rupiah_terbilang')

    @staticmethod
    def _default_periode_kkhc():
        tz = pytz.timezone('Asia/Jakarta')
        today = datetime.now(tz).date()
        monday = today - timedelta(days=today.weekday())
        return monday
    
    @api.depends('is_umum')
    def _compute_kata_pengantar(self):
        for record in self:
            if record.is_umum:
                record.kata_pengantar = """Sehubungan dengan permintaan KKHC (Kebutuhan Kas Harian Cabang), dengan ini disampaikan agar permintaan KKHC dibawah untuk Biaya SDM dan Umum dapat dipenuhi sebagai berikut:"""
            else:
                record.kata_pengantar = """Sehubungan dengan permintaan KKHC (Kebutuhan Kas Harian Cabang), dengan ini disampaikan agar permintaan KKHC dibawah untuk Biaya Usaha dapat dipenuhi sebagai berikut:"""

    @api.depends('amount_total_jumlah_biaya')
    def _compute_rupiah_terbilang(self):
        for record in self:
            if record.amount_total_jumlah_biaya:
                total_int = int(record.amount_total_jumlah_biaya)
                terbilang = num2words(total_int, lang='id') + " rupiah"
                record.terbilang = terbilang.capitalize()
            else:
                record.terbilang = ""

    @api.depends('is_umum')
    def _compute_kepada_pengirim(self):
        for record in self:
            try:
                jika_umum = record.is_umum

                record.kepada_id = self.env.ref(
                    'agp_keuangan_dro.hr_jabatan_kadiv_keu' if jika_umum else 'agp_keuangan_dro.hr_jabatan_dir_ops'
                ).id

                record.pengirim_id = self.env.ref(
                    'agp_keuangan_dro.hr_jabatan_kadiv_umum' if jika_umum else 'agp_keuangan_dro.hr_jabatan_kadiv_usaha'
                ).id

            except ValueError:
                _logger.warning("Ref jabatan tidak ditemukan, cek apakah XML record tersedia di modul yang benar.")


    @api.depends('is_not_activity_user')
    def _compute_button_class(self):
        for record in self:
            record.button_class = "grey-button" if record.is_not_activity_user else ""

    @api.depends('activity_user_id')
    def _compute_is_not_activity_user(self):
        for record in self:
            if record.activity_user_id is not self._uid:
                record.is_not_activity_user = True
            else:
                record.is_not_activity_user = False

    @api.depends('monitored_kkhc_ids.nominal_pengajuan', 'monitored_kkhc_ids.is_rejected')
    def _compute_total(self):
        for record in self:
            record.total = sum(line.nominal_pengajuan for line in record.monitored_kkhc_ids if not line.is_rejected)

    @api.depends('monitored_kkhc_ids.kode_anggaran_id', 'is_umum')
    def _compute_tipe_nodin(self):
        for record in self:
            invalid_lines = record.monitored_kkhc_ids.filtered(lambda line: not line.kode_anggaran_id)
            invalid_lines.nodin_id = False
            invalid_lines.nodin_bod_id = False

            if not record.monitored_kkhc_ids:
                record.tipe_nodin = 'not_set'
                continue

            kode_anggaran_list = [line.kode_anggaran_id.kode_anggaran for line in record.monitored_kkhc_ids]

            if not kode_anggaran_list:
                record.tipe_nodin = 'not_set'
                continue

            all_start_with_5 = all(kode.startswith('5') for kode in kode_anggaran_list)
            all_start_with_6 = all(kode.startswith('6') for kode in kode_anggaran_list)

            if all_start_with_5:
                record.tipe_nodin = 'business'
            elif all_start_with_6:
                record.tipe_nodin = 'common'
                record.is_umum = True
            else:
                record.tipe_nodin = 'not_set'

    def unlink(self):
        for record in self:
            record.nota_dinas_line_ids.unlink()
            record.monitored_kkhc_ids.unlink()
            record.history_approval_ids.unlink()
            record.document_ids.unlink()
        return super(NotaDinasInheritDro, self).unlink()
    
    def read(self, fields=None, load='_classic_read'):
        records = super(NotaDinasInheritDro, self).read(fields, load)

        if fields:
            for record_dict in records:
                record = self.browse(record_dict['id'])
                record._compute_tipe_nodin()
                record._compute_kata_pengantar()
                record._compute_kepada_pengirim()
                record._compute_total()
                record._compute_amount_total_jumlah_biaya()
                record._compute_amount_total_jumlah_biaya_reject()
                record._compute_rupiah_terbilang()

        if not fields or 'amount_total_jumlah_biaya' in fields or 'monitored_kkhc_ids' in fields:
            for record_dict in records:
                record = self.browse(record_dict['id'])
                record._compute_amount_total_jumlah_biaya()

        if not fields or 'state' in fields:
            for record_dict in records:
                record = self.browse(record_dict['id'])
                if not record.activity_user_id:
                    record.assign_todo_first()

        return records

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

    @api.onchange('kkhc_ids')
    def _onchange_kkhc_ids(self):
        if not self.kkhc_ids:
            return

        new_lines = []
        for kkhc in self.kkhc_ids:
            for kkhc_line in kkhc.kkhc_line_ids:
                kode_anggaran = kkhc_line.kode_anggaran_id.kode_anggaran if kkhc_line.kode_anggaran_id else ""
                
                if kode_anggaran.startswith("5") or kode_anggaran.startswith("6"):
                    new_line = {
                        'nota_dinas_id': self.id,
                        'kkhc_id': kkhc.id,
                        'kode_anggaran_id': kkhc_line.kode_anggaran_id.id,
                        'account_code_id': kkhc_line.account_code_id.id,
                        'uraian': kkhc_line.deskripsi_penggunaan,
                        'jumlah_biaya': kkhc_line.nominal_disetujui,
                    }
                    new_lines.append((0, 0, new_line))

        self.nota_dinas_line_ids = new_lines

    @api.model_create_multi
    def create(self, vals):
        if self.env.user.level in ['usaha', 'umum']:
            pass
        elif self.env.user.id == 2:
            pass
        else:
            raise ValidationError('Anda tidak berwewenang untuk membuat Nota Dinas! Silakan hubungi Administrator.')

        nodin = super(NotaDinasInheritDro, self).create(vals)
        if nodin:
            nodin.assign_todo_first()

        return nodin
    
    def write(self, vals):
        if vals.get('document_ids'):
            print('selfname', self.name)
            
            # Get the sequence number from self.name (first 5 chars)
            # current_seq = self.name[:5]
            current_seq = re.sub(r'\D', '', self.name[:5])  # Remove non-digit characters
            
            # Calculate next sequence by incrementing by 1
            # next_seq = str(int(current_seq) + 1).zfill(5)
            next_seq = str(int(current_seq) + 1).zfill(5)

            # Get the rest of the format from self.name
            format_suffix = self.name[5:]
            
            # Construct the next record number
            next_record_number = next_seq + format_suffix
            
            # Search for the BoD record with that number
            nodin_bod_id = self.env['account.keuangan.nota.dinas.bod'].search([
                ('name', '=', next_record_number)
            ], limit=1)
            
            if nodin_bod_id:
                for doc in vals.get('document_ids'):
                    # doc[2] contains the values dict for (0,0,{}) or (1,id,{}) operations
                    if doc[0] in (0,1) and doc[2]:
                        # For new or updated records
                        doc_line_id = self.env['nodin.document.line'].browse(doc[1]) if doc[0] == 1 else False
                        if doc_line_id:
                            # Update existing record
                            doc_line_id.write({
                                'nodin_bod_id': nodin_bod_id.id
                            })
                        else:
                            # For new records, add nodin_bod_id to values
                            doc[2]['nodin_bod_id'] = nodin_bod_id.id
            # else:
            #     raise ValidationError('Nomor Nota Dinas Tahap Dua dengan disposisi menuju Dir. Keu atas Nota Dinas ini tidak ditemukan! Silakan mengkonfirmasi kembali ke bagian Usaha/Umum!')

        return super(NotaDinasInheritDro, self).write(vals)

    def action_submit(self):
        if not self.monitored_kkhc_ids:
            raise ValidationError('List Nota Dinas tidak boleh kosong. Mohon isi terlebih dahulu!')
        
        for record in self:
            if any(line.state == 'waiting' for line in record.document_ids):
                raise ValidationError('Dokumen Nota Dinas yang diperlukan belum di-upload, silakan cek terlebih dahulu!')
      
        for record in self:
            if any(line.state == 'rejected' for line in record.document_ids):
                raise ValidationError('Dokumen Nota Dinas belum dirubah setelah di-reject, silakan cek terlebih dahulu!')        

        cek = False
        nodin_model_id = self.env['ir.model'].search([('model', '=', 'account.keuangan.nota.dinas')], limit=1)
        if self.tipe_nodin == 'business':
            approval_id = self.env['approval.workflow'].sudo().search([
                ('name', '=', 'Nota Dinas Usaha'),
                ('res_model', '=', nodin_model_id.id)
            ], limit=1)
        elif self.tipe_nodin == 'common':
            approval_id = self.env['approval.workflow'].sudo().search([
                ('name', '=', 'Nota Dinas Umum'),
                ('res_model', '=', nodin_model_id.id)
            ], limit=1)

        if not approval_id:
            raise ValidationError('Approval setting untuk Nota Dinas tidak ditemukan. Silakan hubungi Administrator.')
        
        approval_line_id = self.env['approval.workflow.line'].search([
            ('sequence', '=', 1),
            ('workflow_id', '=', approval_id.id),
            ('level', '=', self.env.user.level)
        ], limit=1)
        print('tipe_nodin',self.tipe_nodin)
        print('approval_id',approval_id.name)
        print('approval_line_id',approval_line_id)
        print('approval_line_id.user_id.name', approval_line_id.user_id.name)

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
                    'note': f'Data Nota Dinas telah di-submit oleh {self.env.user.name} sebagai Maker.',
                    'nodin_id': self.id
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
                            'res_model_id': self.env['ir.model'].sudo().search([('model', '=', 'account.keuangan.nota.dinas')], limit=1).id,
                            'res_id': self.id,
                            'user_id': first_user,
                            'date_deadline': fields.Date.today() + timedelta(days=2),
                            'state': 'planned',
                            'status': 'to_approve',
                            'summary': """Harap segera meng-approve data Nota Dinas."""
                        })

        else:
            raise ValidationError('Hak akses user Anda tidak berhak untuk submit.')

    def action_approve(self):
        cek = False
        nodin_model_id = self.env['ir.model'].search([('model', '=', 'account.keuangan.nota.dinas')], limit=1)
        if self.tipe_nodin == 'business':
            approval_id = self.env['approval.workflow'].sudo().search([
                ('name', '=', 'Nota Dinas Usaha'),
                ('res_model', '=', nodin_model_id.id)
            ], limit=1)
        elif self.tipe_nodin == 'common':
            approval_id = self.env['approval.workflow'].sudo().search([
                ('name', '=', 'Nota Dinas Umum'),
                ('res_model', '=', nodin_model_id.id)
            ], limit=1)

        if not approval_id:
            raise ValidationError('Approval setting untuk menu Nota Dinas tidak ditemukan. Silakan hubungi Administrator.')

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
                self.state = 'approved'

                # final realisasi
                # commented out to test realisasi by dirkeu
                # if self.monitored_kkhc_ids:
                #     for line_monitor in self.monitored_kkhc_ids:
                #         if line_monitor.kode_anggaran_id.jenis_kegiatan_id is not False:
                #             coa_id = line_monitor.kode_anggaran_id.account_code_id
                #             rkap_line_id = self.env['account.keuangan.rkap.line'].sudo().search([
                #                 ('kode_anggaran_id', '=', line_monitor.kode_anggaran_id.id),
                #                 ('account_code_id', '=', coa_id.id),
                #                 ('branch_id', '=', line_monitor.branch_id.id),
                #             ], limit=1)
                #             kkhc_line_id = self.env['account.keuangan.kkhc.line'].sudo().search([
                #                 ('kode_anggaran_id', '=', line_monitor.kode_anggaran_id.id),
                #                 ('account_code_id', '=', coa_id.id),
                #                 ('branch_id', '=', line_monitor.branch_id.id),
                #             ], limit=1)
                #             if rkap_line_id and kkhc_line_id:
                #                 amount_paid_nodin = line_monitor.nominal_pengajuan
                #                 current_pemakaian = rkap_line_id.pemakaian_anggaran
                #                 current_nominal_disetujui = kkhc_line_id.nominal_disetujui
                #                 current_nominal = rkap_line_id.nominal
                #                 current_nominal_pengajuan = kkhc_line_id.nominal_pengajuan

                #                 # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
                #                 # FINAL REALISASI RKAP
                #                 # FIRST WRITE
                #                 rkap_line_id.write({'pemakaian_anggaran': current_pemakaian + amount_paid_nodin})
                #                 self.env.flush_all()

                #                 # 🚀 Reload the updated record
                #                 updated_rkap_line = self.env['account.keuangan.rkap.line'].browse(rkap_line_id.id)
                #                 current_pemakaian = updated_rkap_line.pemakaian_anggaran  # Now it holds the updated value

                #                 # SECOND WRITE
                #                 rkap_line_id.write({'realisasi': current_nominal - current_pemakaian})

                #                 # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
                #                 # FINAL REALISASI KKHC
                #                 # FIRST WRITE
                #                 kkhc_line_id.write({'nominal_disetujui': current_nominal_disetujui + amount_paid_nodin})
                #                 self.env.flush_all()

                #                 # 🚀 Reload the updated record
                #                 updated_kkhc_line = self.env['account.keuangan.kkhc.line'].browse(kkhc_line_id.id)
                #                 current_nominal_disetujui = updated_kkhc_line.nominal_disetujui  # Now it holds the updated value

                #                 # SECOND WRITE
                #                 kkhc_line_id.write({'sisa_pengajuan': current_nominal_pengajuan - current_nominal_disetujui})
                #                 # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

                #                 # CASH OUT
                #                 for line in self.monitored_kkhc_ids:
                #                     if line.kode_anggaran_id.kode_anggaran.startswith('5'):
                #                         # Create Cash Out
                #                         transaction_id = self.env['account.keuangan.transaction'].sudo().create({
                #                             'nodin_line_id': line.id,
                #                             'transaction_branch_id': line.branch_id.id,
                #                             'account_code_id': line.account_code_id.id,
                #                             'amount_paid': line.nominal_pengajuan
                #                         })
                #                         if transaction_id:
                #                             pass
                #                         else:
                #                             raise ValidationError(
                #                                 'Terjadi kesalahan saat membuat Cash-out atas Nota Dinas terkait. Mohon untuk mengecek kembali item Nota Dinas.')
                                
                #                     if line.kode_anggaran_id.kode_anggaran.startswith('6'):
                #                         # Create Cash Out
                #                         transaction_id = self.env['account.keuangan.transaction'].sudo().create({
                #                             'nodin_line_id': line.id,
                #                             'transaction_branch_id': line.branch_id.id,
                #                             'account_code_id': line.account_code_id.id,
                #                             'amount_paid': line.nominal_pengajuan
                #                         })
                #                         if transaction_id:
                #                             pass
                #                         else:
                #                             raise ValidationError(
                #                                 'Terjadi kesalahan saat membuat Cash-out atas Nota Dinas terkait. Mohon untuk mengecek kembali item Nota Dinas.')
                                
                #             else:
                #                 raise ValidationError(
                #                     'Item RKAP dan Item KKHC Cabang atas Nota Dinas ini tidak ditemukan! Approval Nota Dinas ini tidak dapat dilanjutkan. Silakan cek kembali!'
                #                 )

                level = self.env.user.level
                level_val = dict(self.env['res.users']._fields['level'].selection).get(level, level)
                level_bod = self.env.user.bod_level
                level_val_bod = dict(self.env['res.users']._fields['bod_level'].selection).get(level_bod, level_bod)
                if level == 'bod':
                    self.env['nodin.approval.line'].create({
                        'user_id': self._uid,
                        'date': datetime.now(),
                        'note': f'Diverifikasi dan di-approve oleh {self.env.user.name} sebagai {level_val} {level_val_bod}.',
                        'nodin_id': self.id
                    })
                else:
                    self.env['nodin.approval.line'].create({
                        'user_id': self._uid,
                        'date': datetime.now(),
                        'note': f'Diverifikasi dan di-approve oleh {self.env.user.name} sebagai {level_val}.',
                        'nodin_id': self.id
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
                            'res_model_id': self.env['ir.model'].sudo().search([('model', '=', 'account.keuangan.nota.dinas')], limit=1).id, 
                            'res_id': self.id, 
                            'user_id': first_user,  
                            'date_deadline': fields.Date.today() + timedelta(days=2), 
                            'state': 'planned', 
                            'status': 'to_approve', 
                            'summary': """Harap segera meng-approve data Nota Dinas.""" 
                        }) 
                        level = self.env.user.level
                        level_val = dict(self.env['res.users']._fields['level'].selection).get(level, level)
                        self.env['nodin.approval.line'].create({ 
                            'user_id': self._uid, 
                            'date': datetime.now(),
                            'note': f'Di-approve oleh {self.env.user.name} sebagai {level_val}', 
                            'nodin_id': self.id 
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
    
    def action_reject(self):
        if self.activity_user_id.id == self._uid:
            action = {
                'name': ('Alasan Reject Nota Dinas'),
                'type': "ir.actions.act_window",
                'res_model': 'nodin.reject.wizard',
                'view_type': 'form',
                'target': 'new',
                'view_mode': 'form',
                'context': {'active_id': self.id},
                'view_id': self.env.ref('agp_keuangan_dro.nodin_reject_wizard_form').id,
            }
            return action
        else:
            raise ValidationError('Hak akses user Anda tidak berhak untuk reject!')

    
    def set_to_draft(self):
        if self.state != 'draft':
            self.state = 'draft'

    def assign_todo_first(self):
        model_model = self.env['ir.model'].sudo()
        document_setting_model = self.env['approval.workflow.document.setting'].sudo()
        nodin_model_id = model_model.search([('model', '=', 'account.keuangan.nota.dinas')], limit=1)
        for res in self:
            res.approval_step = 1
            first_user = False
            approval_id = self.env['approval.workflow'].sudo().search([('res_model', '=', nodin_model_id.id)], limit=1)
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
                    'res_model_id': nodin_model_id.id,
                    'res_id': res.id,
                    'user_id': first_user,
                    'date_deadline': fields.Date.today() + timedelta(days=2),
                    'state': 'planned',
                    'summary': "Harap segera men-submit data Nota Dinas."
                })

            document_list = []
            doc_setting_id = document_setting_model.search([('model_id', '=', nodin_model_id.id)])

            if doc_setting_id:
                for document_line in doc_setting_id:
                    document_list.append((0, 0, {
                        'nodin_id': res.id,
                        'document_id': document_line.id,
                        'state': 'waiting'
                    }))
                res.document_ids = document_list
            else:
                raise ValidationError("Settingan untuk approval dan/atau dokumen belum dikonfigurasi. Silakan hubungi Administrator.")

class KKHCApprovalLine(models.Model):
    _name = 'nodin.approval.line'
    _description = 'List Riwayat Approval Nota Dinas'

    nodin_id = fields.Many2one('account.keuangan.nota.dinas', string='No. Nota Dinas')
    nodin_bod_id = fields.Many2one('account.keuangan.nota.dinas.bod', string='No. Nota Dinas BoD')
    user_id = fields.Many2one('res.users', string='User')
    date = fields.Datetime(string='Date')
    note = fields.Char(string='Note')

class KKHCApprovalLine(models.Model):
    _name = 'nodin.document.line'
    _description = 'List Dokumen Terkait Nota Dinas'

    nodin_id = fields.Many2one('account.keuangan.nota.dinas', string='No. Nota Dinas')
    nodin_bod_id = fields.Many2one('account.keuangan.nota.dinas.bod', string='No. Nota Dinas BoD')
    document_id = fields.Many2one('approval.workflow.document.setting', string='Dokumen')
    document = fields.Binary(string='Upload File')
    filename = fields.Char(string='Filename')
    state = fields.Selection([
        ('waiting', 'Waiting'),
        ('uploaded', 'Uploaded'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected')
    ], string='Status')

    @api.onchange('document')
    def onchange_document_upload(self):
        if self.document:
            if self.filename and not self.filename.lower().endswith('.pdf'):
                self.document = False
                self.filename = False
                self.state = 'waiting'
                raise ValidationError('Tidak dapat mengunggah file selain ekstensi PDF.')
            elif self.filename.lower().endswith('.pdf'):
                self.state = 'uploaded'

        else:
            self.document = False
            self.filename = False
            self.state = 'waiting'

class NotaDinasLineInheritDro(models.Model):
    _inherit = 'account.keuangan.nota.dinas.line'

    kkhc_id = fields.Many2one('account.keuangan.kkhc', string='No. KKHC')
    branch_id = fields.Many2one('res.branch', string='Cabang', related='kkhc_id.branch_id')
    jumlah_biaya = fields.Float(string='Jumlah Biaya')
    biaya_disetujui = fields.Float(string='Biaya Disetujui')
    sisa_belum_dibayar = fields.Float(string='Sisa Belum Dibayar')
    tanggal_dibayar = fields.Date(string='Tanggal Dibayar')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('done', 'Done'),
        ('reject', 'Reject'),
    ], string='Status')

    @api.onchange('biaya_disetujui', 'jumlah_biaya')
    def _onchange_biaya_disetujui(self):
        for record in self:
            if record.jumlah_biaya and record.biaya_disetujui:
                record.sisa_belum_dibayar = record.jumlah_biaya - record.biaya_disetujui
            else:
                record.sisa_belum_dibayar = record.jumlah_biaya