from odoo import _, api, fields, models


class Location(models.Model):
    _name = "stock.location"
    _description = "Stock Location"

    name = fields.Char(string='Location Name', required=True, translate=True)
    active = fields.Boolean(
        'Active', default=True, help="By unchecking the active field, you may hide a location without deleting it.")
    usage = fields.Selection([
        ('supplier', 'Vendor Location'),
        ('view', 'View'),
        ('internal', 'Internal Location'),
        ('customer', 'Customer Location'),
        ('inventory', 'Inventory Loss'),
        ('production', 'Production'),
        ('transit', 'Transit Location')], string='Location Type',
        default='internal', index=True, required=True)
    location_id = fields.Many2one(
        'stock.location', 'Parent Location', index=True, ondelete='cascade',
        help="The parent location that includes this location. Example : The 'Dispatch Zone' is the 'Gate 1' parent location.")
    company_id = fields.Many2one(
        'res.company', 'Company', index=True,
        help='Let this field empty if this location is shared between companies')
    complete_name = fields.Char(
        "Full Location Name", compute='_compute_complete_name', recursive=True, store=True, translate=True)
    posz = fields.Integer('Height (Z)', default=0,
                          help="Optional localization details, for information purpose only")
    scrap_location = fields.Boolean('Is a Scrap Location?', default=False,
                                    help='Check this box to allow using this location to put scrapped/damaged goods.')

    @api.depends('name', 'location_id.complete_name', 'usage')
    def _compute_complete_name(self):
        for location in self:
            if location.location_id and location.usage != 'view':
                location.complete_name = '%s/%s' % (
                    location.location_id.complete_name, location.name)
            else:
                location.complete_name = location.name

    def name_get(self):
        result = []
        for location in self:
            name = location.complete_name or location.name
            result.append((location.id, name))
        return result
