# -*- coding: utf-8 -*-
{
    'name': "agp_approval_workflow_extended",

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
    'depends': [
        'base',
        'mail',
        'ami_approval_workflow_engine'
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/approval_workflow_views.xml',
        'views/res_users_views.xml',
        'views/filters.xml',
        'views/templates.xml',
    ],
}
