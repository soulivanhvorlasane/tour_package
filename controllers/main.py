from odoo import http
from odoo.http import request

class TourPackageController(http.Controller):

    @http.route(['/packages'], type='http', auth='public', website=True)
    def packages_page(self, **kwargs):
        packages = request.env['tour.package'].sudo().search([], limit=3)
        return request.render('tour_package.website_packages', {
            'packages': packages
        })

    @http.route(['/packages/<int:package_id>/book'], type='http', auth='public', website=True)
    def tour_detail(self, package_id, **kw):
        package = request.env['tour.package'].sudo().browse(package_id)
        calendars = request.env['tour.calendar'].sudo().search([
            ('package_id', '=', package.id),
            ('state', '=', 'open')
        ], order='date_start asc')
        return request.render('tour_package.tour_detail', {
            'package': package,
            'calendars': calendars,
        })

    @http.route(['/packages/book/confirm'], type='http', auth="user", website=True, methods=['POST'])
    def tour_book(self, **post):
        calendar_id = int(post.get('calendar_id'))
        seats = int(post.get('seats', 1))
        
        calendar = request.env['tour.calendar'].sudo().browse(calendar_id)
        if not calendar.exists() or calendar.state != 'open' or calendar.remaining_seats < seats:
            return request.redirect(f'/packages/{calendar.package_id.id}/book?error=unavailable')

        booking = request.env['tour.booking'].sudo().create({
            'calendar_id': calendar.id,
            'partner_id': request.env.user.partner_id.id,
            'user_id': request.env.user.id,
            'seats': seats,
        })
        
        return request.redirect(f'/my/bookings/{booking.id}')

class CustomerPortal(http.Controller):

    @http.route(['/my/bookings'], type='http', auth="user", website=True)
    def portal_my_bookings(self, **kw):
        bookings = request.env['tour.booking'].sudo().search([('user_id', '=', request.env.user.id)])
        return request.render('tour_package.portal_my_bookings', {
            'bookings': bookings,
            'page_name': 'booking',
        })

    @http.route(['/my/bookings/<model("tour.booking"):booking>'], type='http', auth="user", website=True)
    def portal_my_booking_detail(self, booking, **kw):
        if booking.user_id != request.env.user:
            return request.redirect('/my/bookings')
        return request.render('tour_package.portal_booking_detail', {
            'booking': booking,
            'page_name': 'booking',
        })
