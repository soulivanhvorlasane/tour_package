from odoo import models, fields, api

class TourPackageLine(models.Model):
    _name = 'tour.package.line'
    _description = 'Tour Package Line'

    package_id = fields.Many2one('tour.package', string='Tour Package', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, domain=[('type', '=', 'service')])
    name = fields.Char(string='Description', required=True)
    quantity = fields.Float(string='Quantity', default=1.0, required=True)
    price_unit = fields.Float(string='Unit Price', required=True)
    price_subtotal = fields.Float(string='Subtotal', compute='_compute_price_subtotal', store=True)

    @api.depends('quantity', 'price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.quantity * line.price_unit

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.name
            self.price_unit = self.product_id.list_price
