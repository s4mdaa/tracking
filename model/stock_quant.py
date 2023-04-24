from odoo import _, api, fields, models


class Quant(models.Model):
    _name = 'stock.quant'
    _description = 'Quants'

    product_id = fields.Many2one(
        'product.product', 'Product', ondelete='restrict', required=True, index=True, check_company=True)
    product_tmpl_id = fields.Many2one(
        'product.template', string='Product Template',
        related='product_id.product_tmpl_id')
    product_uom_id = fields.Many2one(
        'uom.uom', 'Unit',
        readonly=True, related='product_id.uom_id')
    company_id = fields.Many2one(
        related='location_id.company_id', string='Company', store=True, readonly=True)
    location_id = fields.Many2one(
        'stock.location', 'Location', auto_join=True, ondelete='restrict', required=True, index=True, check_company=True)
    quantity = fields.Float(
        'Quantity',
        help='Quantity of products in this quant, in the default unit of measure of the product',
        readonly=True, digits='Product Unit of Measure')
