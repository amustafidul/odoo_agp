{
    'name': 'Payroll AGP',
    'version': '16.0.0.0.6',
    'category': 'Payroll',
    'summary': 'Payroll management for AGP',
    'description': """
        Payroll management for AGP
        """,
    'author': 'Ibad (amustafidul@gmail.com)',
    'depends': [
        'web',
        'base',
        'base_multi_branch',
        'hr_payroll_community',
        'hr',
        'report_xlsx',
        'agp_employee_ib'
    ],
    'data': [
        'security/ir.model.access.csv',
        'report/printout_payslip.xml',
        'report/report_organik_pdf.xml',
        'report/report_pkwt_pdf.xml',
        'report/report_direksi_pdf.xml',
        'report/report_dekom_pdf.xml',
        'wizard/wizard_odoo_payroll.xml',
        'views/odoo_payroll_view_ib.xml',
        'views/menuitem.xml',
    ],
    'installable': True,
    'application': True,
    'icon': '/payroll_ib/static/description/odoo_payroll.png',
    'license': 'LGPL-3',
}