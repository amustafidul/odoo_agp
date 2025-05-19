from odoo import models, fields, tools
import logging

_logger = logging.getLogger(__name__)


class EmployeeUnitPayroll(models.Model):
    _name = 'employee.unit.payroll'
    _description = 'Master Unit Penempatan'
    _auto = False

    id = fields.Integer()
    name = fields.Char(string='Unit Penempatan', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute(f"""  
            CREATE OR REPLACE VIEW employee_unit_payroll AS (  
                SELECT      
                    unit.id AS id,     
                    unit.name AS name  
                FROM      
                    res_branch unit
            )  
        """)