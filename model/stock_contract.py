from odoo import fields, models


class Contract(models.Model):
    _name = 'stock.contract'
    _description = "Stock Contract"
    _order = 'sequence, id'

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence', default=10)
    company_id = fields.Many2one(
        'res.company', 'Company', related='location_id.company_id')
    product_id = fields.Many2one('product.product', 'Product')
    state = fields.Selection([
        ('draft', 'New'),
        ('open', 'Running'),
        ('close', 'Expired'),
        ('cancel', 'Cancelled')
    ], string='Status', group_expand='_expand_states', copy=False,
        tracking=True, help='Status of the contract', default='draft')
    date_start = fields.Date(
        'Start Date', default=fields.Date.today, tracking=True, index=True)
    date_end = fields.Date('End Date', tracking=True,
                           help="End date of the contract (if it's a fixed-term contract).")
    source_company_id = fields.Many2one('res.company', 'Source Company')
    destination_company_id = fields.Many2one(
        'res.company', 'Destination Company')
    active = fields.Boolean(default=True)
    location_id = fields.Many2one(
        'stock.location', 'Source Location', domain=[('usage', '=', 'internal')])
    location_dest_id = fields.Many2one(
        'stock.location', 'Destination Location', domain=[('usage', '=', 'internal')])
    total_qty = fields.Integer('Quantity')
