{
    'name': 'AGP HR Resignation',
    'version': '16.0.0.0.2',
    'category': 'Human Resources',
    'summary': 'HR Resignation',
    'description': 'HR Resignation',
    'depends': [
        'web',
        'base',
        'base_multi_branch',
        'hr',
        'agp_employee_ib',
        'hr_resignation',
    ],
    'data': [
        'views/hr_employee_view.xml'
    ],
    'installable': True,
    'application': True,
}