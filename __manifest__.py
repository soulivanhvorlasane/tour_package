{
    'name': 'Tour Package Management',
    'version': '18.0.1.0.1',
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
    'depends': ['base', 'mail', 'website', 'portal', 'payment', 'account'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'data/mail_template_data.xml',
        'data/tour_package_category_data.xml',
        'views/tour_package_category_views.xml',
        'views/tour_package_views.xml',
        'views/tour_calendar_views.xml',
        'views/tour_booking_views.xml',
        'views/menu_views.xml',
        'views/portal_templates.xml',
        'views/website_templates.xml',
        'wizard/tour_booking_merge_wizard_views.xml',
        'wizard/tour_demo_wizard_views.xml',
        'reports/booking_report_views.xml',
        'reports/booking_report_templates.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
