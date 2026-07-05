from odoo import models, fields

class TourPackageCategory(models.Model):
    _name = 'tour.package.category'
    _description = 'Tour Package Category'

    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)

