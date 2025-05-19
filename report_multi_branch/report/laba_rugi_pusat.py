# -*- coding: utf-8 -*-

import time
from odoo import api, models, _
from odoo.exceptions import UserError


class ReportLabaRugiPusat(models.AbstractModel):
    _name = 'report.report_multi_branch.report_laba_rugi_pusat_mb'
    _description = 'Laba Rugi Pusat Report'


    @api.model
    def _get_report_values(self, docids, data=None):
        active_model = self.env.context.get('active_model')
        docs = self.env[active_model].browse(self.env.context.get('active_id'))
        vals = {
            'docs': docs,
        }
        return vals
    
    
    # def get_value_multi_branch(self, account_id, report, branch_id, date_from, date_to):
    #     where = f"""where am.state = 'posted' and aml.date >= '{date_from}' and aml.date <= '{date_to}'"""
    #     if account_id:
    #         where += f""" and aa.id = {int(account_id)}"""
    #     if branch_id:
    #         where += f""" and aml.branch_id = {int(branch_id)}"""
    #     if report.type == 'accounts':
    #         where += f""" and aa.id in {str(tuple(report.account_ids.ids)).replace(',)',')')}"""
    #     if report.type == 'account_type':
    #         where += f""" and aa.account_type in {str(tuple(report.account_type_ids.mapped('type'))).replace(',)',')')}"""

    #     query = f"""
    #         -- select COALESCE(SUM(aml.debit), 0) - COALESCE(SUM(aml.credit), 0) as balance
    #         select COALESCE(SUM(aml.balance), 0) as balance
    #         from account_move_line aml
    #         join account_move am on aml.move_id = am.id
    #         join account_account aa on aml.account_id = aa.id
    #         {where}
    #     """
    #     self.env.cr.execute(query)
    #     result = self.env.cr.dictfetchall()[0]
    #     # if account_id == 803:
    #     #     print(result)
    #     return result


    # def _compute_account_balance(self, accounts):
    #     """ compute the balance, debit and credit for the provided accounts
    #     """
    #     mapping = {
    #         'balance': "COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0) as balance",
    #         'debit': "COALESCE(SUM(debit), 0) as debit",
    #         'credit': "COALESCE(SUM(credit), 0) as credit",
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
    #         request = "SELECT account_id as id, " + ', '.join(mapping.values()) + \
    #                    " FROM " + tables + \
    #                    " WHERE account_id IN %s " \
    #                         + filters + \
    #                    " GROUP BY account_id"
    #         params = (tuple(accounts._ids),) + tuple(where_params)
    #         self.env.cr.execute(request, params)
    #         for row in self.env.cr.dictfetchall():
    #             res[row['id']] = row
    #     return res

    
    # def _compute_report_balance(self, reports):
    #     '''returns a dictionary with key=the ID of a record and value=the credit, debit and balance amount
    #        computed for this record. If the record is of type :
    #            'accounts' : it's the sum of the linked accounts
    #            'account_type' : it's the sum of leaf accoutns with such an account_type
    #            'account_report' : it's the amount of the related report
    #            'sum' : it's the sum of the children of this record (aka a 'view' record)'''
    #     res = {}
    #     fields = ['credit', 'debit', 'balance']
    #     for report in reports:
    #         if report.id in res:
    #             continue
    #         res[report.id] = dict((fn, 0.0) for fn in fields)
    #         if report.type == 'accounts':
    #             # it's the sum of the linked accounts
    #             res[report.id]['account'] = self._compute_account_balance(report.account_ids)
    #             for value in res[report.id]['account'].values():
    #                 for field in fields:
    #                     res[report.id][field] += value.get(field)
    #         elif report.type == 'account_type':
    #             # it's the sum the leaf accounts with such an account type
    #             accounts = self.env['account.account'].search([('account_type', 'in', report.account_type_ids.mapped('type'))])

    #             res[report.id]['account'] = self._compute_account_balance(accounts)
    #             for value in res[report.id]['account'].values():
    #                 for field in fields:
    #                     res[report.id][field] += value.get(field)
    #         elif report.type == 'account_report' and report.account_report_id:
    #             # it's the amount of the linked report
    #             res2 = self._compute_report_balance(report.account_report_id)
    #             for key, value in res2.items():
    #                 for field in fields:
    #                     res[report.id][field] += value[field]
    #         elif report.type == 'sum':
    #             # it's the sum of the children of this account.report
    #             res2 = self._compute_report_balance(report.children_ids)
    #             for key, value in res2.items():
    #                 for field in fields:
    #                     res[report.id][field] += value[field]
    #     return res
    
    # def get_account_lines(self, data):
    #     lines = []
    #     account_report = self.env['account.financial.report'].search([('id', '=', data['account_report_id'][0])])
    #     child_reports = account_report._get_children_by_order()
    #     res = self._compute_report_balance(child_reports)
    #     for report in child_reports:
    #         type_report = 'head'
    #         if report.type == 'account_report':
    #             type_report = 'total'
    #         vals = {
    #             'report': report,
    #             'account_id': False,
    #             'name': report.name,
    #             'level': report.level,
    #             'balance': res[report.id]['balance'],
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
    #                     'name': account.code + ' ' + account.name,
    #                     'level': report.level + 1,
    #                     'balance': value['balance'],
    #                     'type': 'subline',
    #                 }
    #                 sub_lines.append(vals)
    #             lines += sorted(sub_lines, key=lambda sub_line: sub_line['name'])
                
    #             vals = {
    #                 'report': report,
    #                 'account_id': False,
    #                 'name': 'TOTAL ' + report.name,
    #                 'level': report.level,
    #                 'balance': res[report.id]['balance'],
    #                 'type': 'total',
    #             }
    #             lines.append(vals)
    #     return lines

    # @api.model
    # def _get_report_values(self, docids, data=None):
    #     active_model = self.env.context.get('active_model')
    #     docs = self.env[active_model].browse(self.env.context.get('active_id'))
    #     date_from = data['form']['date_from']
    #     date_to = data['form']['date_to']
    #     branchs = self.env['res.branch'].sudo().search([])
    #     account_lines = self.get_account_lines(data.get('form'))
    #     vals = {
    #         'docs': docs,
    #         'periode': data['periode'],
    #         'branchs': branchs,
    #         'account_lines': account_lines,
    #         'model': self,
    #         'date_from': date_from,
    #         'date_to': date_to,
    #     }
    #     # print(vals)
    #     return vals