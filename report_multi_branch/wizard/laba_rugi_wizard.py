from odoo import fields, api, models, _
from odoo.exceptions import UserError

import ast


class LabaRugiWizard(models.Model):
    _name = "laba.rugi.mb.wizard"
    _description = "Laba Rugi Wizard"
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    financial_param_id = fields.Many2one('financial.param', string='Financial Param')
    report_type = fields.Selection([('pusat','Pusat dan Cabang'),('cabang','Cabang dan Sub Branch')], string='Type')
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')

    # @api.onchange('report_type')
    # def onchange_report_type(self):
    #     for rec in self:
    #         if rec.report_type:
    #             if rec.report_type == 'pusat':
    #                 rec.financial_param_id = self.env.ref('report_multi_branch.data_laba_rugi_financial_param')
    #             else:
    #                 rec.financial_param_id = self.env.ref('report_multi_branch.data_laba_rugi_cabang_financial_param')
    
    # Andro version
    def _get_list_branch(self):
        """Private method to get branch list more efficiently"""
        return self.env['res.branch'].search([
            ('company_id', 'in', self.env.company.ids)
        ], order='seq_id').read(['id', 'name'])
    
    # Andro version
    def check_report_laba_rugi_mb(self):
        # Prepare data dictionary more efficiently
        data = {
            'form': self.read(['company_id', 'financial_param_id', 'report_type', 'date_from', 'date_to'])[0],
            'periode': f"{self.date_to.strftime('%m')} - {self.date_to.strftime('%Y')}",
            'branchs': self._get_list_branch(),
            'account_lines': self.compute_formula(self.date_from, self.date_to)
        }

        # Determine report action based on report_type
        report_ref = 'report_multi_branch.action_report_laba_rugi_pusat_mb' \
            if self.report_type == 'pusat' else \
            'report_multi_branch.action_report_laba_rugi_cabang_mb'
            
        return self.env.ref(report_ref).report_action(self, data=data)
    
    def check_report_xls_laba_rugi_mb(self):
        if self.report_type == 'pusat':
            return {
                'type': 'ir.actions.act_url',
                'url': '/laba_rugi_pusat/export/%s' % (self.id),
                'target': 'new',
            }
        else:
            return {
                'type': 'ir.actions.act_url',
                'url': '/laba_rugi_cabang/export/%s' % (self.id),
                'target': 'new',
            }

    # Ahmad version
    # def check_report_laba_rugi_mb(self):
    #     data = {}
    #     data['form'] = self.read()[0]
    #     data['periode'] = f"""{self.date_to.strftime('%m')} - {self.date_to.strftime('%Y')}"""

    #     branchs = self.get_list_branch()
    #     data['branchs'] = branchs
        
    #     account_lines = self.compute_formula(self.date_from, self.date_to)
    #     data['account_lines'] = account_lines

    #     if self.report_type == 'pusat':
    #         return self.env.ref('report_multi_branch.action_report_laba_rugi_pusat_mb').report_action(self, data=data)
    #     else:
    #         return self.env.ref('report_multi_branch.action_report_laba_rugi_cabang_mb').report_action(self, data=data)

    # Ahmad version
    # def get_list_branch(self):
    #     company_ids = str(tuple(self.env.company.ids)).replace(',)',')')
    #     self.env.cr.execute(f"""select id, name from res_branch where company_id in {company_ids} order by seq_id""")
    #     result = self.env.cr.dictfetchall()
    #     return result

    def compute_formula(self, date_from, date_to):
        def get_balance(account_id=False, branch_id=False, date_from=False, date_to=False):
            where_query = "where parent_state = 'posted' "
            if date_from:
                where_query += f"and date >= '{date_from}' "
            if date_to:
                where_query += f"and date <= '{date_to}' "
            if account_id:
                where_query += f"and account_id = {account_id} "
            if branch_id:
                where_query += f"and branch_id = {branch_id} "
            self.env.cr.execute(f"""
            select COALESCE(SUM(balance), 0) as balance
            from account_move_line
            {where_query}
            """)
            result = self.env.cr.dictfetchone()
            return result['balance']
        


        def get_balance_multi_account(account_ids=False, branch_id=False, date_from=False, date_to=False):
            if account_ids:
                account_ids = str(tuple(account_ids.ids)).replace(',)',')')
                where_query = f"where parent_state = 'posted' and account_id in {account_ids} "
                if date_from:
                    where_query += f"and date >= '{date_from}' "
                if date_to:
                    where_query += f"and date <= '{date_to}' "
                if branch_id:
                    where_query += f"and branch_id = {branch_id} "
                self.env.cr.execute(f""" select COALESCE(SUM(balance), 0) as balance from account_move_line {where_query} """)
                result = self.env.cr.dictfetchone()
                return result



        def get_balance_formula(financial_param, code, params, parent_code=None):
            if code in params:
                return params[code]  # Return the value if it's already computed
        
            line = self.env['financial.param.line'].sudo().search([
                ('param_id', '=', financial_param.id),
                ('code', '=', code)
            ])
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
                                balance = get_balance_formula(financial_param, sub_code, params, line.code)
                                params[sub_code] = balance  # Update params with computed value
                    
                    locals().update(params)
                    try:
                        params[code] = eval(formula)
                    except Exception as e:
                        raise UserError(_('Parameter dengan kode %s error: %s' % (line.code, e)))
                    
                    return params[code]
        
        
        
        account_lines = []
        params = {}
        branch_params = {}
        for line in self.financial_param_id.sub_param_ids.filtered(lambda x:not x.invisible):
            if not line.type:
                account_lines.append({
                    'name': line.name,
                    'balance': 0.0,
                    'branch_list_vals': [],
                    'type': line.type,
                    'level': line.level,
                    'bold': line.bold,
                    'blank': line.blank,
                })
            if line.type == 'account':
                for account in line.account_ids:
                    balance = get_balance(account_id=account.id, date_from=date_from, date_to=date_to)
                    
                    if account.account_type in ['income', 'income_other']:
                        balance = abs(balance)
                   
                    branch_list_vals = []
                    branchs = self._get_list_branch()
                    for branch in branchs:
                        branch_balance = get_balance(account_id=account.id, branch_id=branch['id'], date_from=date_from, date_to=date_to)
                    
                        if account.account_type in ['income', 'income_other']:
                            branch_balance = abs(branch_balance)

                        branch_list_vals.append({'balance': branch_balance})
                        
                    account_lines.append({
                        'name': account.code + ' ' + account.name,
                        'balance': balance,
                        'branch_list_vals': branch_list_vals,
                        'type': line.type,
                        'level': line.level,
                        'bold': line.bold,
                        'blank': line.blank,
                    })
            if line.type == 'formula':
                params = {}
                for param_line in self.financial_param_id.sub_param_ids.filtered(lambda x:x.type == 'account' and not x.invisible):
                    multi_account_balance = get_balance_multi_account(account_ids=param_line.account_ids, date_from=date_from, date_to=date_to)
                    if not multi_account_balance:
                        raise UserError(f'Account pada parameter {param_line.name} kosong. Mohon di isi')
                    params[param_line.code] = multi_account_balance['balance']
                get_balance_formula(self.financial_param_id, line.code, params)
                balance = params[line.code]

                branch_list_vals = []
                branchs = self._get_list_branch()
                for branch in branchs:
                    branch_params = {}
                    for param_line in self.financial_param_id.sub_param_ids.filtered(lambda x:x.type == 'account' and not x.invisible):
                        branch_multi_account_balance = get_balance_multi_account(account_ids=param_line.account_ids, branch_id=branch['id'], date_from=date_from, date_to=date_to)
                        if not branch_multi_account_balance:
                            raise UserError(f'Account pada parameter {param_line.name} kosong. Mohon di isi')
                        branch_params[param_line.code] = branch_multi_account_balance['balance']
                    get_balance_formula(self.financial_param_id, line.code, branch_params)
                    branch_balance = branch_params[line.code]
                    branch_list_vals.append({'balance': branch_balance})
                
                account_lines.append({
                    'name': line.name,
                    'balance': balance,
                    'branch_list_vals': branch_list_vals,
                    'type': line.type,
                    'level': line.level,
                    'bold': line.bold,
                    'blank': line.blank,
                })
        return account_lines