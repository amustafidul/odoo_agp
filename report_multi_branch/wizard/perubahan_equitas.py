from odoo import fields, models, api, tools, _
from odoo.exceptions import UserError
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
import babel

class PerubahanEquitasWizard(models.Model):
    _name = "perubahan.equitas.wizard"
    _description = "Perubahan Equitas Wizard"
    
    account_report_id = fields.Many2one('account.financial.report', string='Account Reports', required=True)
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    periode = fields.Selection(
        [(str(year), str(year)) for year in range(datetime.now().year - 100, datetime.now().year + 100)]
        , default=str(datetime.now().year)
        , string='Periode')

    
    def action_view(self):
        data = {}
        data['form'] = self.read()[0]
        
        previous_year = str(int(self.periode) - 1)
        data['previous_year'] = previous_year
        
        current_year = str(self.periode)
        data['current_year'] = current_year

        pre_B2 = self.get_value("('3101002')", previous_year)
        pre_C2 = self.get_value("('3203002')", previous_year)
        pre_total_G2 = pre_B2['balance'] + pre_C2['balance']
        pre_E3 = self.get_value("('2203101', '2203102', '2203103')", previous_year)
        pre_total_G3 = pre_E3['balance']
        pre_E4 = self.get_value("('3302001')", previous_year)
        pre_total_G4 = pre_E4['balance']
        pre_F5 = self.get_value("('9900003','9900004')", previous_year)
        pre_total_G5 = pre_F5['balance']

        pre_total_B6 = pre_B2['balance']
        pre_total_C6 = pre_C2['balance']
        pre_total_E6 = pre_E3['balance'] + pre_E4['balance']
        pre_total_F6 = pre_F5['balance']
        pre_total_G6 = pre_total_G2 + pre_total_G3 + pre_total_G4 + pre_total_G5


        cur_B2 = self.get_value("('3101002')", current_year)
        cur_C2 = self.get_value("('3203002')", current_year)
        cur_total_G2 = cur_B2['balance'] + cur_C2['balance']
        cur_E3 = self.get_value("('2203101', '2203102', '2203103')", current_year)
        cur_total_G3 = cur_E3['balance']
        cur_E4 = self.get_value("('3302001')", current_year)
        cur_total_G4 = cur_E4['balance']
        cur_F5 = self.get_value("('9900003','9900004')", current_year)
        cur_total_G5 = cur_F5['balance']

        cur_total_B6 = cur_B2['balance']
        cur_total_C6 = cur_C2['balance']
        cur_total_E6 = cur_E3['balance'] + cur_E4['balance']
        cur_total_F6 = cur_F5['balance']
        cur_total_G6 = cur_total_G2 + cur_total_G3 + cur_total_G4 + cur_total_G5

        data['value'] = {
            'pre_B2': pre_B2['balance'],
            'pre_C2': pre_C2['balance'],
            'pre_total_G2': pre_total_G2,
            'pre_E3': pre_E3['balance'],
            'pre_total_G3': pre_total_G3,
            'pre_E4': pre_E4['balance'],
            'pre_total_G4': pre_total_G4,
            'pre_F5': pre_F5['balance'],
            'pre_total_G5': pre_total_G5,
            'pre_total_B6': pre_total_B6,
            'pre_total_C6': pre_total_C6,
            'pre_total_E6': pre_total_E6,
            'pre_total_F6': pre_total_F6,
            'pre_total_G6': pre_total_G6,
            
            'cur_B2': cur_B2['balance'],
            'cur_C2': cur_C2['balance'],
            'cur_total_G2': cur_total_G2,
            'cur_E3': cur_E3['balance'],
            'cur_total_G3': cur_total_G3,
            'cur_E4': cur_E4['balance'],
            'cur_total_G4': cur_total_G4,
            'cur_F5': cur_F5['balance'],
            'cur_total_G5': cur_total_G5,
            'cur_total_B6': cur_total_B6,
            'cur_total_C6': cur_total_C6,
            'cur_total_E6': cur_total_E6,
            'cur_total_F6': cur_total_F6,
            'cur_total_G6': cur_total_G6,
        }
        
        return self.env.ref('report_multi_branch.action_report_perubahan_equitas').report_action(self, data=data)

    
    def get_value(self, code_accounts, year):
        self._cr.execute(f"""
        select ABS(COALESCE(SUM(aml.balance), 0)) as balance
        from account_move_line aml
        join account_move am on aml.move_id = am.id
        join account_account aa on aml.account_id = aa.id
        where am.state = 'posted' and aa.code in {code_accounts} and EXTRACT(YEAR FROM aml.date) = {year}
        """)
        result = self._cr.dictfetchone()
        return result
    
    
    def check_report_perubahan_equitas(self):
        # return {
        #     'name': 'Laporan Perubahan Equitas',
        #     'type': 'ir.actions.act_url',
        #     'url': str('/report_multi_branch/static/src/xlsxv1/ekuitas.xlsx'),
        #     'target': 'download',
        # }

        return {
            'type': 'ir.actions.act_url',
            'url': '/perubahan_equitas/export/%s' % (self.id),
            'target': 'new',
        }