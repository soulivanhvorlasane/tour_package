from odoo import models, api

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _post_process(self):
        """ Override of payment to automatically confirm tour bookings when payment is done. """
        super()._post_process()
        
        for tx in self.filtered(lambda t: t.state == 'done' and t.reference):
            # Odoo payment references can be appended with -1, -2 for retries (e.g. TB001-1)
            # We split by '-' to grab the base booking name.
            ref_prefix = tx.reference.split('-')[0]
            
            # Search for a matching booking
            booking = self.env['tour.booking'].sudo().search([('name', '=', ref_prefix)], limit=1)
            
            if booking and booking.state == 'draft':
                # Create invoice
                invoice = self.env['account.move'].sudo().create({
                    'move_type': 'out_invoice',
                    'partner_id': booking.partner_id.id,
                    'invoice_line_ids': [(0, 0, {
                        'name': booking.name,
                        'quantity': booking.seats,
                        'price_unit': booking.price,
                    })],
                })
                invoice.action_post()
                
                # Automatically confirm the booking
                booking.action_confirm()
