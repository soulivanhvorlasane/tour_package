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

        from odoo.exceptions import ValidationError, RedirectWarning
        
        # Check for duplicates BEFORE creating to avoid database constraint exceptions
        duplicate = request.env['tour.booking'].sudo().search([
            ('package_id', '=', calendar.package_id.id),
            ('partner_id', '=', user.partner_id.id),
            ('calendar_id', '=', calendar.id),
            ('state', '!=', 'cancelled')
        ], limit=1)
        if duplicate:
            return request.redirect(f'/packages/{calendar.package_id.id}/book?error=duplicate')

        request.session['pending_payment'] = {
            'calendar_id': calendar.id,
            'seats': seats,
        }
        return request.redirect('/packages/book/payment')

    @http.route(['/packages/book/merge_seats'], type='http', auth="user", website=True, methods=['POST'])
    def tour_merge_seats(self, **post):
        calendar_id = int(post.get('calendar_id', 0))
        seats = int(post.get('seats', 1))
        
        if not calendar_id:
            return request.redirect('/packages')
            
        calendar = request.env['tour.calendar'].sudo().browse(calendar_id)
        if not calendar.exists() or calendar.state != 'open' or calendar.remaining_seats < seats:
            return request.redirect(f'/packages/{calendar.package_id.id}/book?error=unavailable')
            
        user = request.env.user
        existing_booking = request.env['tour.booking'].sudo().search([
            ('package_id', '=', calendar.package_id.id),
            ('partner_id', '=', user.partner_id.id),
            ('calendar_id', '=', calendar.id),
            ('state', '!=', 'cancelled')
        ], limit=1)
        
        if existing_booking:
            request.session['pending_payment'] = {
                'calendar_id': calendar.id,
                'seats': seats,
                'existing_booking_id': existing_booking.id
            }
            return request.redirect('/packages/book/payment')
            
        # Fallback if no existing booking found
        return request.redirect(f'/packages/{calendar.package_id.id}/book?error=validation')

    @http.route(['/packages/book/check_duplicate'], type='http', auth="user", website=True, csrf=False, methods=['POST'])
    def check_duplicate_booking(self, calendar_id=None, **kw):
        import json
        if not calendar_id:
            try:
                data = json.loads(request.httprequest.data)
                calendar_id = data.get('params', {}).get('calendar_id')
            except:
                pass
                
        if not calendar_id:
            return request.make_response(json.dumps({'result': {'is_duplicate': False}}), headers=[('Content-Type', 'application/json')])

        calendar = request.env['tour.calendar'].sudo().browse(int(calendar_id))
        user = request.env.user
        duplicate = request.env['tour.booking'].sudo().search([
            ('package_id', '=', calendar.package_id.id),
            ('partner_id', '=', user.partner_id.id),
            ('calendar_id', '=', calendar.id),
            ('state', '!=', 'cancelled')
        ], limit=1)
        
        response_data = {
            "jsonrpc": "2.0",
            "id": None,
            "result": {
                "is_duplicate": bool(duplicate)
            }
        }
        return request.make_response(json.dumps(response_data), headers=[('Content-Type', 'application/json')])

    @http.route(['/packages/book/payment'], type='http', auth="user", website=True)
    def booking_payment_page(self, **kw):
        pending = request.session.get('pending_payment')
        if not pending:
            return request.redirect('/packages')
            
        calendar = request.env['tour.calendar'].sudo().browse(pending['calendar_id'])
        if not calendar.exists():
            return request.redirect('/packages')
            
        seats = pending['seats']
        total_price = seats * (calendar.package_id.price or 0.0)
        
        return request.render('tour_package.booking_payment_page', {
            'calendar': calendar,
            'seats': seats,
            'total_price': total_price,
            'existing_booking_id': pending.get('existing_booking_id'),
        })

    @http.route(['/packages/book/payment/submit'], type='http', auth="user", website=True, methods=['POST'])
    def booking_payment_submit(self, **post):
        pending = request.session.get('pending_payment')
        if not pending:
            return request.redirect('/packages')
            
        calendar = request.env['tour.calendar'].sudo().browse(pending['calendar_id'])
        seats = pending['seats']
        existing_booking_id = pending.get('existing_booking_id')
        user = request.env.user
        
        # Check duplicate one last time if not merging
        if not existing_booking_id:
            duplicate = request.env['tour.booking'].sudo().search([
                ('package_id', '=', calendar.package_id.id),
                ('partner_id', '=', user.partner_id.id),
                ('calendar_id', '=', calendar.id),
                ('state', '!=', 'cancelled')
            ], limit=1)
            if duplicate:
                return request.redirect(f'/packages/{calendar.package_id.id}/book?error=duplicate')
                
        payment_data = {
            'payment_status': 'pending',
        }
        
        payment_method = post.get('payment_method')
        if payment_method == 'auto':
            payment_data.update({
                'visa_card_name': post.get('visa_card_name'),
                'visa_card_number': post.get('visa_card_number'),
                'visa_expiry': post.get('visa_expiry'),
                'visa_cvv': post.get('visa_cvv'),
            })
        else:
            import base64
            transaction_file = post.get('transaction_file')
            file_content = False
            filename = ''
            if transaction_file:
                file_content = base64.b64encode(transaction_file.read())
                filename = transaction_file.filename
                
            payment_data.update({
                'visa_account_name': post.get('visa_account_name'),
                'visa_account_number': post.get('visa_account_number'),
                'transfer_amount': float(post.get('transfer_amount', 0)) if post.get('transfer_amount') else 0.0,
                'payment_date': post.get('payment_date'),
                'payment_time': float(post.get('payment_time', 0).replace(':', '.')) if post.get('payment_time') else 0.0,
                'transaction_file': file_content,
                'transaction_filename': filename,
            })
            
        if existing_booking_id:
            booking = request.env['tour.booking'].sudo().browse(existing_booking_id)
            payment_data['seats'] = booking.seats + seats
            booking.sudo().write(payment_data)
        else:
            payment_data.update({
                'calendar_id': calendar.id,
                'partner_id': user.partner_id.id,
                'user_id': user.id,
                'seats': seats,
            })
            request.env['tour.booking'].sudo().create(payment_data)
            
        request.session.pop('pending_payment', None)
        return request.redirect('/my/bookings')


    @http.route(['/qrcode/visa/<string:account_number>'], type='http', auth='public', website=True)
    def generate_qr_code(self, account_number, **kwargs):
        import qrcode
        import io
        
        qr = qrcode.make(account_number)
        img_byte_arr = io.BytesIO()
        qr.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        return request.make_response(
            img_byte_arr.read(),
            headers=[('Content-Type', 'image/png')]
        )


