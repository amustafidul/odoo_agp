from odoo import models, fields, api, _


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    employee_type = fields.Selection(
        selection_add=[
            ('tad', 'TAD'),
            ('pkwt', 'PKWT'),
            ('organik', 'Organik'),
            ('direksi', 'Direksi'),
            ('jajaran_dekom', 'Dekom & Perangkat Dekom'),
            ('konsultan_individu', 'Konsultan Individu'),
        ],
        ondelete={'tad': lambda sor: sor.write({'employee_type': 'employee'}),
                  'pkwt': lambda sor: sor.write({'employee_type': 'employee'}),
                  'organik': lambda sor: sor.write({'employee_type': 'employee'}),
                  'direksi': lambda sor: sor.write({'employee_type': 'employee'}),
                  'jajaran_dekom': lambda sor: sor.write({'employee_type': 'employee'}),
                  'konsultan_individu': lambda sor: sor.write({'employee_type': 'employee'})
                  }
    )