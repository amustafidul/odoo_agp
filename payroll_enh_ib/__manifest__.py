{
    'name': 'Payroll AGP (Enhancement)',
    'version': '16.0.0.0.2',
    'category': 'Payroll',
    'summary': 'Payroll management for AGP (Enhancement)',
    'description': """
        Payroll management for AGP (Enhancement)
        """,
    'author': 'Ibad (amustafidul@gmail.com)',
    'depends': [
        'web',
        'base',
        'base_multi_branch',
        'hr',
        'hr_contract',
        'hr_payroll_community',
        'report_xlsx',
        'agp_employee_ib'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_secure_wage.xml',
        'wizard/wizard_create_mass_payslip_view.xml',
        'views/master_nilai_kemahalan_view.xml',
        'views/tunjangan_jabatan_master_view.xml',
        'views/hr_contract_view.xml',
        # 'views/hr_payslip_view.xml',
        'views/menuitem.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'payroll_enh_ib/static/src/views/list/*.js',
            'payroll_enh_ib/static/src/views/list/*.xml',
        ],
    },
    'post_init_hook': 'migrate_existing_wage',
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}