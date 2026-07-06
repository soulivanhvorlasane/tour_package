from odoo import models, fields, api

class TourBookingMergeWizard(models.TransientModel):
    _name = "tour.booking.merge.wizard"
    _description = "Merge Duplicate Booking Wizard"

    existing_booking_id = fields.Many2one('tour.booking', string="Existing Booking", required=True)
    new_seats = fields.Integer(string="Seats to Add", required=True, default=1)
    
    @api.model
    def default_get(self, fields_list):
        res = super(TourBookingMergeWizard, self).default_get(fields_list)
        if self.env.context.get('default_existing_booking_id'):
            res['existing_booking_id'] = self.env.context.get('default_existing_booking_id')
        if self.env.context.get('default_new_seats'):
            res['new_seats'] = self.env.context.get('default_new_seats')
        return res

    def action_merge_seats(self):
        self.ensure_one()
        if self.existing_booking_id and self.new_seats > 0:
            self.existing_booking_id.seats += self.new_seats
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
