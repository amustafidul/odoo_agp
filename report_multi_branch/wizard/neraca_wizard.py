from odoo import fields, api, models, _
from odoo.exceptions import UserError
import ast

class NeracaWizard(models.Model):
    _name = "neraca.mb.wizard"
    _description = "Neraca Wizard"
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    financial_param_id = fields.Many2one('financial.param', string='Financial Param')
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    
    def check_report_neraca(self):
        data = {
            'form': self.read(['company_id', 'financial_param_id', 'date_from', 'date_to'])[0],
            'periode': f"{self.date_to.strftime('%m')} - {self.date_to.strftime('%Y')}",
            'branchs': self.get_list_branch(),
        }
        
        account_lines = self.compute_formula_optimized(self.date_from, self.date_to)
        data['account_lines'] = account_lines
        
        return self.env.ref('report_multi_branch.action_report_neraca_mb').with_context(
            discard_logo_check=True,
            must_skip_sentry=True
        ).report_action(self, data=data)
    
    def check_report_xls_neraca(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/neraca/export/%s' % (self.id),
            'target': 'new',
        }

    def get_list_branch(self):
        company_ids = str(tuple(self.env.company.ids)).replace(',)',')')
        self.env.cr.execute(f"""select id, name from res_branch where company_id in {company_ids} order by seq_id""")
        return self.env.cr.dictfetchall()

    def compute_formula_optimized(self, date_from, date_to):
        """Optimized version that maintains correct data structure for template"""
        # Get all needed data in efficient queries
        all_lines = self.financial_param_id.sub_param_ids.filtered(lambda x: not x.invisible)
        account_ids = list(set(
            account.id 
            for line in all_lines.filtered(lambda x: x.type == 'account') 
            for account in line.account_ids
        ))
        branch_ids = [branch['id'] for branch in self.get_list_branch()]
        
        # Precompute balances
        balances_cache = self._precompute_balances(date_from, date_to, account_ids, branch_ids)
        
        account_lines = []
        for line in all_lines:
            if not line.type:
                # Create empty line structure with correct format
                account_lines.append({
                    'name': line.name,
                    'balance': 0.0,
                    'branch_list_vals': [0.0 for _ in branch_ids],  # List of numbers, not dicts
                    'type': line.type,
                    'level': line.level,
                    'bold': line.bold,
                    'blank': line.blank,
                })
                continue
                
            if line.type == 'account':
                for account in line.account_ids:
                    balance = balances_cache['global'].get(account.id, 0.0)
                    if self._should_reverse_balance(account):
                        balance = -balance
                    
                    # Create list of branch balances (NUMERIC VALUES, not dicts)
                    branch_balances = [
                        -balances_cache['branch'].get((account.id, branch_id), 0.0)
                        if self._should_reverse_balance(account)
                        else balances_cache['branch'].get((account.id, branch_id), 0.0)
                        for branch_id in branch_ids
                    ]
                    
                    account_lines.append({
                        'name': f"{account.code} {account.name}",
                        'balance': balance,
                        'branch_list_vals': branch_balances,  # Direct numeric values
                        'type': line.type,
                        'level': line.level,
                        'bold': line.bold,
                        'blank': line.blank,
                    })
                    
            elif line.type == 'formula':
                # Global balance calculation
                params = {}
                for param_line in all_lines.filtered(lambda x: x.type == 'account'):
                    account_ids = param_line.account_ids.ids
                    total = sum(balances_cache['global'].get(acc_id, 0.0) for acc_id in account_ids)
                    params[param_line.code] = total or 0.0
                    
                self._compute_formula_optimized(line, params)
                balance = params[line.code]
                
                # Branch balance calculation - produces list of NUMERIC VALUES
                branch_balances = []
                for branch_id in branch_ids:
                    branch_params = {}
                    for param_line in all_lines.filtered(lambda x: x.type == 'account'):
                        account_ids = param_line.account_ids.ids
                        branch_total = sum(
                            balances_cache['branch'].get((acc_id, branch_id), 0.0) 
                            for acc_id in account_ids
                        )
                        branch_params[param_line.code] = branch_total or 0.0
                        
                    self._compute_formula_optimized(line, branch_params)
                    branch_balances.append(branch_params[line.code])  # Just the numeric value
                
                account_lines.append({
                    'name': line.name,
                    'balance': balance,
                    'branch_list_vals': branch_balances,  # Direct numeric values
                    'type': line.type,
                    'level': line.level,
                    'bold': line.bold,
                    'blank': line.blank,
                })
        
        return account_lines
        
    def _precompute_balances(self, date_from, date_to, account_ids, branch_ids):
        """Efficiently precompute all needed balances"""
        balances_cache = {'global': {}, 'branch': {}}
        
        if not account_ids:
            return balances_cache
            
        # Global balances
        query = """
            SELECT account_id, COALESCE(SUM(balance), 0) as balance
            FROM account_move_line
            WHERE parent_state = 'posted'
              AND account_id IN %s
              AND date >= %s AND date <= %s
            GROUP BY account_id
        """
        self.env.cr.execute(query, (tuple(account_ids), date_from, date_to))
        balances_cache['global'] = {r['account_id']: r['balance'] for r in self.env.cr.dictfetchall()}
        
        # Branch balances
        query = """
            SELECT account_id, branch_id, COALESCE(SUM(balance), 0) as balance
            FROM account_move_line
            WHERE parent_state = 'posted'
              AND account_id IN %s
              AND branch_id IN %s
              AND date >= %s AND date <= %s
            GROUP BY account_id, branch_id
        """
        self.env.cr.execute(query, (
            tuple(account_ids), 
            tuple(branch_ids), 
            date_from, 
            date_to
        ))
        balances_cache['branch'] = {
            (r['account_id'], r['branch_id']): r['balance'] 
            for r in self.env.cr.dictfetchall()
        }
        
        return balances_cache

    def _compute_formula_optimized(self, line, params):
        """Compute formula values with error handling"""
        if line.code in params:
            return params[line.code]
            
        try:
            # Parse the formula and ensure all dependencies are computed
            parse_code = ast.parse(line.formula)
            for node in ast.walk(parse_code):
                if isinstance(node, ast.Name):
                    sub_code = node.id
                    if sub_code != line.code and sub_code not in params:
                        sub_line = self.env['financial.param.line'].search([
                            ('param_id', '=', self.financial_param_id.id),
                            ('code', '=', sub_code)
                        ], limit=1)
                        if sub_line:
                            self._compute_formula_optimized(sub_line, params)
            
            params[line.code] = eval(line.formula, {'__builtins__': None}, params)
        except Exception as e:
            raise UserError(_('Error in formula for %s: %s') % (line.code, str(e)))
        
        return params[line.code]

    def _create_line_structure(self, line, balance, branch_list_vals, account_name=None):
        """Maintain the exact structure expected by the template"""
        return {
            'name': account_name if account_name else line.name,
            'balance': balance,
            'branch_list_vals': branch_list_vals,  # Keep as list of dicts
            'type': line.type,
            'level': line.level,
            'bold': line.bold,
            'blank': line.blank,
        }

    def _should_reverse_balance(self, account):
        """Determine if balance should be reversed for this account"""
        if account.code and (
            ('1107201' <= account.code <= '1107207') or 
            ('1202101' <= account.code <= '1202106') or 
            ('1205101' <= account.code <= '1205103') or 
            ('9112100' <= account.code <= '9200000')
        ):
            return True
        return account.account_type in [
            'liability_payable', 
            'liability_current', 
            'liability_non_current', 
            'equity'
        ]



