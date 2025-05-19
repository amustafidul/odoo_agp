from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)


class PersetujuanAnggaran(models.Model):
    _name = 'account.keuangan.pa'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Surat Persetujuan Anggaran'

    name = fields.Char(string='Persetujuan Anggaran Number', required=True, copy=False, readonly=True, default=lambda self: _('New'), tracking=True)
    unit_penempatan_id = fields.Many2one('hr.employee.unit', string='Kepada', required=True, tracking=True)
    unit_penempatan_ids = fields.Many2one('hr.employee.unit', string='Dari', required=True, tracking=True)
    dibayarkan = fields.Char(string='Dibayarkan', required=True, tracking=True)
    alamat = fields.Text(string='Alamat', tracking=True)
    disiapkan = fields.Char(string='Disiapkan Oleh', required=True, tracking=True)
    diminta = fields.Char(string='Diminta Oleh', required=True, tracking=True)
    bidang_anggaran = fields.Char(string='Kepala Bidang Anggaran', required=True, tracking=True)
    div_keuangan = fields.Char(string='Kepala Divisi Keuangan', required=True, tracking=True)
    direktur_ops = fields.Char(string='Direktur Operasional', required=True, tracking=True)
    direktur_ksdm = fields.Char(string='Direktur Keuangan & SDM', required=True, tracking=True)
    direktur_utama = fields.Char(string='Direktur Utama', required=True, tracking=True)
    pa_line_ids = fields.One2many('account.keuangan.pa.line', 'pa_id', string='Persetujuan Anggaran Lines')
    approval_step = fields.Integer(string='Approval Step', default=1)
    history_approval_ids = fields.One2many('spa.approval.line', 'pa_id', string='List Riwayat Approval')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('on_review', 'On Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):            
            # Get the date details
            date_str = vals.get('date', fields.Date.context_today(self))
            date_obj = fields.Date.from_string(date_str) if isinstance(date_str, str) else date_str
            year = date_obj.strftime('%Y')
            month = int(date_obj.strftime('%m'))
            roman_month = self._to_roman(month)
            
            # Get the default branch of the user
            user = self.env.user
            default_branch = user.branch_id[0] if user.branch_id else None
            branch_code = default_branch.code if default_branch else 'KOSONG'
            
            # Get the department code of the user
            # department_code = user.department_id.kode if user.department_id else 'NO_DEPT'
            
            # Generate the custom sequence number
            sequence_code = self.env['ir.sequence'].next_by_code('report.spp') or '0000'

            # Generate the custom sequence
            vals['name'] = f'{sequence_code}/SPA-{branch_code}/{roman_month}/{year}'
        
        # return super(PersetujuanAnggaran, self).create(vals)
        spa = super(PersetujuanAnggaran, self).create(vals)
        if spa:
            spa.assign_todo_first()

        return spa

    @staticmethod
    def _to_roman(month):
        roman = {
            1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI',
            7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X', 11: 'XI', 12: 'XII'
        }
        return roman.get(month, '')
    
    # def action_submit(self):
    #     if not self.pa_line_ids:
    #         raise ValidationError('List Persetujuan Anggaran tidak boleh kosong. Mohon isi terlebih dahulu!')

    #     cek = False
    #     spa_model_id = self.env['ir.model'].search([('model', '=', 'account.keuangan.pa')], limit=1)
    #     approval_id = self.env['approval.workflow'].sudo().search([
    #         ('name', '=', 'SPA'),
    #         ('res_model', '=', spa_model_id.id)
    #     ], limit=1)

    #     if not approval_id:
    #         raise ValidationError('Approval setting untuk SPA tidak ditemukan. Silakan hubungi Administrator.')

    #     approval_line_id = self.env['approval.workflow.line'].search([
    #         ('sequence', '=', 1),
    #         ('workflow_id', '=', approval_id.id),
    #     ], limit=1)

        # if approval_line_id.user_id.id == self._uid:
        #     cek = True
        # else:
        #     raise ValidationError('Role berjenjang untuk approval SPA belum di-setting. Silakan hubungi Administrator.')

        # if cek == True:
        #     first_user = False
        #     if self.activity_ids:
        #         for x in self.activity_ids.filtered(lambda x: x.status != 'approved'):
        #             if x.user_id.id == self._uid:
        #                 x.status = 'approved'
        #                 x.action_done()
        #         self.state = 'on_review'
        #         self.approval_step += 1
        #         level = self.env.user.level
        #         level_val = dict(self.env['res.users']._fields['level'].selection).get(level, level)
        #         self.env['spa.approval.line'].sudo().create({
        #             'user_id': self._uid,
        #             'date': datetime.now(),
        #             'note': f'Data SPA telah di-submit oleh {self.env.user.name} {level_val}.',
        #             'pa_id': self.id
        #         })

        #         approval_line = self.env['approval.workflow.line'].search([
        #             ('workflow_id', '=', approval_id.id),
        #             ('sequence', '=', self.approval_step + 1),
        #             ('level', '=', self.env.user.level)
        #         ], limit=1)
        #         user_id_next = approval_line.user_id
        #         if user_id_next:
        #             first_user = user_id_next.id

        #             if first_user:
        #                 self.env['mail.activity'].sudo().create({
        #                     'activity_type_id': 4,
        #                     'res_model_id': self.env['ir.model'].sudo().search([('model', '=', 'account.keuangan.pa')], limit=1).id,
        #                     'res_id': self.id,
        #                     'user_id': first_user,
        #                     'date_deadline': fields.Date.today() + timedelta(days=2),
        #                     'state': 'planned',
        #                     'status': 'to_approve',
        #                     'summary': """Harap segera meng-approve data SPA."""
        #                 })

        # else:
        #     raise ValidationError('Hak akses user Anda tidak berhak untuk submit.')
    
    def action_approve(self):
        cek = False
        pa_model_id = self.env['ir.model'].search([('model', '=', 'account.keuangan.pa')], limit=1)
        approval_id = self.env['approval.workflow'].sudo().search([
            ('name', '=', 'SPA'),
            ('res_model', '=', pa_model_id.id)
        ], limit=1)

        if not approval_id:
            raise ValidationError('Approval setting untuk menu SPA tidak ditemukan. Silakan hubungi Administrator.')

        approval_line_id = self.env['approval.workflow.line'].search([
            ('sequence', '=', self.approval_step),
            ('workflow_id', '=', approval_id.id),
            # ('level', '=', self.env.user.level)
        ], limit=1)

        user_id = approval_line_id.user_id
        if user_id:
            if self._uid == user_id.id:
                cek = True

        if cek == True:
            if approval_id.total_approve == self.approval_step:
                self.state = 'approved'

                level = self.env.user.level
                level_val = dict(self.env['res.users']._fields['level'].selection).get(level, level)
                level_bod = self.env.user.bod_level
                level_val_bod = dict(self.env['res.users']._fields['bod_level'].selection).get(level_bod, level_bod)
                if level == 'bod':
                    self.env['spa.approval.line'].create({
                        'user_id': self._uid,
                        'date': datetime.now(),
                        'note': f'Diverifikasi dan di-approve oleh {self.env.user.name} sebagai {level_val} {level_val_bod}.',
                        'pa_id': self.id
                    })
                else:
                    self.env['spa.approval.line'].create({
                        'user_id': self._uid,
                        'date': datetime.now(),
                        'note': f'Diverifikasi dan di-approve oleh {self.env.user.name} sebagai {level_val}.',
                        'pa_id': self.id
                    })

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
                            'res_model_id': self.env['ir.model'].sudo().search([('model', '=', 'account.keuangan.pa')], limit=1).id, 
                            'res_id': self.id, 
                            'user_id': first_user,  
                            'date_deadline': fields.Date.today() + timedelta(days=2), 
                            'state': 'planned', 
                            'status': 'to_approve', 
                            'summary': """Harap segera meng-approve data SPA.""" 
                        }) 
                        level = self.env.user.level
                        level_val = dict(self.env['res.users']._fields['level'].selection).get(level, level)
                        self.env['spa.approval.line'].create({ 
                            'user_id': self._uid, 
                            'date': datetime.now(),
                            'note': f'Di-approve oleh {self.env.user.name} sebagai {level_val}', 
                            'pa_id': self.id 
                        })
                        if self.activity_ids:
                            for x in self.activity_ids.filtered(lambda x: x.status != 'approved'):
                                if x.user_id.id == self._uid:
                                    x.status = 'approved'
                                    x.sudo().action_done()
                    else:
                        raise ValidationError('User role untuk approval Surat Persetujuan Anggaran (SPA) selanjutnya belum di-setting, silakan hubungi Administrator.')

        else:
            raise ValidationError('Hak akses user anda tidak berhak untuk approve.')

    def assign_todo_first(self):
        model_model = self.env['ir.model'].sudo()
        spa_model_id = model_model.search([('model', '=', 'account.keuangan.pa')], limit=1)
        for res in self:
            res.approval_step = 1
            res.state = 'on_review'
            first_user = False
            approval_id = self.env['approval.workflow'].sudo().search([('res_model', '=', spa_model_id.id)], limit=1)
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
                    'res_model_id': spa_model_id.id,
                    'res_id': res.id,
                    'user_id': first_user,
                    'date_deadline': fields.Date.today() + timedelta(days=2),
                    'state': 'planned',
                    'summary': "Harap segera meng-approve data Surat Persetujuan Anggaran (SPA)."
                })
            
            else:
                raise ValidationError("Settingan untuk approval SPA belum dikonfigurasi. Silakan hubungi Administrator.")
            
    def action_reject(self):
        if self.activity_user_id.id == self._uid:
            action = {
                'name': ('Alasan Reject SPA'),
                'type': "ir.actions.act_window",
                'res_model': 'pa.reject.wizard',
                'view_type': 'form',
                'target': 'new',
                'view_mode': 'form',
                'context': {'active_id': self.id},
                'view_id': self.env.ref('agp_keuangan_ib.pa_reject_wizard_form').id,
            }
            return action
        else:
            raise ValidationError('Hak akses user Anda tidak berhak untuk reject!')

