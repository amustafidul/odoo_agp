from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, time

import logging

_logger = logging.getLogger(__name__)


class HrLeaveDinasModifyWizard(models.TransientModel):
    _name = 'hr.leave.dinas.modify.wizard'
    _description = 'Wizard Modifikasi Perjalanan per Peserta'

    sppd_id = fields.Many2one('hr.leave.dinas', string="SPPD Induk", readonly=True)
    # Akan diisi salah satu, tergantung dari mana wizard dipanggil
    biaya_peserta_internal_id = fields.Many2one('hr.leave.dinas.biaya', string="Biaya Peserta Internal", readonly=True)
    biaya_peserta_external_id = fields.Many2one('hr.leave.dinas.external.follower.biaya',
                                                string="Biaya Pengikut Eksternal", readonly=True)

    peserta_name_display = fields.Char(string="Nama Peserta", readonly=True)
    current_date_to_display = fields.Date(string="Tgl Kembali Rencana/Efektif", readonly=True)
    current_destination_display = fields.Char(string="Tujuan Rencana/Efektif", readonly=True)

    modification_type = fields.Selection([
        ('early_return', 'Kembali Lebih Awal'),
        ('extend_days', 'Perpanjangan Hari Dinas'),
        ('change_location', 'Pindah Lokasi'),
    ], string='Jenis Modifikasi', required=True, default='early_return')

    # Field untuk input deviasi
    new_date_to = fields.Date('Tanggal Kembali Aktual Baru')  # Untuk early_return & extend_days
    new_sppd_location = fields.Char('Tujuan Baru')  # Untuk change_location
    city_transfer_date = fields.Date(string='Tgl Efektif Pindah Tujuan')  # Untuk change_location
    reason = fields.Text('Alasan Modifikasi', required=True)

    # Untuk perpanjangan
    extend_proposed_date_to_wiz = fields.Date(string="Tanggal Perpanjangan Diajukan (Wizard)")

    @api.model
    def default_get(self, fields_list):
        res = super(HrLeaveDinasModifyWizard, self).default_get(fields_list)
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')

        target_record = None
        nama_peserta = None
        tgl_kembali_efektif = None
        tujuan_efektif = None
        sppd_main_record = None

        if active_model == 'hr.leave.dinas.biaya' and active_id:
            target_record = self.env['hr.leave.dinas.biaya'].browse(active_id)
            nama_peserta = target_record.employee_id.name
            sppd_main_record = target_record.leave_dinas_id
        elif active_model == 'hr.leave.dinas.external.follower.biaya' and active_id:
            target_record = self.env['hr.leave.dinas.external.follower.biaya'].browse(active_id)
            nama_peserta = target_record.external_follower_id.name
            sppd_main_record = target_record.leave_dinas_id

        if target_record and sppd_main_record:
            tgl_kembali_efektif = target_record.effective_date_to  # Ambil dari field compute
            tujuan_efektif = target_record.deviated_destination_place or sppd_main_record.destination_place

            res.update({
                'sppd_id': sppd_main_record.id,
                'peserta_name_display': nama_peserta,
                'current_date_to_display': tgl_kembali_efektif,
                'current_destination_display': tujuan_efektif,
            })
            if active_model == 'hr.leave.dinas.biaya':
                res['biaya_peserta_internal_id'] = active_id
            elif active_model == 'hr.leave.dinas.external.follower.biaya':
                res['biaya_peserta_external_id'] = active_id
        return res

    @api.onchange('modification_type')
    def _onchange_modification_type(self):
        # Reset field berdasarkan tipe modifikasi
        if self.modification_type == 'early_return':
            self.new_sppd_location = False
            self.city_transfer_date = False
            self.extend_proposed_date_to_wiz = False
        elif self.modification_type == 'extend_days':
            self.new_sppd_location = False
            self.city_transfer_date = False
            self.new_date_to = False  # Untuk extend, tanggal ada di extend_proposed_date_to_wiz
        elif self.modification_type == 'change_location':
            self.new_date_to = False
            self.extend_proposed_date_to_wiz = False
        else:
            self.new_date_to = False
            self.new_sppd_location = False
            self.city_transfer_date = False
            self.extend_proposed_date_to_wiz = False

    def action_apply_modification(self):
        self.ensure_one()
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')

        target_biaya_record = None
        if self.biaya_peserta_internal_id:
            target_biaya_record = self.biaya_peserta_internal_id
        elif self.biaya_peserta_external_id:
            target_biaya_record = self.biaya_peserta_external_id

        if not target_biaya_record:
            raise UserError(_("Tidak bisa menemukan record biaya peserta yang akan dimodifikasi."))

        sppd_main = target_biaya_record.leave_dinas_id
        vals_to_write = {
            'is_deviated': True,
            'deviation_type': self.modification_type,
            'deviation_reason': self.reason,
        }
        pesan_nama = self.peserta_name_display
        pesan_deviasi = ""

        if self.modification_type == 'early_return':
            if not self.new_date_to:
                raise UserError(_('Tanggal Kembali Aktual Baru wajib diisi.'))
            if self.new_date_to >= self.current_date_to_display:
                raise UserError(
                    _('Tanggal kembali baru (%s) harus lebih awal dari tanggal kembali rencana/efektif (%s).') %
                    (self.new_date_to.strftime('%d-%m-%Y'), self.current_date_to_display.strftime('%d-%m-%Y')))
            vals_to_write.update({
                'deviated_date_to': self.new_date_to,
                'deviated_destination_place': False,
                'deviation_city_transfer_date': False,
                'extend_deviation_state': 'no_extension'
            })
            pesan_deviasi = _("Jenis: Kembali Lebih Awal<br/>Tgl Kembali Aktual Baru: %s") % self.new_date_to.strftime(
                '%d-%m-%Y')

        elif self.modification_type == 'extend_days':
            if not self.extend_proposed_date_to_wiz:  # Gunakan field wizard
                raise UserError(_('Tanggal Perpanjangan Diajukan wajib diisi.'))
            if self.extend_proposed_date_to_wiz <= self.current_date_to_display:
                raise UserError(
                    _('Tanggal perpanjangan baru (%s) harus setelah tanggal kembali rencana/efektif (%s).') %
                    (self.extend_proposed_date_to_wiz.strftime('%d-%m-%Y'),
                     self.current_date_to_display.strftime('%d-%m-%Y')))

            vals_to_write.update({
                'extend_deviation_state': 'waiting_approval',  # Mulai alur approval perpanjangan
                'deviated_date_to': False,  # Akan diisi setelah approval
                'deviated_destination_place': False,
                'deviation_city_transfer_date': False,
            })
            pesan_deviasi = _(
                "Jenis: Perpanjangan Hari Dinas<br/>Tgl Perpanjangan Diajukan: %s<br/>Status: Menunggu Persetujuan") % self.extend_proposed_date_to_wiz.strftime(
                '%d-%m-%Y')

            # TODO: Buat record approval di participant_extend_approval_ids
            # Logic ini perlu detail approver (MB, Kadiv, Direksi) seperti yang lama
            # Untuk sementara, kita hanya set state.
            target_biaya_record.participant_extend_approval_ids.unlink()  # Hapus approval lama jika ada
            # Contoh pembuatan approval (perlu disesuaikan dengan logic penentuan approver)
            # approvers_data = target_biaya_record.leave_dinas_id._get_expected_approver_employee_ids() # Adaptasi ini
            # for seq, approver_id in enumerate(approvers_data):
            #     self.env['hr.leave.dinas.participant.extend.approval'].create({
            #         'biaya_peserta_id': target_biaya_record.id if active_model == 'hr.leave.dinas.biaya' else False,
            #         'biaya_external_id': target_biaya_record.id if active_model == 'hr.leave.dinas.external.follower.biaya' else False,
            #         'employee_id': approver_id,
            #         'sequence': (seq + 1) * 10,
            #         'approval_type': 'mb' # atau kadiv, dll. perlu logic
            #     })


        elif self.modification_type == 'change_location':
            if not self.new_sppd_location or not self.city_transfer_date:
                raise UserError(_('Tujuan Baru dan Tanggal Efektif Pindah Tujuan wajib diisi.'))

            current_effective_date_to = self.current_date_to_display
            if self.city_transfer_date < (
            target_biaya_record.leave_dinas_id.date_from if target_biaya_record.leave_dinas_id else False) or self.city_transfer_date > current_effective_date_to:
                raise UserError(
                    _('Tanggal Efektif Pemindahan Tujuan harus di antara tanggal berangkat SPPD dan tanggal kembali efektif peserta.'))
            vals_to_write.update({
                'deviated_destination_place': self.new_sppd_location,
                'deviation_city_transfer_date': self.city_transfer_date,
                'deviated_date_to': False,
                'extend_deviation_state': 'no_extension'
            })
            pesan_deviasi = _("Jenis: Pindah Lokasi<br/>Tujuan Baru: %s<br/>Tgl Efektif Pindah: %s") % (
                self.new_sppd_location, self.city_transfer_date.strftime('%d-%m-%Y'))

        target_biaya_record.write(vals_to_write)

        sppd_main.message_post(body=_(
            "Pengajuan Deviasi SPPD untuk peserta <b>%s</b>:<br/>%s<br/><b>Alasan</b>: %s"
        ) % (pesan_nama, pesan_deviasi, self.reason))

        return {'type': 'ir.actions.act_window_close'}