# class NeracaWizard(models.Model):
#     _name = "neraca.mb.wizard"
#     _description = "Neraca Wizard"
    
#     company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
#     financial_param_id = fields.Many2one('financial.param', string='Financial Param')
#     date_from = fields.Date(string='Date From')
#     date_to = fields.Date(string='Date To')
    
    
#     def check_report_neraca(self):
#         data = {}
#         data['form'] = self.read()[0]
#         data['periode'] = f"""{self.date_to.strftime('%m')} - {self.date_to.strftime('%Y')}"""

#         branchs = self.get_list_branch()
#         data['branchs'] = branchs
        
#         account_lines = self.compute_formula(self.date_from, self.date_to)
#         data['account_lines'] = account_lines
        
#         return self.env.ref('report_multi_branch.action_report_neraca_mb').report_action(self, data=data)
    
    
#     def check_report_xls_neraca(self):
#         return {
#             'type': 'ir.actions.act_url',
#             'url': '/neraca/export/%s' % (self.id),
#             'target': 'new',
#         }


#     def get_list_branch(self):
#         company_ids = str(tuple(self.env.company.ids)).replace(',)',')')
#         self.env.cr.execute(f"""SELECT id, name FROM res_branch WHERE company_id IN {company_ids} ORDER BY seq_id""")
#         result = self.env.cr.dictfetchall()
#         return result



#     def compute_formula(self, date_from, date_to):
#         def get_balance(account_id=False, branch_id=False, date_from=False, date_to=False):
#             where_query = "WHERE parent_state = 'posted' "
#             if date_from:
#                 where_query += f"AND date >= '{date_from}' "
#             if date_to:
#                 where_query += f"AND date <= '{date_to}' "
#             if account_id:
#                 where_query += f"AND account_id = {account_id} "
#             if branch_id:
#                 where_query += f"AND branch_id = {branch_id} "
#             self.env.cr.execute(f"""
#                 SELECT
#                     COALESCE(SUM(balance), 0) AS balance
#                 FROM
#                     account_move_line
#                 {where_query}
#             """)
#             result = self.env.cr.dictfetchone()
#             return result['balance']
        


#         def get_balance_multi_account(account_ids=False, branch_id=False, date_from=False, date_to=False):
#             if account_ids:
#                 account_ids = str(tuple(account_ids.ids)).replace(',)',')')
#                 where_query = f"WHERE parent_state = 'posted' AND account_id in {account_ids} "
#                 if date_from:
#                     where_query += f"AND date >= '{date_from}' "
#                 if date_to:
#                     where_query += f"AND date <= '{date_to}' "
#                 if branch_id:
#                     where_query += f"AND branch_id = {branch_id} "
#                 self.env.cr.execute(f"""
#                     SELECT
#                         COALESCE(SUM(balance), 0) AS balance
#                     FROM account_move_line
#                         {where_query}
#                 """)
#                 result = self.env.cr.dictfetchone()
#                 return result



