from odoo import http
from odoo.http import request

class TourPackageController(http.Controller):

    @http.route(['/packages'], type='http', auth='public', website=True)
    def packages_page(self, **kwargs):
        packages = request.env['tour.package'].sudo().search([], limit=3)
        return request.render('tour_package.website_packages', {
            'packages': packages
        })

    @http.route('/tour', type='http', auth='public', website=True)
    def tour_packages(self, **kwargs):
        packages = request.env['tour.package'].sudo().search([])
        return request.render('tour_package.website_tour_packages', {
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

    @http.route(['/packages/book/confirm'], type='http', auth="public", website=True, methods=['POST', 'GET'])
    def tour_book(self, **post):
        # Handle GET requests (redirect back from login)
        if request.httprequest.method == 'GET':
            post = request.session.get('pending_tour_booking', {})
            if not post:
                return request.redirect('/packages')
            request.session.pop('pending_tour_booking', None)

        user = request.env.user
        
        # 1. If the user is not logged in
        if user._is_public():
            if post:
                request.session['pending_tour_booking'] = post
            return request.redirect('/web/login?redirect=/packages/book/confirm')
            
        # 2. If the user does not have a proper account
        if not user.has_group('base.group_portal') and not user.has_group('base.group_user'):
            return request.redirect('/web/signup?redirect=/packages/book/confirm')

        # 3. User is logged in -> Create Booking and proceed to Payment
        calendar_id = int(post.get('calendar_id', 0))
        seats = int(post.get('seats', 1))
        
        if not calendar_id:
            return request.redirect('/packages')
            
        calendar = request.env['tour.calendar'].sudo().browse(calendar_id)
        if not calendar.exists() or calendar.state != 'open' or calendar.remaining_seats < seats:
            return request.redirect(f'/packages/{calendar.package_id.id}/book?error=unavailable')

        booking = request.env['tour.booking'].sudo().create({
            'calendar_id': calendar.id,
            'partner_id': user.partner_id.id,
            'user_id': user.id,
            'seats': seats,
        })
        
        from odoo.addons.payment import utils as payment_utils
        access_token = payment_utils.generate_access_token(booking.partner_id.id, booking.total_price, request.env.company.currency_id.id)
        
        payment_url = f'/payment/pay?reference={booking.name}&amount={booking.total_price}&currency_id={request.env.company.currency_id.id}&partner_id={booking.partner_id.id}&access_token={access_token}'
        return request.redirect(payment_url)



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
