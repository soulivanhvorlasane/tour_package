from odoo import models, api
from odoo.tools import convert_file
import logging

_logger = logging.getLogger(__name__)

class TourDemoWizard(models.TransientModel):
    _name = 'tour.demo.wizard'
    _description = 'Manage Tour Package Demo Data'

    def action_load_demo_data(self):
        try:
            convert_file(self.env, 'tour_package', 'data/demo.xml', None, mode='init', noupdate=False, kind='data')
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'Demo data loaded successfully.',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error("Failed to load demo data: %s", e)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': f'Failed to load demo data: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def action_remove_demo_data(self):
        packages = self.env['tour.package'].search([('is_demo', '=', True)])
        calendars = self.env['tour.calendar'].search([('is_demo', '=', True)])
        
        pkg_count = len(packages)
        cal_count = len(calendars)
        
        calendars.unlink()
        packages.unlink()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'Removed {pkg_count} packages and {cal_count} calendars.',
                'type': 'success',
                'sticky': False,
            }
        }
