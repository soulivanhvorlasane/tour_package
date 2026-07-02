{
    'name': 'Tour Package Management',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Manage Tour Packages, Availabilities and Bookings',
    'description': """
        Tour Package Management System:
        - Admin can create and manage tour packages.
        - Admin can define availability via calendar entries.
        - Users can browse and book available packages.
        - Booking portal for users.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'mail', 'website', 'portal'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'views/tour_package_views.xml',
        'views/tour_calendar_views.xml',
        'views/tour_booking_views.xml',
        'views/menu_views.xml',
        'views/portal_templates.xml',
        'reports/booking_report_views.xml',
        'reports/booking_report_templates.xml',
    ],
    'demo': [
        'data/demo.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
