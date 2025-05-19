from odoo import models, fields, tools
import logging

_logger = logging.getLogger(__name__)


class EmployeePosition(models.Model):
    _name = 'employee.position.payroll'
    _description = 'Employee Position'
    _auto = False

    id = fields.Integer()
    name = fields.Char(string='Jabatan', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute(f"""  
            CREATE OR REPLACE VIEW employee_position_payroll AS (  
                SELECT DISTINCT id, name  
                FROM (  
                    SELECT      
                        ket_jab.id + 100000 AS id,     
                        ket_jab.name AS name  
                    FROM      
                        hr_employee_keterangan_jabatan ket_jab     

                    UNION   

                    SELECT      
                        fp.id + 200000 AS id,    
                        fp.name AS name  
                    FROM      
                        hr_employee_fungsi_penugasan fp  
                ) AS combined  
            )  
        """)