#         def get_balance_formula(financial_param, code, params, parent_code=None):
#             if code in params:
#                 return params[code]  # Return the value if it's already computed
        
#             line = self.env['financial.param.line'].sudo().search([
#                 ('param_id', '=', financial_param.id),
#                 ('code', '=', code)
#             ])
#             if not line:
#                 raise UserError(_('Parameter dengan kode %s error (kode: %s tidak ditemukan)' % (parent_code, code)))
            
#             if line.type == 'formula':
#                 formula = line.formula
#                 if formula:
#                     parse_code = ast.parse(formula)
#                     for node in ast.walk(parse_code):
#                         if isinstance(node, ast.Name):
#                             sub_code = node.id
#                             if sub_code != code:  # Avoid infinite recursion for circular dependencies
#                                 balance = get_balance_formula(financial_param, sub_code, params, line.code)
#                                 params[sub_code] = balance  # Update params with computed value
                    
#                     locals().update(params)
#                     try:
#                         params[code] = eval(formula)
#                     except Exception as e:
#                         raise UserError(_('Parameter dengan kode %s error: %s' % (line.code, e)))
                    
#                     return params[code]
        
        
        
#         account_lines = []
#         for line in self.financial_param_id.sub_param_ids.filtered(lambda x:not x.invisible):
#             if not line.type:
#                 account_lines.append({
#                     'name': line.name,
#                     'balance': 0.0,
#                     'branch_list_vals': [],
#                     'type': line.type,
#                     'level': line.level,
#                     'bold': line.bold,
#                     'blank': line.blank,
#                 })
#             if line.type == 'account':
#                 for account in line.account_ids:
#                     balance = get_balance(account_id=account.id, date_from=date_from, date_to=date_to)
                    
#                     if account.code and (('1107201' <= account.code <= '1107207') or ('1202101' <= account.code <= '1202106') or ('1205101' <= account.code <= '1205103') or ('9112100'<= account.code <= '9200000')) or account.account_type in ['liability_payable', 'liability_current', 'liability_non_current', 'equity']:
#                         balance = -balance  # Membalik nilai, negatif menjadi positif, positif menjadi negatif

#                     branch_list_vals = []
#                     branchs = self.get_list_branch()
#                     for branch in branchs:
#                         branch_balance = get_balance(account_id=account.id, branch_id=branch['id'], date_from=date_from, date_to=date_to)
                        
#                         if account.code and (('1107201' <= account.code <= '1107207') or ('1202101' <= account.code <= '1202106') or ('1205101' <= account.code <= '1205103') or ('9112100'<= account.code <= '9200000')) or account.account_type in ['liability_payable', 'liability_current', 'liability_non_current', 'equity']:
#                             branch_balance = -branch_balance  # Membalik nilai, negatif menjadi positif, positif menjadi negatif

#                         branch_list_vals.append({'balance': branch_balance})        
                    
#                     account_lines.append({
#                         'name': account.code + ' ' + account.name,
#                         'balance': balance,
#                         'branch_list_vals': branch_list_vals,
#                         'type': line.type,
#                         'level': line.level,
#                         'bold': line.bold,
#                         'blank': line.blank,
#                     })
#             if line.type == 'formula':
#                 params = {}
#                 for param_line in self.financial_param_id.sub_param_ids.filtered(lambda x:x.type == 'account' and not x.invisible):
#                     multi_account_balance = get_balance_multi_account(account_ids=param_line.account_ids, date_from=date_from, date_to=date_to)
#                     if not multi_account_balance:
#                         raise UserError(f'Account pada parameter {param_line.name} kosong. Mohon di isi')
#                     params[param_line.code] = multi_account_balance['balance']
#                 get_balance_formula(self.financial_param_id, line.code, params)
#                 balance = params[line.code]

#                 branch_list_vals = []
#                 branchs = self.get_list_branch()
#                 for branch in branchs:
#                     branch_params = {}
#                     for param_line in self.financial_param_id.sub_param_ids.filtered(lambda x:x.type == 'account' and not x.invisible):
#                         branch_multi_account_balance = get_balance_multi_account(account_ids=param_line.account_ids, branch_id=branch['id'], date_from=date_from, date_to=date_to)
#                         if not branch_multi_account_balance:
#                             raise UserError(f'Account pada parameter {param_line.name} kosong. Mohon di isi')
#                         branch_params[param_line.code] = branch_multi_account_balance['balance']
#                     get_balance_formula(self.financial_param_id, line.code, branch_params)
#                     branch_balance = branch_params[line.code]
#                     branch_list_vals.append({'balance': branch_balance})
                
#                 account_lines.append({
#                     'name': line.name,
#                     'balance': balance,
#                     'branch_list_vals': branch_list_vals,
#                     'type': line.type,
#                     'level': line.level,
#                     'bold': line.bold,
#                     'blank': line.blank,
#                 })
#         return account_lines