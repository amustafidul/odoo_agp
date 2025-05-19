# -*- coding: utf-8 -*-
{
    'name': "agp_report_extended",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Andromeda",
    'website': "https://andromedasupendi.pythonanywhere.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'agp_keuangan_ib',
        'agp_custom_fields',
        'agp_keuangan_dro'
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'report/ir_actions_report.xml',
        'report/non_invoice/report_rkap_konsolidasi.xml',

        'views/rkap.xml',
        'views/views.xml',
        'views/rkap_konsol_views.xml',
        'views/bank_harian_views.xml',
        'wizard/konsolidasi.xml',
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'agp_report_extended/static/src/js/button_report_konsolidasi.js',
            'agp_report_extended/static/src/xml/button_report_konsolidasi.xml',
            'agp_report_extended/static/src/js/custom_action_menus.js',
            'agp_report_extended/static/src/js/custom_action_menus_invoice.js',
        ],
    },
}