from odoo import models, fields
from odoo.exceptions import UserError, ValidationError
from datetime import datetime

class BayarWizardAGPNodin(models.TransientModel):
    _name = 'nodin.bayar.wizard'
    _description = 'Nota Dinas Bayar'

    # amount_total_nodin = fields.Float(string='Jumlah Tagihan Nota Dinas', readonly=True, default=_get_default_jumlah_tagihan)
    amount_total_nodin = fields.Float(string='Jumlah Tagihan Nota Dinas', required=True)
    amount_bayar = fields.Float(string='Jumlah Bayar', required=True)

    def cancel(self):
        return

    def ok(self):
        active_id = self.env.context.get('active_id')
        if active_id:
            print('active_id',active_id)
            print('typeofactiveid',type(active_id))
            nodin_bod_id = self.env['account.keuangan.nota.dinas.bod'].sudo().browse(active_id)

            # final realisasi
            if nodin_bod_id:
                if nodin_bod_id.monitored_kkhc_ids:
                    for line_monitor in nodin_bod_id.monitored_kkhc_ids:
                        if line_monitor.kode_anggaran_id.jenis_kegiatan_id is not False:
                            coa_id = line_monitor.kode_anggaran_id.account_code_id
                            rkap_line_id = self.env['account.keuangan.rkap.line'].sudo().search([
                                ('kode_anggaran_id', '=', line_monitor.kode_anggaran_id.id),
                                ('account_code_id', '=', coa_id.id),
                                ('branch_id', '=', line_monitor.branch_id.id),
                            ], limit=1)
                            kkhc_line_id = self.env['account.keuangan.kkhc.line'].sudo().search([
                                ('kode_anggaran_id', '=', line_monitor.kode_anggaran_id.id),
                                ('account_code_id', '=', coa_id.id),
                                ('branch_id', '=', line_monitor.branch_id.id),
                            ], limit=1)
                            if rkap_line_id and kkhc_line_id:
                                amount_paid_nodin = line_monitor.nominal_pengajuan
                                current_pemakaian = rkap_line_id.pemakaian_anggaran
                                current_nominal_disetujui = kkhc_line_id.nominal_disetujui
                                current_nominal = rkap_line_id.nominal
                                current_nominal_pengajuan = kkhc_line_id.nominal_pengajuan

                                # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
                                # FINAL REALISASI RKAP
                                # FIRST WRITE
                                rkap_line_id.write({'pemakaian_anggaran': amount_paid_nodin})
                                self.env.flush_all()

                                # 🚀 Reload the updated record
                                updated_rkap_line = self.env['account.keuangan.rkap.line'].browse(rkap_line_id.id)
                                current_pemakaian = updated_rkap_line.pemakaian_anggaran  # Now it holds the updated value

                                # SECOND WRITE
                                rkap_line_id.write({'realisasi': current_nominal - current_pemakaian})

                                # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
                                # FINAL REALISASI KKHC
                                # FIRST WRITE
                                kkhc_line_id.write({'nominal_disetujui': amount_paid_nodin})
                                self.env.flush_all()

                                # 🚀 Reload the updated record
                                updated_kkhc_line = self.env['account.keuangan.kkhc.line'].browse(kkhc_line_id.id)
                                current_nominal_disetujui = updated_kkhc_line.nominal_disetujui  # Now it holds the updated value

                                # SECOND WRITE
                                kkhc_line_id.write({'sisa_pengajuan': current_nominal_pengajuan - current_nominal_disetujui})
                                # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

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

                                for doc in nodin_bod_id.document_ids.filtered(lambda x: x.state in ('uploaded','rejected')):
                                    doc.state = 'verified'

                                if nodin_bod_id.activity_ids:
                                    for x in nodin_bod_id.activity_ids.filtered(lambda x: x.status != 'approved'):
                                        if x.user_id.id == self._uid:
                                            x.status = 'approved'
                                            x.sudo().action_done()

                            else:
                                raise ValidationError(
                                    'Item RKAP dan Item KKHC Cabang atas Nota Dinas ini tidak ditemukan! Approval Nota Dinas ini tidak dapat dilanjutkan. Silakan cek kembali!'
                                )