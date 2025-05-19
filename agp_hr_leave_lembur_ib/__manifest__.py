{
    'name': 'Lembur Management',
    'version': '16.0.0.3.4',
    'category': 'Human Resources',
    'summary': 'Custom module for managing lembur',
    'description': 'A module to manage lembur by extending functionality from Time Off module',
    'depends': [
        'web',
        'base',
        'base_multi_branch',
        'hr_holidays',
        'agp_employee_ib',
        'agp_hr_leave_ib',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'data/lembur_data.xml',
        'wizard/lembur_reject_wizard_view.xml',
        'wizard/lembur_ask_for_revision_wizard_view.xml',
        'views/hr_leave_lembur_allocation_views.xml',
        'views/hr_leave_lembur_views.xml',
        'views/hr_leave_lembur_menuitem.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'agp_hr_leave_lembur_ib/static/src/js/calendar_date_restriction.js',
        ],
    },
    'installable': True,
    'application': True,
    'icon': '/agp_hr_leave_lembur_ib/static/description/icon_lembur.png',
}