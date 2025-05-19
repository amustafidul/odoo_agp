{
    'name': 'Dinas Management',
    'version': '16.0.0.1.2',
    'category': 'Human Resources',
    'summary': 'Custom module for managing Dinas',
    'description': 'A module to manage Dinas Assignment',
    'depends': [
        'hr_holidays',
        'hr',
        'agp_employee_ib',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'data/sppd_cron.xml',
        'report/report_nota_dinas_template.xml',
        'report/report_sppd_template.xml',
        'wizard/hr_leave_dinas_modify_wizard_view.xml',
        'wizard/nota_dinas_disposisi_wizard_view.xml',
        'views/hr_dinas_biaya_view.xml',
        'views/penugasan_dinas_view.xml',
        'views/nota_dinas_view.xml',
        'views/hr_department_view.xml',
        'views/menuitem.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'agp_dinas_ib/static/src/css/styles.css',
            'agp_dinas_ib/static/src/js/sppd_bus_handler.js',
        ],
    },
    'installable': True,
    'application': True,
    'icon': '/agp_dinas_ib/static/description/icon_dinas.png',
}