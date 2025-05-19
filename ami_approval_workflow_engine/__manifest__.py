{
    'name': 'Dynamic Approval Workflow',
    'version': '16.0.0.5.6',
    'summary': 'Module for Dynamic Approval Workflow with Sync to Target Models',
    'description': """
        This module allows users to create dynamic approval workflows and sync them to target models.
        It adds a tab with a tree view to the target model displaying the approval sequence and approvers.
    """,
    'author': 'Ahmad Mustafidul Ibad',
    'maintainer': 'amustafidul@gmail.com - Ibad',
    'category': 'Tools',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'hr',
        'agp_employee_ib'
        ],
    'data': [
        'security/approval_groups.xml',
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/approval_workflow_engine_view.xml',
        'views/menuitem.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ami_approval_workflow_engine/static/src/css/custom_styles.css',
        ],
    },
    'installable': True,
    'application': True,
    'icon': '/ami_approval_workflow_engine/static/description/icon.png',
    'auto_install': False,
}
