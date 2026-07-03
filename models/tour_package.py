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

    start_date = fields.Date(string='Start Date', compute='_compute_dates', store=False)
    end_date = fields.Date(string='End Date', compute='_compute_dates', store=False)
    availability_status = fields.Char(string='Status', compute='_compute_availability_status', store=False)

    @api.depends('calendar_ids.date_start', 'calendar_ids.date_end')
    def _compute_dates(self):
        for record in self:
            starts = [d for d in record.calendar_ids.mapped('date_start') if d]
            ends = [d for d in record.calendar_ids.mapped('date_end') if d]
            record.start_date = min(starts) if starts else False
            record.end_date = max(ends) if ends else False

    @api.depends('calendar_ids.state')
    def _compute_availability_status(self):
        for record in self:
            if any(cal.state == 'open' for cal in record.calendar_ids):
                record.availability_status = 'Available'
            elif all(cal.state == 'full' for cal in record.calendar_ids) and record.calendar_ids:
                record.availability_status = 'Fully Booked'
            else:
                record.availability_status = 'Not Available'
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
            if len(record.image_ids) > 6:
                raise ValidationError("You can upload a maximum of 6 images for the photo gallery.")

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
