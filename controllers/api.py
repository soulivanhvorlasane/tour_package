from odoo import http
from odoo.http import request

class PackageApi(http.Controller):

    @http.route('/api/package/create', type='json', auth="user", methods=['POST'], csrf=False)
    def create_package(self, **kwargs):
        name = kwargs.get('name')
        price = kwargs.get('price')
        duration = kwargs.get('duration', 1)
        
        if not name or price is None:
            return {'error': 'Missing required fields: name, price'}
            
        try:
            # Create a new package as the authenticated user (will check access rights)
            package = request.env['tour.package'].create({
                'name': name,
                'price': float(price),
                'duration': int(duration),
                'description': kwargs.get('description', ''),
            })
            return {
                'success': True,
                'package_id': package.id,
                'message': 'Package created successfully'
            }
        except Exception as e:
            return {'error': str(e)}
