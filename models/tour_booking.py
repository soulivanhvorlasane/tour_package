from odoo import models, fields, api
from odoo.exceptions import ValidationError

class TourBooking(models.Model):
    _name = 'tour.booking'
    _description = 'Tour Booking'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Booking Reference', required=True, copy=False, readonly=True, default=lambda self: 'New')
    calendar_id = fields.Many2one('tour.calendar', string='Tour Date', required=True, ondelete='restrict')
    package_id = fields.Many2one(related='calendar_id.package_id', string='Package', store=True)
    
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    
    seats = fields.Integer(string='Number of Seats', required=True, default=1)
    total_price = fields.Float(string='Total Price', compute='_compute_total_price', store=True)
    
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

    def action_confirm(self):
        for record in self:
            if record.seats <= 0:
                raise ValidationError("Number of seats must be strictly positive.")
            if record.calendar_id.remaining_seats < record.seats:
                raise ValidationError("Not enough seats available.")
            
            # Collect product list from linked package
            invoice_lines = []
            if record.package_id.product_ids:
                for product in record.package_id.product_ids:
                    invoice_lines.append((0, 0, {
                        'product_id': product.id,
                        'quantity': record.seats,  # dynamic based on seats
                        'price_unit': product.list_price,
                    }))

                # Create invoice automatically
                invoice = self.env['account.move'].create({
                    'move_type': 'out_invoice',
                    'partner_id': record.partner_id.id,
                    'invoice_date': fields.Date.today(),
                    'invoice_line_ids': invoice_lines,
                })

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
