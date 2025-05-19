from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

class KKHCInheritDro(models.Model):
    _inherit = 'account.keuangan.kkhc'

    periode_kkhc_start = fields.Date(string='Dari', default=fields.Date.today())
    periode_kkhc_end = fields.Date(string='Sampai', compute='_compute_periode_kkhc_end')
    history_approval_ids = fields.One2many('kkhc.approval.line', 'kkhc_id', string='List Riwayat Approval')
    document_ids = fields.One2many('kkhc.document.line', 'kkhc_id', string='List Dokumen Terkait')
    approval_step = fields.Integer(string='Approval Step')
    is_convertible_to_nodin = fields.Boolean(string='Bisa Dibuat Nodin', compute='_compute_is_convertible_to_nodin', store=True)
    kkhc_type = fields.Selection([
        ('usaha', 'Usaha'),
        ('umum', 'Umum')
    ], string='Tipe KKHC', compute='_compute_kkhc_type', store=True)
    rkap_id = fields.Many2one('account.keuangan.rkap', string='No. RKAP', readonly=True)
    # rejected_monitored_kkhc_line_ids = fields.One2many('account.keuangan.monitor.kkhc.line', 'kkhc_kkhc_id', string='List Undropping KKHC', domain=[('is_rejected', '=', True)])

    def _cron_create_monitoring_lines(self):
        for record in self:
            existing_kkhc_line_ids = self.env['account.keuangan.monitor.kkhc.line'].search([('kkhc_id', '=', record.id)]).mapped('kkhc_line_id.id')
            new_kkhc_lines = self.env['account.keuangan.kkhc.line'].search([('kkhc_id', '=', record.id)])
            
            for line in new_kkhc_lines:
                if line.id not in existing_kkhc_line_ids:
                    if line.is_approved_by_divs == True:
                        self.env['account.keuangan.monitor.kkhc.line'].create({
                            'kkhc_line_id': line.id,
                            'kkhc_id': record.id,
                            'branch_id': line.kkhc_id.branch_id.id,
                            'kode_anggaran_id': line.kode_anggaran_id.id,
                            'deskripsi': line.deskripsi,
                            'account_code_id': line.account_code_id.id,
                            'nominal_pengajuan': line.nominal_pengajuan,
                            'nominal_disetujui': line.nominal_disetujui,
                            'pagu_limit': line.pagu_limit,
                            'sisa_pengajuan': line.sisa_pengajuan,
                            'active': True,
                        })

    def create_monitoring_lines(self):
        for record in self:
            existing_monitors = self.env['account.keuangan.monitor.kkhc.line'].search([
                ('kkhc_id', '=', record.id)
            ])
            new_kkhc_lines = self.env['account.keuangan.kkhc.line'].search([('kkhc_id', '=', record.id)])
            
            for line in new_kkhc_lines:
                exists = existing_monitors.filtered(lambda m: m.kkhc_line_id.id == line.id and m.kode_anggaran_id.id == line.kode_anggaran_id.id and m.account_code_id.id == line.account_code_id.id)
                if not exists:
                    self.env['account.keuangan.monitor.kkhc.line'].create({
                        'kkhc_line_id': line.id,
                        'kkhc_id': record.id,
                        'branch_id': line.kkhc_id.branch_id.id,
                        'kode_anggaran_id': line.kode_anggaran_id.id,
                        'deskripsi': line.deskripsi,
                        'account_code_id': line.account_code_id.id,
                        'nominal_pengajuan': line.nominal_pengajuan,
                        'nominal_disetujui': line.nominal_disetujui,
                        'pagu_limit': line.pagu_limit,
                        'sisa_pengajuan': line.sisa_pengajuan,
                        'active': True,
                    })

                # if line.id not in existing_kkhc_line_ids:
                    # Rev 17/04 - Jangan Saling Tunggu antar Divs!
                    # if line.is_approved_by_divs == True:
                    # self.env['account.keuangan.monitor.kkhc.line'].create({
                    #     'kkhc_line_id': line.id,
                    #     'kkhc_id': record.id,
                    #     'branch_id': line.kkhc_id.branch_id.id,
                    #     'kode_anggaran_id': line.kode_anggaran_id.id,
                    #     'deskripsi': line.deskripsi,
                    #     'account_code_id': line.account_code_id.id,
                    #     'nominal_pengajuan': line.nominal_pengajuan,
                    #     'nominal_disetujui': line.nominal_disetujui,
                    #     'pagu_limit': line.pagu_limit,
                    #     'sisa_pengajuan': line.sisa_pengajuan,
                    #     'active': True,
                    # })
                    # else:
                        # raise ValidationError('Item KKHC belum di-approve oleh Kepala Divisi terkait!')
                    
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Berhasil',
                'message': 'Item KKHC terkait sudah masuk ke fase monitoring.',
                'type': 'success',
                'sticky': False,
            }
        }


    @api.depends('kkhc_line_ids.kode_anggaran_id')
    def _compute_kkhc_type(self):
        for record in self:
            usaha = any(line.kode_anggaran_id.kode_anggaran.startswith("5") for line in record.kkhc_line_ids)
            umum = any(line.kode_anggaran_id.kode_anggaran.startswith("6") for line in record.kkhc_line_ids)
            if usaha and umum:
                record.kkhc_type = 'umum'
            elif usaha:
                record.kkhc_type = 'usaha'
            elif umum:
                record.kkhc_type = 'umum'
            else:
                record.kkhc_type = None

    @api.depends('kkhc_line_ids.nominal_disetujui')
    def _compute_is_convertible_to_nodin(self):
        for record in self:
            if record.kkhc_line_ids and all(
                line.nominal_disetujui and line.nominal_disetujui != 0.0 for line in record.kkhc_line_ids
            ):
                record.is_convertible_to_nodin = True
            else:
                record.is_convertible_to_nodin = False

    @api.model_create_multi
    def create(self, vals):
        if self.env.user.level == 'maker':
            pass
        else:
            raise ValidationError('Anda tidak berwewenang untuk membuat KKHC! Silakan hubungi Administrator.')

        # if self.periode_kkhc_start == False:
        #     raise ValidationError('Mohon untuk mengisi tanggal awal periode dinas terlebih dahulu!')
        # else:
        #     pass
            
        kkhc = super(KKHCInheritDro, self).create(vals)
        if kkhc:
            rkap = self.env['account.keuangan.rkap'].search([('branch_id', '=', kkhc.branch_id.id)], limit=1)
            kkhc.rkap_id = rkap.id if rkap else False
            kkhc.assign_todo_first()

        return kkhc

    @api.depends('periode_kkhc_start')
    def _compute_periode_kkhc_end(self):
        for record in self:
            if record.periode_kkhc_start:
                record.periode_kkhc_end = (datetime.strptime(str(record.periode_kkhc_start), '%Y-%m-%d') + timedelta(days=7)).strftime('%Y-%m-%d')
            else:
                record.periode_kkhc_end = None

    def action_submit(self):
        if not self.kkhc_line_ids:
            raise ValidationError('List KKHC tidak boleh kosong. Mohon isi terlebih dahulu!')

        cek = False
        kkhc_model_id = self.env['ir.model'].search([('model', '=', 'account.keuangan.kkhc')], limit=1)
        approval_id = self.env['approval.workflow'].sudo().search([
            ('name', '=', 'KKHC'),
            ('res_model', '=', kkhc_model_id.id),
            ('branch_id', '=', self.branch_id.id)
        ], limit=1)

        if not approval_id:
            raise ValidationError('Approval setting untuk KKHC tidak ditemukan. Silakan hubungi Administrator.')

        approval_line_id = self.env['approval.workflow.line'].search([
            ('sequence', '=', 1),
            ('workflow_id', '=', approval_id.id),
            ('level', '=', self.env.user.level)
        ], limit=1)

        if approval_line_id.user_id.id == self._uid:
            cek = True
        else:
            raise ValidationError('Role berjenjang untuk Approval KKHC belum di-setting. Silakan hubungi Administrator.')

        if cek == True:
            first_user = False
            if self.activity_ids:
                for x in self.activity_ids.filtered(lambda x: x.status != 'approved'):
                    if x.user_id.id == self._uid:
                        x.status = 'approved'
                        x.action_done()
                self.state = 'on_review'
                self.approval_step += 1
                self.env['kkhc.approval.line'].sudo().create({
                    'user_id': self._uid,
                    'date': datetime.now(),
                    'note': f'Data KKHC telah di-submit oleh {self.env.user.name} sebagai Maker.',
                    'kkhc_id': self.id
                })

                approval_line = self.env['approval.workflow.line'].search([
                    ('workflow_id', '=', approval_id.id),
                    ('sequence', '=', self.approval_step),
                    ('level', '=', self.env.user.level)
                ], limit=1)
                user_id_next = approval_line.user_id
                if user_id_next:
                    first_user = user_id_next.id

                    if first_user:
                        self.env['mail.activity'].sudo().create({
                            'activity_type_id': 4,
                            'res_model_id': self.env['ir.model'].sudo().search([('model', '=', 'account.keuangan.kkhc')], limit=1).id,
                            'res_id': self.id,
                            'user_id': first_user,
                            'date_deadline': fields.Date.today() + timedelta(days=2),
                            'state': 'planned',
                            'status': 'to_approve',
                            'summary': """Harap segera meng-approve data KKHC."""
                        })

        else:
            raise ValidationError('Hak akses user Anda tidak berhak untuk submit.')

    def action_approve(self):
        cek = False
        kkhc_model_id = self.env['ir.model'].search([('model', '=', 'account.keuangan.kkhc')], limit=1)
        approval_id = self.env['approval.workflow'].sudo().search([
            ('name', '=', 'KKHC'),
            ('res_model', '=', kkhc_model_id.id),
            ('branch_id', '=', self.branch_id.id)
        ], limit=1)

        if not approval_id:
            raise ValidationError(f'Approval setting untuk KKHC Cabang {self.branch_id.name} tidak ditemukan. Silakan hubungi Administrator.')

        approval_line_id = self.env['approval.workflow.line'].search([
            ('sequence', '=', self.approval_step),
            ('workflow_id', '=', approval_id.id),
            ('level', '=', self.env.user.level)
        ], limit=1)

        user_id = approval_line_id.user_id
        if user_id:
            if self._uid == user_id.id:
                cek = True

        if cek:
            if approval_id.total_approve == self.approval_step:
                self.state = 'approved'
                self.env['kkhc.approval.line'].create({
                    'user_id': self._uid,
                    'date': datetime.now(),
                    'note': f'Diverifikasi dan di-approve oleh {self.env.user.name}.',
                    'kkhc_id': self.id
                })

                for doc in self.document_ids.filtered(lambda x: x.state in ('uploaded','rejected')):
                    doc.state = 'verified'

                if self.activity_ids:
                    for x in self.activity_ids.filtered(lambda x: x.status != 'approved'):
                        if x.user_id.id == self._uid:
                            x.status = 'approved'
                            x.sudo().action_done()
            else:
                if self.approval_step == 2:
                    pass
                else:
                    # FINAL TOUCH: Check that all line items have been approved by Divisi (i.e., is_approved_by_divs == True)  
                    if not all(line.is_approved_by_divs for line in self.kkhc_line_ids):
                        raise ValidationError(
                            'Salah satu item pada KKHC ini belum di-approve oleh Divisi Usaha dan/atau Divisi Umum, silakan cek kembali!'
                        )
                
                # Proceed with next approval step if all lines are approved by divisions
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
                            'res_model_id': self.env['ir.model'].sudo().search([('model', '=', 'account.keuangan.kkhc')], limit=1).id, 
                            'res_id': self.id, 
                            'user_id': first_user,  
                            'date_deadline': fields.Date.today() + timedelta(days=2), 
                            'state': 'planned', 
                            'status': 'to_approve', 
                            'summary': """Harap segera meng-approve data KKHC.""" 
                        }) 
                        level = self.env.user.level
                        level_val = dict(self.env['res.users']._fields['level'].selection).get(level, level)
                        level_bod = self.env.user.bod_level
                        level_val_bod = dict(self.env['res.users']._fields['bod_level'].selection).get(level_bod, level_bod)
                        if level == 'bod':
                            self.env['kkhc.approval.line'].create({ 
                                'user_id': self._uid, 
                                'date': datetime.now(),
                                'note': f'Di-approve oleh {self.env.user.name} sebagai {level_val} {level_val_bod}.', 
                                'kkhc_id': self.id 
                            })
                        else:
                            self.env['kkhc.approval.line'].create({ 
                                'user_id': self._uid, 
                                'date': datetime.now(),
                                'note': f'Di-approve oleh {self.env.user.name} sebagai {level_val}.', 
                                'kkhc_id': self.id 
                            })

                        if self.activity_ids:
                            for x in self.activity_ids.filtered(lambda x: x.status != 'approved'):
                                if x.user_id.id == self._uid:
                                    x.status = 'approved'
                                    x.sudo().action_done()
                    else:
                        raise ValidationError('User role untuk approval KKHC selanjutnya belum di-setting, silakan hubungi Administrator.')

        else:
            raise ValidationError('Hak akses user anda tidak berhak untuk approve.')
    
    def action_reject(self):
        cek = False
        if self.branch_id:
            if self.activity_user_id.id == self._uid:
                cek = True

        if cek == True:
            action = {
                'name': ('Alasan Reject KKHC'),
                'type': "ir.actions.act_window",
                'res_model': 'kkhc.reject.wizard',
                'view_type': 'form',
                'target': 'new',
                'view_mode': 'form',
                'context': {'active_id': self.id},
                'view_id': self.env.ref('agp_keuangan_dro.kkhc_reject_wizard_form').id,
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
        kkhc_model_id = model_model.search([('model', '=', 'account.keuangan.kkhc')], limit=1)
        for res in self:
            res.approval_step = 1
            first_user = False
            approval_id = self.env['approval.workflow'].sudo().search([
                ('name', '=', 'KKHC'),
                ('res_model', '=', kkhc_model_id.id),
                ('branch_id', '=', self.branch_id.id)
            ], limit=1)
            approval_line_id = self.env['approval.workflow.line'].search([
                ('sequence', '=', 1),
                ('workflow_id', '=', approval_id.id),
                ('level', '=', self.env.user.level)
                # ('branch_id', '=', self.branch_id.id)
            ], limit=1)
                                
            if approval_line_id:
                first_user = approval_line_id.user_id.id

            if first_user:
                self.env['mail.activity'].sudo().create({
                    'activity_type_id': 4,
                    'res_model_id': kkhc_model_id.id,
                    'res_id': res.id,
                    'user_id': first_user,
                    'date_deadline': fields.Date.today() + timedelta(days=2),
                    'state': 'planned',
                    'summary': "Harap segera men-submit data KKHC."
                })

            document_list = []
            doc_setting_id = document_setting_model.search([('model_id', '=', kkhc_model_id.id)])

            if doc_setting_id:
                for document_line in doc_setting_id:
                    document_list.append((0, 0, {
                        'kkhc_id': res.id,
                        'document_id': document_line.id,
                        'state': 'waiting'
                    }))
                res.document_ids = document_list
            else:
                # Create a default document line even if no settings exist
                document_list.append((0, 0, {
                    'kkhc_id': res.id,
                    'state': 'waiting'
                }))
                res.document_ids = document_list

class KKHCApprovalLine(models.Model):
    _name = 'kkhc.approval.line'
    _description = 'List Riwayat Approval KKHC'

    kkhc_id = fields.Many2one('account.keuangan.kkhc', string='No. KKHC')
    user_id = fields.Many2one('res.users', string='User')
    date = fields.Datetime(string='Date')
    note = fields.Char(string='Note')

class KKHCApprovalLine(models.Model):
    _name = 'kkhc.document.line'
    _description = 'List Dokumen Terkait KKHC'

    kkhc_id = fields.Many2one('account.keuangan.kkhc', string='No. KKHC')
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

class KKHCLinesInheritDro(models.Model):
    _inherit = 'account.keuangan.kkhc.line'

    branch_id = fields.Many2one('res.branch', string='Cabang', related='kkhc_id.branch_id', store=True)
    header_state = fields.Selection([], string="Header Status", related="kkhc_id.state", store=True)
    item_type = fields.Selection([
        ('item_usaha', 'Usaha'),
        ('item_umum', 'Umum')
    ], compute='_compute_item_type_kkhc', store=True, string='Tipe Item')
    is_approved_by_divs = fields.Boolean(string='Approved by Kadiv', default=False)
    nominal_disetujui_divisi = fields.Float(string='Disetujui Usaha/Umum', compute='_compute_nominal_disetujui_divisi_default', readonly=False, store=True)

    @api.constrains('nominal_disetujui_divisi')
    def _check_nominal_disetujui_divisi(self):
        for record in self:
            if record.nominal_disetujui_divisi > record.nominal_pengajuan:
                raise ValidationError('Nominal yang disetujui tidak boleh lebih besar dari nominal pengajuan.')

    @api.depends('nominal_pengajuan')
    def _compute_nominal_disetujui_divisi_default(self):
        for rec in self:
            if not rec.nominal_disetujui_divisi or rec.nominal_disetujui_divisi == 0.0:
                rec.nominal_disetujui_divisi = rec.nominal_pengajuan

    def _action_approve_as_kadiv(self):
        return {
            'name': ('Apakah anda yakin akan meng-approve item-item KKHC berikut ini?'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.keuangan.kkhc.line.wizard',
            'view_type': 'form',
            'target': 'new',
            'view_mode': 'form',
            'context': {'default_kkhc_line_ids': self.ids},
            'view_id': self.env.ref('agp_keuangan_dro.view_kkhc_line_kadiv_form').id,
        }

    @api.depends('kode_anggaran_id.kode_anggaran')
    def _compute_item_type_kkhc(self):
        for line in self:
            if line.kode_anggaran_id and line.kode_anggaran_id.kode_anggaran:
                if line.kode_anggaran_id.kode_anggaran.startswith(('4', '5')):
                    line.item_type = 'item_usaha'
                elif line.kode_anggaran_id.kode_anggaran.startswith('6'):
                    line.item_type = 'item_umum'
                else:
                    line.item_type = False
            else:
                line.item_type = False

    def read(self, fields=None, load='_classic_read'):
        records = super(KKHCLinesInheritDro, self).read(fields, load)

        if fields:
            for record_dict in records:
                record = self.browse(record_dict['id'])
                record._compute_nominal_disetujui_divisi_default()

        return records


    def action_approve_item(self):
        if self.nominal_disetujui_divisi != 0.0:
            if self.env.user.level not in ['usaha', 'umum']:
                raise ValidationError('Hak akses user Anda tidak berhak untuk approve Item KKHC.')
            else:
                for line in self:
                    if line.header_state == 'approved':
                        if not line.is_approved_by_divs:
                            line.is_approved_by_divs = True
                            self.env['kkhc.approval.line'].sudo().create({
                                'user_id': self._uid,
                                'date': datetime.now(),
                                'note': f'Data KKHC telah di-approve oleh {self.env.user.name} sebagai {self.env.user.level}.',
                                'kkhc_id': self.kkhc_id.id
                            })
                            return {
                                'type': 'ir.actions.client',
                                'tag': 'display_notification',
                                'params': {
                                    'title': 'Berhasil',
                                    'message': f'Item KKHC {line.kkhc_id.name} kode {line.kode_anggaran_id.kode_anggaran} dengan deskripsi {line.deskripsi} sudah di-approve oleh {self.env.user.name} sebagai {self.env.user.level.capitalize()}. Halaman akan segera di-refresh...',
                                    'type': 'success',
                                    'sticky': False,
                                    'tag': 'reload',
                                }
                            }
                        else:
                            return {
                                'type': 'ir.actions.client',
                                'tag': 'display_notification',
                                'params': {
                                    'title': 'Me-refresh Halaman...',
                                    'message': 'Item ini sudah di-approve oleh divisi terkait. Harap tunggu, browser sedang memperbarui data.',
                                    'type': 'warning',
                                    'sticky': False,
                                }
                            }
                    else:
                        raise ValidationError('Item KKHC ini sudah di-approve oleh divisi terkait!')
                    
        else:
            raise ValidationError('Anda belum mengisi nominal yang disetujui oleh divisi. Silakan isi terlebih dahulu.')
