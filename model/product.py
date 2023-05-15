from odoo import _, api, fields, models


class Product(models.Model):
    _inherit = "product.product"


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    detailed_type = fields.Selection(selection_add=[
        ('product', 'Storable Product')
    ], tracking=True, ondelete={'product': 'set consu'})
    type = fields.Selection(selection_add=[
        ('product', 'Storable Product')
    ], ondelete={'product': 'set consu'})
    uom_id = fields.Many2one(
        'uom.uom', string='Unit of Measure', default=lambda self: self._get_default_uom())

    def _get_default_uom(self):
        default_uom_weight = self.env['uom.uom'].search(
            [('name', '=', 'тонн')], limit=1)
        return default_uom_weight.id

    @api.model
    def delete_products(self):
        product_templates = self.env['product.template'].search(
            [('type', '!=', 'product')])
        product_templates.unlink()


class ProductCategory(models.Model):
    _inherit = 'product.category'
