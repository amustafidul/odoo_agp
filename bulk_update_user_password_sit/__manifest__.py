# -*- coding: utf-8 -*-

{
    'name': u' Bulk Password Update',
    'version': "16.0.1.0.0",
    'category': '',
    'summary': """ simplify and expedite the process of changing passwords for multiple users simultaneously """,
    'description': """Bulk Password Update""",
    'website': 'https://silentinfotech.com',
    "price": 0.00,
    "currency": "USD",
    'author': 'Silent Infotech Pvt. Ltd.',
    'depends': ['base'],
    'data': [
        'views/bulk_password_user.xml',
        'security/ir.model.access.csv',

    ],
    'qweb': [

    ],

    'application': True,
    'license': u'OPL-1',
    'auto_install': False,
    'installable': True,
    "images": ['static/description/banner.gif'],
    'assets': {
        'web.assets_backend': [
            'bulk_update_user_password_sit/static/src/js/systray.js',
            'bulk_update_user_password_sit/static/src/xml/systray.xml',
        ]
    }

}
