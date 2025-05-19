from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import qrcode
import io
import base64
import pytz

class RKAPInheritDro(models.Model):
    _inherit = 'account.keuangan.rkap'

    history_approval_ids = fields.One2many('rkap.approval.line', 'rkap_id', string='List Riwayat Approval')
    approval_step = fields.Integer(string='Approval Step')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('on_review', 'On Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft')
    is_approved = fields.Boolean(string='Approved')
    qr_code = fields.Binary('QR Code', compute='_compute_qr_code')
    img_src = fields.Char(string='Img Source',
                          default=lambda self: self.env['ir.config_parameter'].sudo().get_param('web.base.url') + '/agp_report_extended/static/src/img/agp_logo.png')
    kkhc_ids = fields.One2many('account.keuangan.kkhc', 'rkap_id', string='List KKHC atas RKAP')

    def action_print_konsolidasi(self):
        if self.sisa_pengeluaran != 0.0:
            report = self.env.ref('agp_report_extended.action_report_rkap_konsolidasi').report_action(self)
            return report
        else:
            raise ValidationError(f'Sisa RKAP untuk Cabang {self.branch_id} tidak mencukupi.')

    def get_data_konsolidasi(self):
        self.ensure_one()
        # Retrieve branch information
        self._cr.execute("""
            SELECT id, UPPER(name) AS name FROM res_branch ORDER BY name
        """)
        branches = self._cr.fetchall()

        # Construct dynamic sub-query for saldo
        sub_query = ", ".join(
            f"SUM(CASE WHEN acc_saldo.branch_id = {b[0]} THEN acc_saldo.saldo ELSE 0 END) AS \"{b[1].replace(' ', '_')}\""
            for b in branches
        )

        # Fetch consolidated saldo data
        query = f"""
            SELECT anggaran.kode_anggaran, acc.code, anggaran.deskripsi, {sub_query}
            FROM account_keuangan_saldo AS acc_saldo
            INNER JOIN account_keuangan_kode_anggaran AS anggaran ON acc_saldo.kode_anggaran_id = anggaran.id
            INNER JOIN account_account AS acc ON anggaran.account_code_id = acc.id
            GROUP BY anggaran.kode_anggaran, acc.code, anggaran.deskripsi
            ORDER BY anggaran.kode_anggaran;
        """
        self._cr.execute(query)
        query_results = self._cr.fetchall()

        branch_list = ['kode', 'coa', 'uraian']
        branch_list.extend(b[1].lower().replace(' ', '_') for b in branches)

        lines = []
        for res in query_results:
            line = {branch_list[i]: res[i] for i in range(len(branch_list))}
            lines.append(line)

        return {
            'headers': branch_list,
            'lines': lines,
        }

    @api.depends('name', 'history_approval_ids')
    def _compute_qr_code(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        
        for record in self:
            if record.name:
                record_url = (
                    f"{base_url}/rkap/approvals/{record.id}"
                )
                
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(record_url)

                qr.make(fit=True)
                qr_image = qr.make_image(fill_color="black", back_color="white")

                # Convert the image to RGB and save it to a buffer
                qr_image = qr_image.convert('RGB')
                buffer = io.BytesIO()
                qr_image.save(buffer, format="PNG")
                qr_image_data = buffer.getvalue()

                # Encode the image to base64 and save it in the field
                record.qr_code = base64.b64encode(qr_image_data)
            else:
                record.qr_code = False

    @api.model_create_multi
    def create(self, vals):
        if self.env.user.level == 'maker':
            pass
        else:
            raise ValidationError('Anda tidak berwewenang untuk membuat RKAP! Silakan hubungi Administrator.')

        rkap = super(RKAPInheritDro, self).create(vals)
        if rkap:
            rkap.assign_todo_first()

        return rkap

    def action_submit(self):
        if not self.rkap_line_ids:
            raise ValidationError('List RKAP tidak boleh kosong. Mohon isi terlebih dahulu!')

        cek = False
        rkap_model_id = self.env['ir.model'].search([('model', '=', 'account.keuangan.rkap')], limit=1)
        approval_id = self.env['approval.workflow'].sudo().search([
            ('name', '=', 'RKAP'),
            ('res_model', '=', rkap_model_id.id),
            ('branch_id', '=', self.branch_id.id),
        ], limit=1)

        if not approval_id:
            raise ValidationError('Approval setting untuk RKAP tidak ditemukan. Silakan hubungi Administrator.')

        approval_line_id = self.env['approval.workflow.line'].search([
            ('sequence', '=', 1),
            ('workflow_id', '=', approval_id.id),
            ('level', '=', self.env.user.level)
        ], limit=1)

        if approval_line_id.user_id.id == self._uid:
            cek = True
        else:
            raise ValidationError('Role berjenjang untuk Approval RKAP belum di-setting. Silakan hubungi Administrator.')

        if cek == True:
            first_user = False
            if self.activity_ids:
                for x in self.activity_ids.filtered(lambda x: x.status != 'approved'):
                    if x.user_id.id == self._uid:
                        x.status = 'approved'
                        x.action_done()
                self.state = 'on_review'
                self.approval_step += 1
                self.env['rkap.approval.line'].sudo().create({
                    'user_id': self._uid,
                    'date': datetime.now(),
                    'note': f'Data RKAP telah di-submit oleh {self.env.user.name} sebagai Maker.',
                    'rkap_id': self.id
                })

                approval_line = self.env['approval.workflow.line'].search([
                    ('workflow_id', '=', approval_id.id),
                    ('sequence', '=', self.approval_step),
                    # ('level', '=', self.env.user.level)
                ], limit=1)
                user_id_next = approval_line.user_id
                if user_id_next:
                    first_user = user_id_next.id

                    if first_user:
                        self.env['mail.activity'].sudo().create({
                            'activity_type_id': 4,
                            'res_model_id': self.env['ir.model'].sudo().search([('model', '=', 'account.keuangan.rkap')], limit=1).id,
                            'res_id': self.id,
                            'user_id': first_user,
                            'date_deadline': fields.Date.today() + timedelta(days=2),
                            'state': 'planned',
                            'status': 'to_approve',
                            'summary': """Harap segera meng-approve data RKAP."""
                        })

        else:
            raise ValidationError('Hak akses user Anda tidak berhak untuk submit.')

    def action_approve(self):
        cek = False
        rkap_model_id = self.env['ir.model'].search([('model', '=', 'account.keuangan.rkap')], limit=1)
        approval_id = self.env['approval.workflow'].sudo().search([
            ('name', '=', 'RKAP'),
            ('res_model', '=', rkap_model_id.id),
            ('branch_id', '=', self.branch_id.id)
        ], limit=1)

        if not approval_id:
            raise ValidationError(
                f'Approval setting untuk RKAP Cabang {self.branch_id.name} tidak ditemukan. Silakan hubungi Administrator.'
            )

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
                if not self.tanggal_disetujui:
                    raise ValidationError('Harap isi tanggal disetujui terlebih dahulu!')
                # Log approval with proper note
                level = self.env.user.level
                level_val = dict(self.env['res.users']._fields['level'].selection).get(level, level)
                level_bod = self.env.user.bod_level
                level_val_bod = dict(self.env['res.users']._fields['bod_level'].selection).get(level_bod, level_bod)
                if level == 'bod':
                    self.env['rkap.approval.line'].create({
                        'user_id': self._uid,
                        'date': datetime.now(),
                        'note': f'Diverifikasi dan di-approve oleh {self.env.user.name} sebagai {level_val} {level_val_bod}.',
                        'rkap_id': self.id
                    })
                else:
                    self.env['rkap.approval.line'].create({
                        'user_id': self._uid,
                        'date': datetime.now(),
                        'note': f'Diverifikasi dan di-approve oleh {self.env.user.name} sebagai {level_val}.',
                        'rkap_id': self.id
                    })

                if self.activity_ids:
                    for x in self.activity_ids.filtered(lambda x: x.status != 'approved'):
                        if x.user_id.id == self._uid:
                            x.status = 'approved'
                            x.sudo().action_done()
            else:
                if self.approval_step == 2:
                    pass
                else:
                    # Force all lines to be approved by divisions
                    for line in self.rkap_line_ids:
                        line.is_approved_by_divs = True
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
                            'res_model_id': self.env['ir.model'].sudo().search([('model', '=', 'account.keuangan.rkap')], limit=1).id,
                            'res_id': self.id,
                            'user_id': first_user,
                            'date_deadline': fields.Date.today() + timedelta(days=2),
                            'state': 'planned',
                            'status': 'to_approve',
                            'summary': "Harap segera meng-approve data RKAP."
                        })
                        level = self.env.user.level
                        level_val = dict(self.env['res.users']._fields['level'].selection).get(level, level)
                        level_bod = self.env.user.bod_level
                        level_val_bod = dict(self.env['res.users']._fields['bod_level'].selection).get(level_bod, level_bod)
                        if level == 'bod':
                            self.env['rkap.approval.line'].create({
                                'user_id': self._uid,
                                'date': datetime.now(),
                                'note': f'Di-approve oleh {self.env.user.name} sebagai {level_val} {level_val_bod}.',
                                'rkap_id': self.id
                            })
                        else:
                            self.env['rkap.approval.line'].create({
                                'user_id': self._uid,
                                'date': datetime.now(),
                                'note': f'Di-approve oleh {self.env.user.name} sebagai {level_val}.',
                                'rkap_id': self.id
                            })

                        if self.activity_ids:
                            for x in self.activity_ids.filtered(lambda x: x.status != 'approved'):
                                if x.user_id.id == self._uid:
                                    x.status = 'approved'
                                    x.sudo().action_done()
                    else:
                        raise ValidationError('User role untuk approval RKAP selanjutnya belum di-setting, silakan hubungi Administrator.')

        else:
            raise ValidationError('Hak akses user anda tidak berhak untuk approve.')
        
    def action_reject(self):
        # if self.branch_id:
        if self.activity_user_id.id == self._uid:
            action = {
                'name': ('Alasan Reject RKAP'),
                'type': "ir.actions.act_window",
                'res_model': 'rkap.reject.wizard',
                'view_type': 'form',
                'target': 'new',
                'view_mode': 'form',
                'context': {'active_id': self.id},
                'view_id': self.env.ref('agp_keuangan_dro.rkap_reject_wizard_form').id,
            }
            return action
        else:
            raise ValidationError('Hak akses user anda tidak berhak untuk reject RKAP.')

    def set_to_draft(self):
        if self.state != 'draft':
            self.state = 'draft'

    def assign_todo_first(self):
        model_model = self.env['ir.model'].sudo()
        rkap_model_id = model_model.search([('model', '=', 'account.keuangan.rkap')], limit=1)
        for res in self:
            res.approval_step = 1
            first_user = False
            approval_id = self.env['approval.workflow'].sudo().search([
                ('name', '=', 'RKAP'),
                ('res_model', '=', rkap_model_id.id),
                ('branch_id', '=', self.branch_id.id),
            ], limit=1)
            approval_line_id = self.env['approval.workflow.line'].search([
                ('sequence', '=', 1),
                ('workflow_id', '=', approval_id.id),
                ('level', '=', self.env.user.level)
            ], limit=1)
                                
            if approval_line_id:
                first_user = approval_line_id.user_id.id

            if first_user:
                self.env['mail.activity'].sudo().create({
                    'activity_type_id': 4,
                    'res_model_id': rkap_model_id.id,
                    'res_id': res.id,
                    'user_id': first_user,
                    'date_deadline': fields.Date.today() + timedelta(days=2),
                    'state': 'planned',
                    'summary': "Harap segera men-submit data RKAP."
                })

            else:
                raise ValidationError("Settingan untuk approval dan/atau dokumen belum dikonfigurasi. Silakan hubungi Administrator.")

