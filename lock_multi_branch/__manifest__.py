{
    'name': "Lock Journal Multi Branch",
    'summary': """Lock Journal Per Branch""",
    'description': """Lock Journal Per Branch""",
    'author': 'Ahmad Rizki Rhomadoni',
    'category': 'Extra Rights',
    'version': "16.0.1.0.0",
    'license': 'AGPL-3',
    'depends': [
        'base',
        'account',
        'om_fiscal_year',
        'base_multi_branch',
    ],
    'data': [
        'views/res_branch.xml',
        'wizard/change_lock_date.xml',
    ],
}