class PersetujuanAnggaranLine(models.Model):
    _name = 'account.keuangan.pa.line'
    _description = 'Persetujuan Anggaran Line'

    def _get_years(self):
        current_year = datetime.now().year
        return [(str(year), str(year)) for year in range(current_year - 1, current_year + 10)]
    
    pa_id = fields.Many2one('account.keuangan.pa', string='Persetujuan Anggaran', required=True)
    kode_anggaran_id = fields.Many2one('account.keuangan.kode.anggaran', string='Kode Anggaran', required=True, tracking=True)
    deskripsi = fields.Text(string='Deskripsi Anggaran', readonly=True, tracking=True)
    account_code_id = fields.Many2one('account.account', string='Account Code', readonly=True, tracking=True, related='kode_anggaran_id.account_code_id')
    rincian_permintaan = fields.Char(string='Nomor Referensi', tracking=True)
    periode = fields.Selection(selection=_get_years, string="Tahun Anggaran", required=True)
    saldo = fields.Float(string='Saldo Terkini', readonly=True, store=True, compute='_compute_saldo')
    branch_id = fields.Many2one('res.branch', string='Cabang')
    saldo_penambahan = fields.Float(string='Nominal Penambahan Saldo')

    def read(self, fields=None, load='_classic_read'):
        records = super(PersetujuanAnggaranLine, self).read(fields, load)

        if not fields or 'saldo' in fields:
            for record_dict in records:
                record = self.browse(record_dict['id'])  # Convert dictionary to recordset
                record._compute_saldo()  # Manually trigger compute
                
        return records

    @api.depends('kode_anggaran_id', 'branch_id')
    def _compute_saldo(self):
        for record in self:
            if record.kode_anggaran_id and record.branch_id:
                saldo_record = self.env['account.keuangan.saldo'].search([
                    ('kode_anggaran_id', '=', record.kode_anggaran_id.id),
                    ('branch_id', '=', record.branch_id.id)
                ], limit=1)
                record.saldo = saldo_record.saldo if saldo_record else 0.0
            else:
                record.saldo = 0.0

    @api.onchange('kode_anggaran_id')
    def _onchange_kode_anggaran_id(self):
        if self.kode_anggaran_id:
            self.deskripsi = self.kode_anggaran_id.deskripsi
            self.account_code_id = self.kode_anggaran_id.account_code_id
        else:
            self.deskripsi = False
            self.account_code_id = False

    @api.model
    def create(self, vals):
        if vals.get('kode_anggaran_id'):
            kode_anggaran = self.env['account.keuangan.kode.anggaran'].browse(vals['kode_anggaran_id'])
            vals.update({
                'deskripsi': kode_anggaran.deskripsi,
                'account_code_id': kode_anggaran.account_code_id.id,
            })
        return super(PersetujuanAnggaranLine, self).create(vals)

    def write(self, vals):
        if vals.get('kode_anggaran_id'):
            kode_anggaran = self.env['account.keuangan.kode.anggaran'].browse(vals['kode_anggaran_id'])
            vals.update({
                'deskripsi': kode_anggaran.deskripsi,
                'account_code_id': kode_anggaran.account_code_id.id,
            })
        return super(PersetujuanAnggaranLine, self).write(vals)
    
class PersetujuanAnggaranApprovalLine(models.Model):
    _name = 'spa.approval.line'
    _description = 'List Riwayat Approval SPA'

    pa_id = fields.Many2one('account.keuangan.pa', string='No. SPA')
    user_id = fields.Many2one('res.users', string='User')
    date = fields.Datetime(string='Date')
    note = fields.Char(string='Note')