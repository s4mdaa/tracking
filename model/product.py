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
            [('name', '=', 't')], limit=1)
        return default_uom_weight.id

    @api.model
    def create_products(self):
        product_templates = self.env['product.template'].search([])
        product_templates.unlink()
        company_id = self.env['res.company'].search(
            [('company_type', '=', 'mining')], limit=1)
        for i in range(1, 6):
            attribute = self.env['product.attribute'].create({
                'name': f'Attribute0{i}',
            })
            attribute_value = self.env['product.attribute.value'].create({
                'name': f'Value0{i}',
                'attribute_id': attribute.id
            })
            attribute_line_ids = []
            attribute_line_ids.append(
                (0, 0, {
                    'attribute_id': attribute.id,
                    'value_ids': [(6, 0, [attribute_value.id])]
                })
            )
            self.env['product.template'].create({
                'name': f'Нүүрс0{i}',
                'attribute_line_ids': attribute_line_ids,
                'detailed_type': 'product',
                'company_id': company_id.id
            })


class ProductCategory(models.Model):
    _inherit = 'product.category'