class CustomerPortal(http.Controller):

    @http.route(['/my/bookings'], type='http', auth="user", website=True)
    def portal_my_bookings(self, **kw):
        bookings = request.env['tour.booking'].sudo().search([('user_id', '=', request.env.user.id)])
        return request.render('tour_package.portal_my_bookings', {
            'bookings': bookings,
            'page_name': 'booking',
        })

    @http.route(['/my/bookings/calendar'], type='http', auth="user", website=True)
    def portal_my_bookings_calendar(self, **kw):
        import json
        import datetime
        bookings = request.env['tour.booking'].sudo().search([('user_id', '=', request.env.user.id)])
        
        events = []
        for b in bookings:
            if b.date_start and b.date_end:
                # FullCalendar end date is exclusive, so add 1 day to date_end
                end_date = b.date_end + datetime.timedelta(days=1)
                
                # Color code based on payment status
                color = '#28a745' if b.payment_status == 'confirmed' else '#ffc107'
                
                events.append({
                    'title': f"{b.package_id.name}",
                    'start': b.date_start.strftime('%Y-%m-%d'),
                    'end': end_date.strftime('%Y-%m-%d'),
                    'url': f'/my/bookings/{b.id}',
                    'backgroundColor': color,
                    'borderColor': color,
                    'textColor': '#fff' if b.payment_status == 'confirmed' else '#000',
                    'extendedProps': {
                        'booking_id': b.id,
                        'package_name': b.package_id.name,
                        'date_range': f"{b.date_start.strftime('%Y-%m-%d')} to {b.date_end.strftime('%Y-%m-%d')}",
                        'seats': b.seats,
                        'status': dict(b.fields_get(allfields=['payment_status'])['payment_status']['selection']).get(b.payment_status, b.payment_status)
                    }
                })
                
        return request.render('tour_package.portal_my_bookings_calendar', {
            'events_json': json.dumps(events),
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
