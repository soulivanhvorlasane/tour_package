from odoo import models, fields, api
from odoo.exceptions import ValidationError

class TourPackage(models.Model):
    _name = 'tour.package'
    _description = 'Tour Package'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Package Name', required=True, tracking=True)
    description = fields.Html(string='Description')
    price = fields.Float(string='Price per Person', required=True, tracking=True)
    duration = fields.Integer(string='Duration (Days)')
    image = fields.Image(string='Main Image')
    
    calendar_ids = fields.One2many('tour.calendar', 'package_id', string='Availabilities')
    
    # Photo Gallery and Video
    image_ids = fields.Many2many('ir.attachment', 'tour_package_attachment_rel', 'tour_id', 'attachment_id', string='Photo Gallery')
    preview_html = fields.Html(compute='_compute_preview_html', string='Preview')
    video_url = fields.Char(string='YouTube Video URL')
    embed_video_url = fields.Char(compute='_compute_embed_video_url')

    active = fields.Boolean(default=True)

    @api.depends('image_ids')
    def _compute_preview_html(self):
        for record in self:
            if not record.image_ids:
                record.preview_html = "<p class='text-muted'>No images uploaded yet.</p>"
                continue
                
            html = '<div style="display: flex; flex-wrap: wrap; gap: 15px;">'
            for img in record.image_ids:
                html += f'<div style="border: 1px solid #ddd; padding: 5px; border-radius: 5px; background: #fff;"><img src="/web/image/{img.id}" style="height: 150px; width: auto; object-fit: cover; border-radius: 3px;"/></div>'
            html += '</div>'
            record.preview_html = html

    @api.constrains('image_ids')
    def _check_image_limit(self):
        for record in self:
            if len(record.image_ids) > 5:
                raise ValidationError("You can upload a maximum of 5 images for the photo gallery.")

    @api.depends('video_url')
    def _compute_embed_video_url(self):
        for record in self:
            if record.video_url and 'youtube.com/watch?v=' in record.video_url:
                video_id = record.video_url.split('v=')[1][:11]
                record.embed_video_url = f'https://www.youtube.com/embed/{video_id}'
            elif record.video_url and 'youtu.be/' in record.video_url:
                video_id = record.video_url.split('youtu.be/')[1][:11]
                record.embed_video_url = f'https://www.youtube.com/embed/{video_id}'
            else:
                record.embed_video_url = False
