from odoo import models, fields, api, tools
from odoo.exceptions import ValidationError
from odoo.modules.module import get_module_resource
import base64
import os
import shutil
import datetime
import logging

_logger = logging.getLogger(__name__)

class TourPackage(models.Model):
    _name = 'tour.package'
    _description = 'Tour Package'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Package Name', required=True, tracking=True)
    category_id = fields.Many2one('tour.package.category', string='Category')
    description = fields.Html(string='Description')
    price = fields.Float(string='Price per Person', required=True, tracking=True)
    duration = fields.Integer(string='Duration (Days)')
    cover_image = fields.Binary(string='Cover Image', attachment=True)
    
    # Link products such as car fee, room fee, travel fee
    line_ids = fields.One2many(
        'tour.package.line',
        'package_id',
        string='Included Products'
    )
    
    untaxed_amount = fields.Float(string="Untaxed Amount", compute="_compute_amounts", store=True)
    tax_amount = fields.Float(string="Tax 15%", compute="_compute_amounts", store=True)
    total_amount = fields.Float(string="Total", compute="_compute_amounts", store=True)
    terms_and_conditions = fields.Html(string="Terms and Conditions")

    @api.depends("line_ids.price_subtotal")
    def _compute_amounts(self):
        for record in self:
            untaxed = sum(line.price_subtotal for line in record.line_ids)
            tax = untaxed * 0.15
            record.untaxed_amount = untaxed
            record.tax_amount = tax
            record.total_amount = untaxed + tax
    
    calendar_ids = fields.One2many('tour.calendar', 'package_id', string='Availabilities')
    
    # Photo Gallery and Video
    image_ids = fields.Many2many('ir.attachment', 'tour_package_attachment_rel', 'tour_id', 'attachment_id', string='Photo Gallery')
    preview_html = fields.Html(compute='_compute_preview_html', string='Preview')
    video_url = fields.Char(string='YouTube Video URL')
    embed_video_url = fields.Char(compute='_compute_embed_video_url')

    active = fields.Boolean(default=True)

    start_date = fields.Date(string='Start Date', compute='_compute_dates', store=True)
    end_date = fields.Date(string='End Date', compute='_compute_dates', store=True)
    availability_status = fields.Char(string='Status', compute='_compute_availability_status', store=False)

    @api.depends('calendar_ids.date_start', 'calendar_ids.date_end')
    def _compute_dates(self):
        for record in self:
            starts = [d for d in record.calendar_ids.mapped('date_start') if d]
            ends = [d for d in record.calendar_ids.mapped('date_end') if d]
            record.start_date = min(starts) if starts else False
            record.end_date = max(ends) if ends else False

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.image_ids:
                record.image_ids.sudo().write({'public': True})
            if record.cover_image:
                attachment = self.env['ir.attachment'].search([
                    ('res_model', '=', self._name),
                    ('res_field', '=', 'cover_image'),
                    ('res_id', '=', record.id)
                ], limit=1)
                if attachment:
                    attachment.sudo().write({'public': True})
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'image_ids' in vals:
            for record in self:
                record.image_ids.sudo().write({'public': True})
        
        # Ensure cover image is public if we need it
        if 'cover_image' in vals:
            for record in self:
                attachment = self.env['ir.attachment'].search([
                    ('res_model', '=', self._name),
                    ('res_field', '=', 'cover_image'),
                    ('res_id', '=', record.id)
                ], limit=1)
                if attachment:
                    attachment.sudo().write({'public': True})
        return res



    @api.model
    def _cron_backup_images(self):
        filestore_path = tools.config.filestore(self.env.cr.dbname)
        source_dir = os.path.join(filestore_path, 'tour_package')
        
        if not os.path.exists(source_dir):
            _logger.info("No tour_package images found to backup.")
            return

        # Backup destination: /backups/tour_package_images/ relative to Odoo root
        # tools.config['root_path'] is typically the 'odoo' folder inside the project root
        project_root = os.path.dirname(tools.config['root_path'])
        backup_root = os.path.join(project_root, 'backups', 'tour_package_images')
        
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d')
        backup_dir = os.path.join(backup_root, timestamp)
        
        if not os.path.exists(backup_root):
            os.makedirs(backup_root)
            
        if os.path.exists(backup_dir):
            shutil.rmtree(backup_dir)
            
        shutil.copytree(source_dir, backup_dir)
        _logger.info("Successfully backed up tour_package images to %s", backup_dir)

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
