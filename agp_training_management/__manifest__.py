{
    'name': 'AGP Training Management',
    'version': '16.0.1.0.0',
    'category': 'Human Resources/Training',
    'summary': 'Manajemen Training Kebutuhan (TNA), Pelaksanaan, dan Evaluasi Pelatihan Karyawan.',
    'description': """
        Modul komprehensif untuk pengelolaan seluruh siklus pelatihan karyawan:
        - Training Need Analysis (TNA) berdasarkan usulan dari departemen/cabang.
        - Alur persetujuan kebutuhan training oleh SDM Pusat.
        - Pencatatan dan pelacakan realisasi pelaksanaan training.
        - Evaluasi pasca-training dengan dukungan fuzzy logic.
        - Pencatatan histori training per karyawan.
    """,
    'author': 'Ibad - Safepedia',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'hr',
        'mail',
        'base_multi_branch',
        'report_xlsx',
        'agp_employee_ib',
        'hr_contract',
        'hr_contract_types',
    ],
    'data': [
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'security/training_management_groups.xml',
        'security/training_management_security_rules.xml',
        'security/ir.model.access.csv',
        'report/tna_report_actions.xml',
        'wizard/tna_rekap_report_wizard_views.xml',
        'views/tna_training_scope_views.xml',
        'views/tna_period_views.xml',
        'views/tna_submission_views.xml',
        'views/tna_proposed_training_views.xml',
        'views/hr_employee_completed_training_views.xml',
        'views/hr_employee_views.xml',
        'views/training_course_views.xml',
        'views/training_evaluation_view.xml',
        'views/training_management_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'agp_training_management/static/src/css/custom_styles.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}