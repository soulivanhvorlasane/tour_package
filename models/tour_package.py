from odoo import models, fields

class TourPackage(models.Model):
    _name = 'tour.package'
    _description = 'Tour Package'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Package Name', required=True, tracking=True)
    description = fields.Html(string='Description')
    price = fields.Float(string='Price per Person', required=True, tracking=True)
    duration = fields.Integer(string='Duration (Days)')
    image = fields.Image(string='Image')
    
    calendar_ids = fields.One2many('tour.calendar', 'package_id', string='Availabilities')
    
    active = fields.Boolean(default=True)
