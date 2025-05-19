# -*- coding: utf-8 -*-

import time
from odoo import api, models, _
from odoo.exceptions import UserError


class ReportLabaRugi(models.AbstractModel):
    _name = 'report.report_multi_branch.report_laba_rugi_mb'
    _description = 'Laba Rugi Multi Branch Report'


    def get_value_pusat(self, account_id, report):
        where = """where am.state = 'posted' and aml.branch_id is null"""
        if account_id:
            where += f""" and aa.id = {account_id}"""
        if report.type == 'accounts':
            where += f""" and aa.id in {str(tuple(report.account_ids.ids)).replace(',)',')')}"""
        if report.type == 'account_type':
            where += f""" and aa.account_type in {str(tuple(report.account_type_ids.mapped('type'))).replace(',)',')')}"""

        query = f"""
            select COALESCE(SUM(aml.debit), 0) - COALESCE(SUM(aml.credit), 0) as balance
            from account_move_line aml
            join account_move am on aml.move_id = am.id
            join account_account aa on aml.account_id = aa.id
            {where}
        """
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()[0]
        return result
    
    
    def get_value_multi_branch(self, account_id, report, branch_id):
        where = """where am.state = 'posted'"""
        if account_id:
            where += f""" and aa.id = {account_id}"""
        if branch_id:
            where += f""" and aml.branch_id = {branch_id}"""
        if report.type == 'accounts':
            where += f""" and aa.id in {str(tuple(report.account_ids.ids)).replace(',)',')')}"""
        if report.type == 'account_type':
            where += f""" and aa.account_type in {str(tuple(report.account_type_ids.mapped('type'))).replace(',)',')')}"""

        query = f"""
            select COALESCE(SUM(aml.debit), 0) - COALESCE(SUM(aml.credit), 0) as balance
            from account_move_line aml
            join account_move am on aml.move_id = am.id
            join account_account aa on aml.account_id = aa.id
            {where}
        """
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()[0]
        return result


    @api.model
    def _get_report_values(self, docids, data=None):
        # print(data)
        active_model = self.env.context.get('active_model')
        docs = self.env[active_model].browse(self.env.context.get('active_id'))
        account_report_id = data['form']['account_report_id'][0]
        date_from = data['form']['date_from']
        date_to = data['form']['date_to']
        
        # Get Branch
        branchs = []
        self.env.cr.execute("""
            select aml.branch_id from account_move_line aml
        """)
        ress = self.env.cr.dictfetchall()
        if ress:
            branch_ids = [row['branch_id'] for row in ress]
            branchs = self.env['res.branch'].search([('id', 'in', branch_ids)], order="seq_id asc")

        account_lines = []
        account_report = self.env['account.financial.report'].browse(account_report_id)
        child_reports = account_report._get_children_by_order()
        for report in child_reports:
            account_lines.append({
                'report': report,
                'account_id': False,
                'name': report.name,
                'level': report.level,
                'balance': 0,
                'type': 'head',
            })

            # Start Detail Account
            account_sub_lines = []

            where_query = f"""where am.state = 'posted'"""
            if date_from:
                where_query += f""" and aml.date >= '{date_from}'"""
            if date_to:
                where_query += f""" and aml.date <= '{date_to}'"""
            
            if report.type == 'accounts':
                where_query += f""" and aa.id in {str(tuple(report.account_ids.ids)).replace(',)',')')}"""
            elif report.type == 'account_type':
                where_query += f""" and aa.account_type in {str(tuple(report.account_type_ids.mapped('type'))).replace(',)',')')}"""
            elif report.type == 'account_report' and report.account_report_id:
                continue
            elif report.type == 'sum':
                continue


            self.env.cr.execute(f"""
                select aa.id as account_id
                    , aa.code as account_code
                    , aa.name as account_name
                    , COALESCE(SUM(aml.debit), 0) - COALESCE(SUM(aml.credit), 0) as balance
                from account_move_line aml
                join account_move am on aml.move_id = am.id
                join account_account aa on aml.account_id = aa.id
                {where_query}
                group by 1,2,3
            """)
            for row in self.env.cr.dictfetchall():
                account_name_value = list(row['account_name'].values())[0]
                account_sub_lines.append({
                    'report': report,
                    'account_id': row['account_id'],
                    'name': row['account_code'] + ' ' + account_name_value,
                    'level': report.level + 1,
                    'balance': row['balance'],
                    'type': 'subline',
                })
            account_lines += sorted(account_sub_lines, key=lambda account_sub_lines: account_sub_lines['name'])

            # PENAMBAHAN TOTAL
            total_balance = 0
            for line in account_lines:
                total_balance += line['balance']

            vals = {
                'report': report,
                'account_id': False,
                'name': 'TOTAL' + ' ' + report.name,
                'level': report.level + 1,
                'balance': total_balance,
                'type': 'total',
            }
            print(vals)
            account_lines.append(vals)
        # print(account_lines)
        
        
        vals = {
            'docs': docs,
            'periode': data['periode'],
            'branchs': branchs,
            'account_lines': account_lines,
            'model': self,
        }
        return vals