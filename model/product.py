from odoo import _, api, fields, models


class Product(models.Model):
    _inherit = "product.product"


class ProductTemplate(models.Model):
    _inherit = 'product.template'


class ProductCategory(models.Model):
    _inherit = 'product.category'
