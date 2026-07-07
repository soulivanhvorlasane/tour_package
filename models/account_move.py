from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    tour_booking_ids = fields.One2many('tour.booking', 'invoice_id', string='Tour Bookings')

    def action_post(self):
        res = super().action_post()
        for move in self:
            for booking in move.tour_booking_ids:
                booking.payment_status = 'done'
        return res
