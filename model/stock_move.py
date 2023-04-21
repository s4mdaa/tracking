from odoo import _, api, Command, fields, models

class Move(models.Model):
    _name = "stock.move"
    _description = "Stock Move"
