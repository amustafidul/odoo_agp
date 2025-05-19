from odoo import models, fields, tools
import logging

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    kategori_jabatan = fields.Selection([
        ('employee', 'Employee'),
        ('dirut', 'Dirut'),
        ('kadiv_keuangan', 'Kadiv Keuangan'),
    ])


class EmployeePosition(models.Model):
    _name = 'employee.position'
    _description = 'Employee Position'
    _auto = False

    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    name = fields.Char(string='Jabatan', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    kategori_jabatan = fields.Selection([
        ('employee', 'Employee'),
        ('dirut', 'Dirut'),
        ('kadiv_keuangan', 'Kadiv Keuangan'),
    ])

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW employee_position AS (
                SELECT
                    emp.id AS id,
                    emp.id AS employee_id,
                    CASE
                        WHEN emp.employment_type IN ('organik', 'pkwt') THEN COALESCE(kj.name, '-')
                        WHEN emp.employment_type = 'tad' THEN COALESCE(fp.name, '-')
                        ELSE '-'
                    END AS name,
                    emp.company_id AS company_id,
                    emp.kategori_jabatan AS kategori_jabatan
                FROM
                    hr_employee emp
                    LEFT JOIN hr_employee_keterangan_jabatan kj ON emp.keterangan_jabatan_id = kj.id
                    LEFT JOIN hr_employee_fungsi_penugasan fp ON emp.fungsi_penugasan_id = fp.id
                WHERE
                    emp.hr_employee_unit_id IS NOT NULL 
                    AND emp.keterangan_jabatan_id IS NOT NULL 
                    AND emp.company_id IS NOT NULL 
                    AND emp.employment_type IN ('organik', 'pkwt', 'tad')
            )
        """)