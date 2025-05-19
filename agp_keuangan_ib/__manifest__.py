# -*- coding: utf-8 -*-
{
    'name': "AGP Keuangan",
    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as"""
                  """ subtitle on modules listing or apps.openerp.com""",
    'description': """
        Long description of module's purpose
    """,
    'author': "Abhimantra - Ibad", # author
    'website': "https://abhimantra.co.id/", # website
    'category': 'Accounting/Keuangan', # category
    'version': '16.0.0.6', # version
    'depends': [
        'base',
        'base_setup',
        'mail',
        'account',
        'analytic',
        'portal',
        'digest',
        'base_multi_branch',
        'report_multi_branch',
        # 'agp_custom_fields',
        # 'agp_employee_ib',
        'web'
    ], # dependencies
    'data': [
        'security/ir.model.access.csv',
        # 'views/assets.xml',
        'views/account_move_view.xml',
        # 'data/data_group_div_anggaran.xml',
        'views/res_partner_bank.xml',
        'views/invoice.xml',
        'views/invoice_scf.xml',
        # 'views/scf.xml',
        'views/ajuan_anggaran.xml',
        'views/nota_dinas.xml',
        'views/asuransi.xml',
        'views/kkhc.xml',
        # 'views/kkhc_buttons.xml',
        'views/antrian_pembayaran.xml',
        # 'views/cash_in_out.xml',
        'views/kode_anggaran.xml',
        'views/deposito.xml',
        'views/bank_garansi.xml',
        'views/periode_produk.xml',
        'views/shareholder_loan.xml',
        'views/sinking_fund.xml',
        'views/national_pooling.xml',
        'views/rkap.xml',
        'views/persetujuan_anggaran.xml',
        'views/approval.xml',
        'views/tagihan.xml',
        'views/tagihan_rutin.xml',
        'views/saldo.xml',
        'views/tagihan_rutin_manual.xml',
        'views/anggaran_harian.xml',
        'views/permohonan_pembayaran.xml',
        'views/payment.xml',
        'views/transaction.xml',
        'views/surat_perjanjian.xml',
        'views/bank_harian.xml',
        'views/bank_harian_master.xml',
        'views/rekap_pelunasan.xml',
        # 'views/kkhc_super_views.xml',
        'views/bank_garansi_html.xml',
        'views/sinking_fund_html.xml',
        'views/deposito_html.xml',
        'views/shl_preview.xml',
        'views/np_preview.xml',
        'wizard/reject_argument.xml',
        # 'wizard/penagihan.xml',
        'wizard/cash_in_out.xml',
        'wizard/bank_garansi_export.xml',
        'wizard/sinking_fund_export.xml',
        'wizard/deposito_export.xml',
        'wizard/shareholder_loan_export.xml',
        'wizard/national_pooling_export.xml',
        # 'report/kkhc.xml',
        'report/proforma.xml',
        # 'report/invoice_general.xml',
        # 'report/invoice_lumpsum.xml',
        # 'report/invoice_bongkar_muat.xml',
        # 'report/invoice_jm.xml',
        # 'report/invoice_emkl.xml',
        # 'report/invoice_mt.xml',
        # 'report/invoice_grt.xml',
        # 'report/invoice_operasi_lainnya.xml',
        # 'report/invoice_logistik.xml',
        # 'report/invoice_keagenan.xml',
        # 'report/kwitansi.xml',
        'report/nota_dinas.xml',
        # 'report/permohonan_pembayaran.xml',
        'views/menuitem.xml'
    ], # data files
    'assets': {
        'web.assets_backend': [
            'agp_keuangan_ib/static/src/scss/account_keuangan_dashboard.scss',
            'agp_keuangan_ib/static/src/css/custom_style.css',
            'agp_keuangan_ib/static/src/js/disable_create.js',
            'agp_keuangan_ib/static/src/views/**/*.js',
            'agp_keuangan_ib/static/src/views/**/*.xml',
        ]
    },
    'installable': True, # installable
    'application': True, # application
    'license': 'LGPL-3', # license
}