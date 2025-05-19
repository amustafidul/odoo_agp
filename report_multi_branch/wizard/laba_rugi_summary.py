from odoo import fields, api, models, _
from odoo.exceptions import UserError
from datetime import datetime

import ast

class LabaRugiSummaryWizard(models.Model):
    _name = "laba_rugi.summary.mb.wizard"
    _description = "Laba Rugi Wizard"
    
    account_report_id = fields.Many2one('account.financial.report', string='Account Reports', required=True)
    financial_param_id = fields.Many2one('financial.param', string='Financial Param')
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
        
        # data['account_lines'] = self.get_account_lines()
        self.compute_formula(previous_year, current_year)
        account_lines = []
        for line in self.financial_param_id.sub_param_ids.filtered(lambda x:not x.invisible):
            account_lines.append({
                'name1': line.name,
                'name2': line.name_eng,
                'balance1': line.balance1,
                'balance2': line.balance2,
                'type': line.type,
                'level': line.level,
                'bold': line.bold,
                'blank': line.blank,
            })
        data['account_lines'] = account_lines
        return self.env.ref('report_multi_branch.action_report_laba_rugi_summary').report_action(self, data=data)
    
    
    def check_report_laba_rugi(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/laba_rugi_summary/export/%s' % (self.id),
            'target': 'new',
        }




    def compute_formula(self, previous_year, current_year):
        def compute_multi_account_balance(account_ids, previous_year, current_year):
            if account_ids:
                self.env.cr.execute("""
                select 
                    COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM date) = %s then balance else 0 end), 0) as balance1
                    , COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM date) = %s then balance else 0 end), 0) as balance2
                from account_move_line
                where account_id in %s and parent_state = 'posted'
                """%(str(current_year), str(previous_year), str(tuple(account_ids.ids)).replace(',)',')')))
                result = self.env.cr.dictfetchall()[0]
                return result
        
        def compute_single_code1(rec, code, params1, parent_code=None):
            line = self.env['financial.param.line'].sudo().search([
                ('param_id', '=', rec.id),
                ('code', '=', code)
            ])
            if code in params1:
                line.balance1 = params1[code]
                return params1[code]  # Return the value if it's already computed
        
            if not line:
                raise UserError(_('Parameter dengan kode %s error (kode: %s tidak ditemukan)' % (parent_code, code)))
            
            if line.type == 'formula':
                formula = line.formula
                if formula:
                    parse_code = ast.parse(formula)
                    for node in ast.walk(parse_code):
                        if isinstance(node, ast.Name):
                            sub_code = node.id
                            if sub_code != code:  # Avoid infinite recursion for circular dependencies
                                balance1 = compute_single_code1(rec, sub_code, params1, line.code)
                                params1[sub_code] = balance1  # Update params with computed value
                    
                    locals().update(params1)
                    try:
                        params1[code] = eval(formula)
                    except Exception as e:
                        raise UserError(_('Parameter dengan kode %s error: %s' % (line.code, e)))
                    
                    line.balance1 = params1[code]
            else:
                params1[code] = line.balance1
            return line.balance1
        
        
        def compute_single_code2(rec, code, params2, parent_code=None):
            line = self.env['financial.param.line'].sudo().search([
                ('param_id', '=', rec.id),
                ('code', '=', code)
            ])
            if code in params2:
                line.balance2 = params2[code]
                return params2[code]  # Return the value if it's already computed
        
            if not line:
                raise UserError(_('Parameter dengan kode %s error (kode: %s tidak ditemukan)' % (parent_code, code)))
            
            if line.type == 'formula':
                formula = line.formula
                if formula:
                    parse_code = ast.parse(formula)
                    for node in ast.walk(parse_code):
                        if isinstance(node, ast.Name):
                            sub_code = node.id
                            if sub_code != code:  # Avoid infinite recursion for circular dependencies
                                balance2 = compute_single_code2(rec, sub_code, params2, line.code)
                                params2[sub_code] = balance2  # Update params with computed value
                    
                    locals().update(params2)
                    try:
                        params2[code] = eval(formula)
                    except Exception as e:
                        raise UserError(_('Parameter dengan kode %s error: %s' % (line.code, e)))
                    
                    line.balance2 = params2[code]
            else:
                params2[code] = line.balance2
            return line.balance2

        
        for rec in self:
            previous_year = int(rec.periode) - 1
            current_year = rec.periode
            
            params1 = {}
            params2 = {}
            for line in rec.financial_param_id.sub_param_ids.filtered(lambda x:x.type == 'account'):
                value = compute_multi_account_balance(line.account_ids, previous_year, current_year)
                # print(value)
                params1[line.code] = value['balance1']
                params2[line.code] = value['balance2']

            for line in rec.financial_param_id.sub_param_ids.filtered(lambda x:x.type == 'formula'):
                compute_single_code1(rec.financial_param_id, line.code, params1)
                compute_single_code2(rec.financial_param_id, line.code, params2)
                line.balance1 = params1[line.code]
                line.balance2 = params2[line.code]


    
    
    
    
    
    # def _compute_account_balance(self, accounts, previous_year, current_year):
    #     mapping = {
    #         'balance1': f"SUM(CASE WHEN EXTRACT(YEAR FROM date) = {str(current_year)} then balance else 0 end) as balance1",
    #         'balance2': f"SUM(CASE WHEN EXTRACT(YEAR FROM date) = {str(previous_year)} then balance else 0 end) as balance2",
    #     }

    #     res = {}
    #     for account in accounts:
    #         res[account.id] = dict.fromkeys(mapping, 0.0)
    #     if accounts:
    #         tables, where_clause, where_params = self.env['account.move.line']._query_get()
    #         tables = tables.replace('"', '') if tables else "account_move_line"
    #         wheres = [""]
    #         if where_clause.strip():
    #             wheres.append(where_clause.strip())
    #         filters = " AND ".join(wheres)
    #         query = "SELECT account_id as id, " + ', '.join(mapping.values()) + \
    #                    " FROM " + tables + \
    #                    " WHERE account_id IN %s " \
    #                         + filters + \
    #                    " GROUP BY account_id"
    #         params = (tuple(accounts._ids),) + tuple(where_params)
    #         self.env.cr.execute(query, params)
    #         for row in self.env.cr.dictfetchall():
    #             res[row['id']] = row
    #     return res


    # def _compute_multi_account_balance(self, report_multi_account, previous_year, current_year):
    #     res = {}
    #     for multi_account in report_multi_account:
    #         if multi_account.account_ids:
    #             self.env.cr.execute("""
    #             select 
    #                 COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM date) = %s then balance else 0 end), 0) as balance1
    #                 , COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM date) = %s then balance else 0 end), 0) as balance2
    #             from account_move_line
    #             where account_id in %s
    #             """%(str(current_year), str(previous_year), str(tuple(multi_account.account_ids.ids)).replace(',)',')')))
    #             res[multi_account.id] = self.env.cr.dictfetchall()[0]
    #     return res

    
    # def _compute_report_balance(self, reports, previous_year, current_year):
    #     res = {}
    #     fields = ['balance1', 'balance2']
    #     for report in reports:
    #         if report.id in res:
    #             continue
    #         res[report.id] = dict((fn, 0.0) for fn in fields)
    #         # print(dict((fn, 0.0) for fn in fields))
    #         if report.type == 'accounts':
    #             # it's the sum of the linked accounts
    #             res[report.id]['account'] = self._compute_account_balance(report.account_ids, previous_year, current_year)
    #             for value in res[report.id]['account'].values():
    #                 for field in fields:
    #                     res[report.id][field] += value.get(field)
    #         elif report.type == 'account_type':
    #             # it's the sum the leaf accounts with such an account type
    #             accounts = self.env['account.account'].search([('account_type', 'in', report.account_type_ids.mapped('type'))])
    #             res[report.id]['account'] = self._compute_account_balance(accounts, previous_year, current_year)
    #             for value in res[report.id]['account'].values():
    #                 for field in fields:
    #                     res[report.id][field] += value.get(field)
    #         elif report.type == 'multi_accounts':
    #             res[report.id]['multi_accounts'] = self._compute_multi_account_balance(report.multi_account_ids, previous_year, current_year)
    #             print(res[report.id]['multi_accounts'].values())
    #             for value in res[report.id]['multi_accounts'].values():
    #                 for field in fields:
    #                     res[report.id][field] += value.get(field)
    #         elif report.type == 'account_report' and report.account_report_id:
    #             # it's the amount of the linked report
    #             res2 = self._compute_report_balance(report.account_report_id, previous_year, current_year)
    #             for key, value in res2.items():
    #                 for field in fields:
    #                     res[report.id][field] += value[field]
    #         elif report.type == 'sum':
    #             # it's the sum of the children of this account.report
    #             res2 = self._compute_report_balance(report.children_ids, previous_year, current_year)
    #             for key, value in res2.items():
    #                 for field in fields:
    #                     res[report.id][field] += value[field]
    #     return res

    
    # def get_account_lines(self):
    #     lines = []
    #     account_report = self.env['account.financial.report'].search([('id', '=', self.account_report_id.id)])
    #     child_reports = account_report._get_children_by_order()
    #     previous_year = int(self.periode) - 1
    #     current_year = self.periode
    #     res = self._compute_report_balance(child_reports, previous_year, current_year)
    #     for report in child_reports:
    #         type_report = 'head'
    #         if report.type == 'account_report':
    #             type_report = 'total'
    #         vals = {
    #             'report': report,
    #             'account_id': False,
    #             'name1': report.name or '',
    #             'name2': report.name_eng or '',
    #             'level': report.level,
    #             'balance1': res[report.id]['balance1'],
    #             'balance2': res[report.id]['balance2'],
    #             'type': type_report,
    #         }
    #         lines.append(vals)
    #         if report.display_detail == 'no_detail':
    #             #the rest of the loop is used to display the details of the financial report, so it's not needed here.
    #             continue
            
    #         if res[report.id].get('account'):
    #             sub_lines = []
    #             for account_id, value in res[report.id]['account'].items():
    #                 account = self.env['account.account'].browse(account_id)
    #                 vals = {
    #                     'report': report,
    #                     'account_id': account.id,
    #                     'name1': account.name or '',
    #                     'name2': account.name_eng or '',
    #                     'level': report.level + 1,
    #                     'balance1': value['balance1'],
    #                     'balance2': value['balance2'],
    #                     'type': 'subline',
    #                 }
    #                 sub_lines.append(vals)
    #             lines += sorted(sub_lines, key=lambda sub_line: sub_line['name1'] and sub_line['name2'])
    #         if res[report.id].get('multi_accounts'):
    #             sub_lines = []
    #             # print(res[report.id]['multi_accounts'].items())
    #             for account_id, value in res[report.id]['multi_accounts'].items():
    #                 account = self.env['multi.accounts.financial.report'].browse(account_id)
    #                 vals = {
    #                     'report': report,
    #                     'account_id': False,
    #                     'name1': account.name or '',
    #                     'name2': account.name_eng or '',
    #                     'level': report.level + 1,
    #                     'balance1': value['balance1'],
    #                     'balance2': value['balance2'],
    #                     'type': 'subline',
    #                 }
    #                 sub_lines.append(vals)
    #             lines += sub_lines
    #     return lines