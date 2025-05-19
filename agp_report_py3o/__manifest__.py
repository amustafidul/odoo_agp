# -*- coding: utf-8 -*-
{
    'name': "agp_report_py3o",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "AGP",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'report_py3o', 'agp_keuangan_ib'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        # 'report/report_debit_note.xml',
        # 'report/report_kredit_note.xml',
        # 'report/invoice_new.xml',
        'report/kwitansi.xml',
        'report/invoice_emkl.xml',
        'report/invoice_grt.xml',
        'report/invoice_lumpsum.xml',
        'report/invoice_mt.xml',
        'report/invoice_jm.xml',
        'report/invoice_logistik.xml',
        'report/bongkar_muat.xml',
        'report/keagenan.xml',
        'report/dredging.xml',
        'report/sts.xml',
        'report/invoice_lainnya.xml',
        'report/permohonan_pembayaran.xml',
        'report/anggaran_harian.xml',

        'report/bank_garansi.xml',
        'report/sinking_fund.xml',
        'report/deposito.xml',
        'report/shl.xml',
        'report/np.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
