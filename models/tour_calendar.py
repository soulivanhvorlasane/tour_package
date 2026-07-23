from odoo import models, fields, api
from odoo.exceptions import ValidationError

class TourCalendar(models.Model):
    _name = 'tour.calendar'
    _description = 'Tour Calendar Availability'

    name = fields.Char(string='Reference', compute='_compute_name', store=True)
    package_id = fields.Many2one('tour.package', string='Tour Package', required=True, ondelete='cascade')
    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date', required=True)
    
    available_seats = fields.Integer(string='Total Seats', required=True, default=20)
    booked_seats = fields.Integer(string='Booked Seats', compute='_compute_booked_seats', store=True)
    remaining_seats = fields.Integer(string='Remaining Seats', compute='_compute_remaining_seats', store=True)
    
    is_demo = fields.Boolean(string='Is Demo Data', default=False)
    
    booking_ids = fields.One2many('tour.booking', 'calendar_id', string='Bookings')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open for Booking'),
        ('full', 'Fully Booked'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', compute='_compute_state', store=True, readonly=False)

    @api.depends('package_id.name', 'date_start')
    def _compute_name(self):
        for record in self:
            if record.package_id and record.date_start:
                record.name = f"{record.package_id.name} - {record.date_start}"
            else:
                record.name = "New"

    @api.depends('booking_ids.state', 'booking_ids.seats')
    def _compute_booked_seats(self):
        for record in self:
            record.booked_seats = sum(record.booking_ids.filtered(lambda b: b.state == 'confirmed').mapped('seats'))

    @api.depends('available_seats', 'booked_seats')
    def _compute_remaining_seats(self):
        for record in self:
            record.remaining_seats = record.available_seats - record.booked_seats

    @api.depends('remaining_seats')
    def _compute_state(self):
        for record in self:
            if record.state != 'draft' and record.state != 'closed':
                if record.remaining_seats <= 0:
                    record.state = 'full'
                else:
                    record.state = 'open'

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for record in self:
            if record.date_start and record.date_end and record.date_end < record.date_start:
                raise ValidationError("End Date cannot be earlier than Start Date.")

    def action_open(self):
        self.state = 'open'

    def action_close(self):
        self.state = 'closed'
