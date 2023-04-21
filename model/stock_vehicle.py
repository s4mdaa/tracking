from odoo import api, fields, models


class Vehicle(models.Model):
    _name = 'stock.vehicle'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Stock Vehicle"
    _order = "state_number"

    @ api.onchange('company_id', 'state_number')
    def _compute_name(self):
        for item in self:
            item.name = str(item.company_id.name) + \
                "." + str(item.state_number)

    name = fields.Char('Name', compute='_compute_name')
    vehicle_type = fields.Selection([
        ('track', 'Track'),
        ('train', 'Train')],
        string="Vehicle Type", required=True, default='track')
    state_number = fields.Char('State number', required=True)
    company_id = fields.Many2one(
        'res.company', 'Company', default=lambda self: self.env.company, required=True)
    active = fields.Boolean(default=True)
    location_id = fields.Many2one('stock.location', 'Location', readonly=True)

    _sql_constraints = [
        ('name_uniq', 'unique (name)',
         "Vehicle already exists on current company.")
    ]

    @api.model
    def create(self, vals):
        parent_location = self.env['stock.location'].search(
            [('company_id', '=', vals.get('company_id')), ('usage', '=', 'internal'), ], order='id ASC', limit=1)
        location_vals = {
            'name': vals.get('state_number'),
            'usage': 'internal',
            'location_id': parent_location.id,
            'company_id': vals.get('company_id'),
        }
        location = self.env['stock.location'].sudo().create(location_vals)
        vals['location_id'] = location.id
        result = super(Vehicle, self).create(vals)
        return result

    def write(self, vals):
        result = super(Vehicle, self).write(vals)
        location = self.env['stock.location'].browse(self.location_id.id)
        if 'state_number' in vals:
            location.name = vals['state_number']
        if 'company_id' in vals:
            parent_location = self.env['stock.location'].search(
                [('company_id', '=', vals['company_id']), ('usage', '=', 'internal'), ], order='id ASC', limit=1)
            location.location_id = parent_location.id
            location.company_id = vals['company_id']
        return result
