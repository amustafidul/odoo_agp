# -*- coding: utf-8 -*-
{
    'name': "AGP Custom Module",

    'summary': """
        Custom Module untuk penambahan Fields""",

    'description': """
        Custom Module untuk penambahan Fields
        - startworkperiod
        - finishworkperiod
    """,

    'author': "AGP",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base', 
        'account', 
        'stock', 
        'base_multi_branch', 
        # 'agp_keuangan_ib',
        'accounting_pdf_reports', 
        # 'hr',     
        'lock_multi_branch', 
        'om_fiscal_year',
        # 'report_multi_branch', 
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/account_access_rights.xml',
        'views/sub_branch.xml',
        'views/res_bank.xml',
        'views/res_users.xml',
        'views/account_move.xml',
        'views/account_payment.xml',
        'views/account_account.xml',
        'views/account_financial_report.xml',
        'views/account_tax.xml',
        'views/res_config_setting.xml',
        'views/hr_department.xml',        
        'views/jenis_kegiatan.xml',
        'views/lock_dates.xml',
        'views/account_rk_views.xml',
        # 'views/ir_sequence.xml',
        'views/product_template.xml',
        'views/tagihan_view.xml',
        'views/menu.xml',
        'wizard/account_payment_register.xml',
        # 'views/printout_debit.xml',
        # 'views/printout_credit.xml',
        
    ],
    'assets': {
        'web.assets_backend': [
            'agp_custom_fields/static/src/css/custom_style.css',
        ],
    },
    "application": True,
    "installable": True,
    "auto_install": False,
}
