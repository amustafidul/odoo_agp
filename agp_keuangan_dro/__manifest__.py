# -*- coding: utf-8 -*-
{
    'name': "agp_keuangan_dro",

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
        'agp_approval_workflow_extended',
        # 'agp_employee_ib'
    ],

    'data': [
        # Preset group records
        'data/groups_data.xml',
        
        # Record rules
        'security/ir.model.access.csv',
        'security/rule_anggaran.xml',
        'security/rule_nodin.xml',
        'security/rule_rkap.xml',

        # Preset records
        'data/document_setting_kkhc.xml',
        'data/nodin_bod_data.xml',
        'data/scheduler_data.xml',
        'data/jabatan_data.xml',

        # View base (search, tree, form)
        'views/search_views.xml',
        'views/partner_bank_views.xml',
        'views/kkhc_super_views.xml',
        'wizard/kkhc_line_wizard_views.xml',
        'views/monitorings.xml',
        'wizard/reject_argument.xml',
        'wizard/bayar.xml',
        'views/nodin_bod_views.xml',
        'views/monitoring_kkhc_views.xml',
        'views/kkhc_views.xml',
        'views/kode_masalah_views.xml',
        'views/rkap_views.xml',
        'views/nodin_views.xml',
        'views/kkhc_rejected_views.xml',

        # Templates (qweb)
        'views/templates.xml',

        # Actions & Menus
        'views/actions.xml',
        'views/menuitems.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'agp_keuangan_dro/static/src/css/custom_style.css',
            'agp_keuangan_dro/static/src/js/many2many_tags_custom.js',
        ],
    },

}
