from odoo import _, _lt, api, fields, models


class Warehouse(models.Model):
    _name = "stock.warehouse"
    _description = "Warehouse"

    def _default_name(self):
        count = self.env['stock.warehouse'].with_context(
            active_test=False).search_count([('company_id', '=', self.env.company.id)])
        return "%s - warehouse # %s" % (self.env.company.name, count + 1) if count else self.env.company.name

    name = fields.Char('Warehouse', required=True, default=_default_name)
    active = fields.Boolean('Active', default=True)
    company_id = fields.Many2one(
        'res.company', 'Company', default=lambda self: self.env.company,
        readonly=True, required=True,
        help='The company is automatically set from your user preferences.')
    partner_id = fields.Many2one(
        'res.partner', 'Address', default=lambda self: self.env.company.partner_id)
    code = fields.Char('Short Name', required=True, size=5,
                       help="Short name used to identify your warehouse")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('company_id'):
                vals['company_id'] = self.env.company.id
            parent_location = self.env.ref(
                'tracking.stock_location_locations', raise_if_not_found=False)
            view_location = self.env['stock.location'].create({
                'name': vals.get('code'),
                'usage': 'view',
                'location_id': parent_location and parent_location.id or False,
                'company_id': vals.get('company_id'),
            })

            self.env['stock.location'].create({
                'name': 'Stock',
                'usage': 'internal',
                'location_id': view_location and view_location.id or False,
                'company_id': vals.get('company_id'),
            })
        warehouses = super().create(vals_list)
        return warehouses
