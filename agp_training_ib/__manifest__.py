{
    'name': 'Training Management',
    'version': '16.0.0.2.7',
    'category': 'Human Resources',
    'summary': 'Module for managing training courses, sessions, and enrollments',
    'description': """
        Training Management Module
        ==========================
        This module helps in managing training courses, sessions, trainers, and participant enrollments.
        """,
    'author': 'Ahmad Mustafidul Ibad (amustafidul@gmail.com)',
    'depends': [
        'web',
        'base',
        'base_multi_branch',
        'agp_employee_ib',
        'hr',
        'hr_contract',
        'hr_contract_types'
    ],
    'data': [
        'data/ir_cron.xml',
        'security/ir.model.access.csv',
        'security/training_security.xml',
        'views/training_course_view.xml',
        'views/training_evaluation_view.xml',
        'views/training_menuitems.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'agp_training_ib/static/src/css/custom_styles.css',
        ],
    },
    'installable': True,
    'application': True,
    'icon': '/agp_training_ib/static/description/odoo_icon_training.png',
    'license': 'LGPL-3',
}