from odoo import fields, models, api, tools, _
from odoo.exceptions import UserError
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
import babel


class AgingPosisiARWizard(models.TransientModel):
    _name = 'aging.posisi.ar.wizard'

    periode = fields.Date(string='Periode', required=True)

    def action_view(self):
        data = {}
        data['form'] = self.read()[0]
        periode = tools.ustr(
            babel.dates.format_date(
                date=datetime.combine(self.periode, time.min),
                format="d MMMM y",
                locale="id_ID",
            )
        )
        data['periode'] = periode.upper()

        
        piutang_emkl = self.get_value(account_code=('1103201','1103301'))
        data['piutang_emkl'] = {
            'piutang_emkl_total': piutang_emkl['total'],
            'piutang_emkl_total1': piutang_emkl['total1'],
            'piutang_emkl_total2': piutang_emkl['total2'],
            'piutang_emkl_total3': piutang_emkl['total3'],
            'piutang_emkl_total4': piutang_emkl['total4'],
            'piutang_emkl_total5': piutang_emkl['total5'],
            'piutang_emkl_total6': piutang_emkl['total6'],
        }

        
        piutang_bongkar_muat = self.get_value(account_code=('1103202','1103302'))
        data['piutang_bongkar_muat'] = {
            'piutang_bongkar_muat_total': piutang_bongkar_muat['total'],
            'piutang_bongkar_muat_total1': piutang_bongkar_muat['total1'],
            'piutang_bongkar_muat_total2': piutang_bongkar_muat['total2'],
            'piutang_bongkar_muat_total3': piutang_bongkar_muat['total3'],
            'piutang_bongkar_muat_total4': piutang_bongkar_muat['total4'],
            'piutang_bongkar_muat_total5': piutang_bongkar_muat['total5'],
            'piutang_bongkar_muat_total6': piutang_bongkar_muat['total6'],
        }

        
        piutang_keagenan = self.get_value(account_code=('1103203','1103303'))
        data['piutang_keagenan'] = {
            'piutang_keagenan_total': piutang_keagenan['total'],
            'piutang_keagenan_total1': piutang_keagenan['total1'],
            'piutang_keagenan_total2': piutang_keagenan['total2'],
            'piutang_keagenan_total3': piutang_keagenan['total3'],
            'piutang_keagenan_total4': piutang_keagenan['total4'],
            'piutang_keagenan_total5': piutang_keagenan['total5'],
            'piutang_keagenan_total6': piutang_keagenan['total6'],
        }

        
        piutang_assist_tug = self.get_value(account_code=('1103204','1103304'))
        data['piutang_assist_tug'] = {
            'piutang_assist_tug_total': piutang_assist_tug['total'],
            'piutang_assist_tug_total1': piutang_assist_tug['total1'],
            'piutang_assist_tug_total2': piutang_assist_tug['total2'],
            'piutang_assist_tug_total3': piutang_assist_tug['total3'],
            'piutang_assist_tug_total4': piutang_assist_tug['total4'],
            'piutang_assist_tug_total5': piutang_assist_tug['total5'],
            'piutang_assist_tug_total6': piutang_assist_tug['total6'],
        }

        
        piutang_jetty_manajemen = self.get_value(account_code=('1103205','1103305'))
        data['piutang_jetty_manajemen'] = {
            'piutang_jetty_manajemen_total': piutang_jetty_manajemen['total'],
            'piutang_jetty_manajemen_total1': piutang_jetty_manajemen['total1'],
            'piutang_jetty_manajemen_total2': piutang_jetty_manajemen['total2'],
            'piutang_jetty_manajemen_total3': piutang_jetty_manajemen['total3'],
            'piutang_jetty_manajemen_total4': piutang_jetty_manajemen['total4'],
            'piutang_jetty_manajemen_total5': piutang_jetty_manajemen['total5'],
            'piutang_jetty_manajemen_total6': piutang_jetty_manajemen['total6'],
        }
        
        piutang_jasa_operasi_lainnya = self.get_value(account_code=('1103206','1103306'))
        data['piutang_jasa_operasi_lainnya'] = {
            'piutang_jasa_operasi_lainnya_total': piutang_jasa_operasi_lainnya['total'],
            'piutang_jasa_operasi_lainnya_total1': piutang_jasa_operasi_lainnya['total1'],
            'piutang_jasa_operasi_lainnya_total2': piutang_jasa_operasi_lainnya['total2'],
            'piutang_jasa_operasi_lainnya_total3': piutang_jasa_operasi_lainnya['total3'],
            'piutang_jasa_operasi_lainnya_total4': piutang_jasa_operasi_lainnya['total4'],
            'piutang_jasa_operasi_lainnya_total5': piutang_jasa_operasi_lainnya['total5'],
            'piutang_jasa_operasi_lainnya_total6': piutang_jasa_operasi_lainnya['total6'],
        }

        piutang_logistik = self.get_value(account_code=('1103207','1103307'))
        data['piutang_logistik'] = {
            'piutang_logistik_total': piutang_logistik['total'],
            'piutang_logistik_total1': piutang_logistik['total1'],
            'piutang_logistik_total2': piutang_logistik['total2'],
            'piutang_logistik_total3': piutang_logistik['total3'],
            'piutang_logistik_total4': piutang_logistik['total4'],
            'piutang_logistik_total5': piutang_logistik['total5'],
            'piutang_logistik_total6': piutang_logistik['total6'],
        }

        piutang_lain = self.get_value(account_code=('1103701','1103702','1103703','1103704','1103401','1103402','1103403','1103404','1103499'))
        data['piutang_lain'] = {
            'piutang_lain_total': piutang_lain['total'],
            'piutang_lain_total1': piutang_lain['total1'],
            'piutang_lain_total2': piutang_lain['total2'],
            'piutang_lain_total3': piutang_lain['total3'],
            'piutang_lain_total4': piutang_lain['total4'],
            'piutang_lain_total5': piutang_lain['total5'],
            'piutang_lain_total6': piutang_lain['total6'],
        }


        
        pendapatan_emkl = self.get_value(account_code=('1107101','1107201'))
        data['pendapatan_emkl'] = {
            'pendapatan_emkl_total': pendapatan_emkl['total'],
            'pendapatan_emkl_total1': pendapatan_emkl['total1'],
            'pendapatan_emkl_total2': pendapatan_emkl['total2'],
            'pendapatan_emkl_total3': pendapatan_emkl['total3'],
            'pendapatan_emkl_total4': pendapatan_emkl['total4'],
            'pendapatan_emkl_total5': pendapatan_emkl['total5'],
            'pendapatan_emkl_total6': pendapatan_emkl['total6'],
        }

        
        pendapatan_bongkar_muat = self.get_value(account_code=('1107102','1107202'))
        data['pendapatan_bongkar_muat'] = {
            'pendapatan_bongkar_muat_total': pendapatan_bongkar_muat['total'],
            'pendapatan_bongkar_muat_total1': pendapatan_bongkar_muat['total1'],
            'pendapatan_bongkar_muat_total2': pendapatan_bongkar_muat['total2'],
            'pendapatan_bongkar_muat_total3': pendapatan_bongkar_muat['total3'],
            'pendapatan_bongkar_muat_total4': pendapatan_bongkar_muat['total4'],
            'pendapatan_bongkar_muat_total5': pendapatan_bongkar_muat['total5'],
            'pendapatan_bongkar_muat_total6': pendapatan_bongkar_muat['total6'],
        }

        
        pendapatan_keagenan = self.get_value(account_code=('1107103','1107203'))
        data['pendapatan_keagenan'] = {
            'pendapatan_keagenan_total': pendapatan_keagenan['total'],
            'pendapatan_keagenan_total1': pendapatan_keagenan['total1'],
            'pendapatan_keagenan_total2': pendapatan_keagenan['total2'],
            'pendapatan_keagenan_total3': pendapatan_keagenan['total3'],
            'pendapatan_keagenan_total4': pendapatan_keagenan['total4'],
            'pendapatan_keagenan_total5': pendapatan_keagenan['total5'],
            'pendapatan_keagenan_total6': pendapatan_keagenan['total6'],
        }

        
        pendapatan_assist_tug = self.get_value(account_code=('1107104','1107204'))
        data['pendapatan_assist_tug'] = {
            'pendapatan_assist_tug_total': pendapatan_assist_tug['total'],
            'pendapatan_assist_tug_total1': pendapatan_assist_tug['total1'],
            'pendapatan_assist_tug_total2': pendapatan_assist_tug['total2'],
            'pendapatan_assist_tug_total3': pendapatan_assist_tug['total3'],
            'pendapatan_assist_tug_total4': pendapatan_assist_tug['total4'],
            'pendapatan_assist_tug_total5': pendapatan_assist_tug['total5'],
            'pendapatan_assist_tug_total6': pendapatan_assist_tug['total6'],
        }

        
        pendapatan_jetty_manajemen = self.get_value(account_code=('1107105','1107205'))
        data['pendapatan_jetty_manajemen'] = {
            'pendapatan_jetty_manajemen_total': pendapatan_jetty_manajemen['total'],
            'pendapatan_jetty_manajemen_total1': pendapatan_jetty_manajemen['total1'],
            'pendapatan_jetty_manajemen_total2': pendapatan_jetty_manajemen['total2'],
            'pendapatan_jetty_manajemen_total3': pendapatan_jetty_manajemen['total3'],
            'pendapatan_jetty_manajemen_total4': pendapatan_jetty_manajemen['total4'],
            'pendapatan_jetty_manajemen_total5': pendapatan_jetty_manajemen['total5'],
            'pendapatan_jetty_manajemen_total6': pendapatan_jetty_manajemen['total6'],
        }
        
        pendapatan_jasa_operasi_lainnya = self.get_value(account_code=('1107106','1107206'))
        data['pendapatan_jasa_operasi_lainnya'] = {
            'pendapatan_jasa_operasi_lainnya_total': pendapatan_jasa_operasi_lainnya['total'],
            'pendapatan_jasa_operasi_lainnya_total1': pendapatan_jasa_operasi_lainnya['total1'],
            'pendapatan_jasa_operasi_lainnya_total2': pendapatan_jasa_operasi_lainnya['total2'],
            'pendapatan_jasa_operasi_lainnya_total3': pendapatan_jasa_operasi_lainnya['total3'],
            'pendapatan_jasa_operasi_lainnya_total4': pendapatan_jasa_operasi_lainnya['total4'],
            'pendapatan_jasa_operasi_lainnya_total5': pendapatan_jasa_operasi_lainnya['total5'],
            'pendapatan_jasa_operasi_lainnya_total6': pendapatan_jasa_operasi_lainnya['total6'],
        }

        pendapatan_logistik = self.get_value(account_code=('1107107','1107207'))
        data['pendapatan_logistik'] = {
            'pendapatan_logistik_total': pendapatan_logistik['total'],
            'pendapatan_logistik_total1': pendapatan_logistik['total1'],
            'pendapatan_logistik_total2': pendapatan_logistik['total2'],
            'pendapatan_logistik_total3': pendapatan_logistik['total3'],
            'pendapatan_logistik_total4': pendapatan_logistik['total4'],
            'pendapatan_logistik_total5': pendapatan_logistik['total5'],
            'pendapatan_logistik_total6': pendapatan_logistik['total6'],
        }
        return self.env.ref('report_multi_branch.action_report_aging_posisi_ar').report_action(self, data=data)

    
    def get_value(self, jenis_kegiatan=False, account_code=''):
        total = total1 = total2 = total3 = total4 = total5 = total6 = 0.0
        domain = [
            ('parent_state', '=', 'posted'),
            ('account_id.code', 'in', account_code),
        ]
        # if jenis_kegiatan:
        #     domain += [('jenis_kegiatan', '=', jenis_kegiatan)]
        move_line_obj = self.env['account.move.line'].search(domain)
        
        for move_line in move_line_obj:
            month = int(((self.periode - move_line.date).days / 365) * 12)
            years = int((self.periode - move_line.date).days / 365)
            total += move_line.balance
            if month >= 1 and month <= 2:
                total1 += move_line.balance
            elif month >= 3 and month <= 6:
                total2 += move_line.balance
            elif month >= 7 and month <= 9:
                total3 += move_line.balance
            elif month >= 10 and month <= 12:
                total4 += move_line.balance
            elif years >= 1 and years <= 3:
                total5 += move_line.balance
            elif years > 3:
                total6 += move_line.balance
        # return total, total1, total2, total3, total4, total5, total6

        return {
            'total': total,
            'total1': total1,
            'total2': total2,
            'total3': total3,
            'total4': total4,
            'total5': total5,
            'total6': total6,
        }

    
    def action_xls(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/aging_posisi_ar/export/%s' % (self.id),
            'target': 'new',
        }