class RKAPApprovalLine(models.Model):
    _name = 'rkap.approval.line'
    _description = 'List Riwayat Approval RKAP'

    rkap_id = fields.Many2one('account.keuangan.rkap', string='No. RKAP')
    user_id = fields.Many2one('res.users', string='User')
    date = fields.Datetime(string='Date')
    note = fields.Char(string='Note')
    id_formatted_date = fields.Char(
        string="Formatted Date", compute="_compute_id_formatted_date", store=True
    )

    @api.depends("date")
    def _compute_id_formatted_date(self):
        wib_tz = pytz.timezone("Asia/Jakarta")
        for record in self:
            if record.date:
                local_dt = record.date.astimezone(wib_tz)
                record.id_formatted_date = local_dt.strftime("%-d %B %Y pada jam %H:%M WIB")
            else:
                record.id_formatted_date = "-"

class RKAPLinesDro(models.Model):
    _inherit = 'account.keuangan.rkap.line'

    branch_id = fields.Many2one('res.branch', string='Cabang', related='rkap_id.branch_id', store=True)
    header_state = fields.Selection([], string="Header Status", related="rkap_id.state", store=True)
    item_type = fields.Selection([
        ('item_usaha', 'Usaha'),
        ('item_umum', 'Umum')
    ], compute='_compute_item_type_rkap', store=True, string='Tipe Item')
    is_approved_by_divs = fields.Boolean(string='Approved by Kadiv', default=False)
    approval_status = fields.Char(
        string="Approval Status", compute="_compute_approval_status", store=True
    )

    def _compute_approval_status(self):
        for record in self:
            record.approval_status = "APPROVED" if record.is_approved_by_divs else ""

    @api.depends('kode_anggaran_id.kode_anggaran')
    def _compute_item_type_rkap(self):
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

    def action_approve_item(self):
        if self.env.user.level not in ['usaha', 'umum']:
            raise ValidationError('Hak akses user Anda tidak berhak untuk approve Item RKAP.')
        else:
            for line in self:
                if line.header_state != 'approved':
                    if not line.is_approved_by_divs:
                        line.is_approved_by_divs = True
                        self.env['rkap.approval.line'].sudo().create({
                            'user_id': self._uid,
                            'date': datetime.now(),
                            'note': f'Data RKAP telah di-approve oleh {self.env.user.name} sebagai {self.env.user.level}.',
                            'rkap_id': self.rkap_id.id
                        })
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': 'Berhasil',
                                'message': f'Item RKAP {line.rkap_id.name} kode {line.kode_anggaran_id.kode_anggaran} dengan deskripsi {line.deskripsi} sudah di-approve oleh {self.env.user.name} sebagai {self.env.user.level}.',
                                'type': 'success',
                                'sticky': False,
                                'next': {'type': 'ir.actions.client', 'tag': 'reload'}
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
                                'next': {'type': 'ir.actions.client', 'tag': 'reload'}
                            }
                        }
                else:
                    raise ValidationError('Item RKAP ini sudah di-approve oleh divisi terkait!')
