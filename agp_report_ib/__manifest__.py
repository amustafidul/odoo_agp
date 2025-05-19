{
    'name': 'AGP Reporting',
    'version': '16.0.0.0.2',
    'category': 'Reporting',
    'summary': 'Custom module for report',
    'description': 'Custom module for report',
    'depends': [
        'base',
        'report_xlsx',
        'base_multi_branch',
        'agp_hr_leave_lembur_ib',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/report_lembur_wizard_view.xml',
    ],
    'installable': True,
    'application': True,
    'icon': '/agp_report_ib/static/description/icon.png',
}