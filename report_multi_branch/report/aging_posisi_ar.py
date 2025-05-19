from odoo import api, models, _
from odoo.exceptions import UserError


class ReportAgingPosisiAR(models.AbstractModel):
    _name = 'report.report_multi_branch.report_aging_posisi_ar'
    _description = 'Aging Posisi AR Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        active_model = self.env.context.get('active_model')
        docs = self.env[active_model].browse(self.env.context.get('active_id'))
        vals = {
            'docs': docs,
            'periode': data['periode'],
            # 'piutang_emkl': data['piutang_emkl'],
            # 'piutang_bongkar_muat': data['piutang_bongkar_muat'],
            # 'piutang_keagenan': data['piutang_keagenan'],
            # 'piutang_assist_tug': data['piutang_assist_tug'],
            # 'piutang_jetty_manajemen': data['piutang_jetty_manajemen'],
            # 'piutang_jasa_operasi_lainnya': data['piutang_jasa_operasi_lainnya'],
            # 'piutang_logistik': data['piutang_logistik'],
            # 'piutang_lain': data['piutang_lain'],
            # 'pendapatan_emkl': data['pendapatan_emkl'],
            # 'pendapatan_bongkar_muat': data['pendapatan_bongkar_muat'],
            # 'pendapatan_keagenan': data['pendapatan_keagenan'],
            # 'pendapatan_assist_tug': data['pendapatan_assist_tug'],
            # 'pendapatan_jetty_manajemen': data['pendapatan_jetty_manajemen'],
            # 'pendapatan_jasa_operasi_lainnya': data['pendapatan_jasa_operasi_lainnya'],
            # 'pendapatan_logistik': data['pendapatan_logistik'],
        }
        return vals
