{
    'name': 'Attendance Custom Modules',
    'version': '16.0.0.1.6',
    'category': 'Human Resources',
    'summary': 'Custom attendance modules',
    'description': """
        This module adds custom features for attendance in Odoo.
        Users can also generate attendance reports based on selected date ranges and employees, and download the report in Excel format.
    """,
    'author': 'Ibad - (amustafidul@gmail.com)',
    'depends': [
        'base',
        'report_xlsx',
        'hr_attendance',
        'hr_attendance_geolocation',
        'agp_dinas_ib'
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/hr_attendance_keterangan_wizard_view.xml',
        'view/hr_attendance_views.xml',
        'reports/attendance_absensi_report_view.xml',
        'reports/attendance_absensi_report_template.xml',
        'reports/attendance_absensi_report_action.xml',
    ],
    'installable': True,
    'application': False,
    'icon': '/agp_attendance_ib/static/description/icon.png',
    'license': 'LGPL-3',
}