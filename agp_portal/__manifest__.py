# -*- coding: utf-8 -*-
{
    'name': "agp_portal",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','agp_keuangan_ib','web'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/rkap_approvals_template.xml',
    ],
    'assets': {
        # "web.assets_backend": [
        #     "agp_portal/static/src/xml/action_print_template_inherit.xml",
        # ],
        'web.assets_frontend': [
            'agp_portal/static/src/css/materialize.min.css',
            'agp_portal/static/src/css/rkap_approvals_style.css',
            'agp_portal/static/src/js/materialize.min.js',
        ],
    },

}