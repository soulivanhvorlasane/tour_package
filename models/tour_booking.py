from odoo import models, fields, api
from odoo.exceptions import ValidationError

class TourBooking(models.Model):
    _name = 'tour.booking'
    _description = 'Tour Booking'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Booking Reference', required=True, copy=False, readonly=True, default=lambda self: 'New')
    calendar_id = fields.Many2one('tour.calendar', string='Tour Date', required=True, ondelete='restrict')
    package_id = fields.Many2one(related='calendar_id.package_id', string='Package', store=True)
    date_start = fields.Date(related='calendar_id.date_start', string='Start Date', store=True)
    date_end = fields.Date(related='calendar_id.date_end', string='End Date', store=True)
    
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    
    seats = fields.Integer(string='Number of Seats', required=True, default=1)
    total_price = fields.Float(string='Total Price', compute='_compute_total_price', store=True)
    
    payment_status = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done')
    ], default='draft', string='Payment Status', tracking=True)

    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)

    # Option A: Auto payment with Visa card
    visa_card_number = fields.Char(string="Visa Card Number")
    visa_card_name = fields.Char(string="Cardholder Name")
    visa_expiry = fields.Char(string="Expiry Date")
    visa_cvv = fields.Char(string="CVV")

    # Option B: QR code payment
    visa_account_name = fields.Char(string='Visa Account Name')
    visa_account_number = fields.Char(string='Visa Account Number')
    transfer_amount = fields.Float(string='Transfer Amount')
    transaction_file = fields.Binary(string='Transaction Capture File')
    transaction_filename = fields.Char(string='Transaction File Name')
    payment_date = fields.Date(string='Payment Date')
    payment_time = fields.Float(string='Payment Time (HH:MM)')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    @api.depends('seats', 'package_id.price')
    def _compute_total_price(self):
        for record in self:
            record.total_price = record.seats * (record.package_id.price or 0.0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('tour.booking') or 'New'
        return super().create(vals_list)

    @api.constrains('seats', 'calendar_id')
    def _check_availability(self):
        for record in self:
            if record.state != 'cancelled':
                # Re-calculate remaining seats for the specific calendar to avoid overbooking
                confirmed_bookings = self.env['tour.booking'].search([
                    ('calendar_id', '=', record.calendar_id.id),
                    ('state', '=', 'confirmed'),
                    ('id', '!=', record.id)
                ])
                booked_seats = sum(confirmed_bookings.mapped('seats'))
                if record.state == 'confirmed':
                    booked_seats += record.seats
                
                if booked_seats > record.calendar_id.available_seats:
                    raise ValidationError("Not enough seats available for this tour date.")

    @api.constrains('package_id', 'partner_id', 'calendar_id')
    def _check_duplicate_booking(self):
        for record in self:
            duplicate = self.search([
                ('id', '!=', record.id),
                ('package_id', '=', record.calendar_id.package_id.id),
                ('partner_id', '=', record.partner_id.id),
                ('calendar_id', '=', record.calendar_id.id),
                ('state', '!=', 'cancelled')
            ], limit=1)
            if duplicate:
                # If created from backend, use RedirectWarning to show merge wizard
                # Note: this requires the wizard action to exist
                action = self.env.ref('tour_package.action_tour_booking_merge_wizard', raise_if_not_found=False)
                if action:
                    msg = "This customer has already booked this package for the same round date."
                    from odoo.exceptions import RedirectWarning
                    raise RedirectWarning(
                        msg, 
                        action.id, 
                        "Add Seats to Existing Booking", 
                        additional_context={
                            'default_existing_booking_id': duplicate.id,
                            'default_new_seats': record.seats,
                        }
                    )
                else:
                    from odoo.exceptions import ValidationError
                    raise ValidationError("This customer has already booked this package for the same round date.")

    def action_confirm(self):
        for record in self:
            if record.seats <= 0:
                raise ValidationError("Number of seats must be strictly positive.")
            if record.calendar_id.remaining_seats < record.seats:
                raise ValidationError("Not enough seats available.")
            
            # Collect product list from linked package
            invoice_lines = []
            if record.package_id.line_ids:
                for line in record.package_id.line_ids:
                    invoice_lines.append((0, 0, {
                        'product_id': line.product_id.id,
                        'name': line.name,
                        'quantity': line.quantity * record.seats,  # dynamic based on seats and line quantity
                        'price_unit': line.price_unit,
                    }))

                # Create invoice automatically
                invoice = self.env['account.move'].create({
                    'move_type': 'out_invoice',
                    'partner_id': record.partner_id.id,
                    'invoice_date': fields.Date.today(),
                    'invoice_origin': record.name,
                    'ref': f"Booking for {record.package_id.name}",
                    'invoice_line_ids': invoice_lines,
                })
                record.invoice_id = invoice.id

            record.state = 'confirmed'
            
            # Send confirmation email
            template = self.env.ref('tour_package.email_template_tour_booking_confirmed', raise_if_not_found=False)
            if template:
                template.send_mail(record.id, force_send=True)

    def action_cancel(self):
        for record in self:
            record.state = 'cancelled'
            
            # Send cancellation email
            template = self.env.ref('tour_package.email_template_tour_booking_cancelled', raise_if_not_found=False)
            if template:
                template.send_mail(record.id, force_send=True)

    def action_view_invoice(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'context': "{'create': False}"
        }
