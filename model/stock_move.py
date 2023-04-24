from odoo import _, api, Command, fields, models


class Move(models.Model):
    _name = "stock.move"
    _description = "Stock Move"

    name = fields.Char('Description', required=True)
    sequence = fields.Integer('Sequence', default=10)
    date = fields.Datetime(
        'Date Scheduled', default=fields.Datetime.now, index=True, required=True,
        help="Scheduled date until move is done, then date of actual move processing")
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env.company,
        index=True, required=True)
    product_id = fields.Many2one(
        'product.product', 'Product',
        check_company=True,
        domain="[('type', 'in', ['product', 'consu']), '|', ('company_id', '=', False), ('company_id', '=', company_id)]", index=True, required=True,
        states={'done': [('readonly', True)]})
    product_qty = fields.Float(
        'Real Quantity', compute='_compute_product_qty',
        digits=0, store=True, compute_sudo=True,
        help='Quantity in the default UoM of the product')
    product_uom = fields.Many2one(
        'uom.uom', "UoM", required=True, domain="[('category_id', '=', product_uom_category_id)]",
        compute="_compute_product_uom", store=True, readonly=False, precompute=True,
    )
    product_tmpl_id = fields.Many2one(
        'product.template', 'Product Template',
        related='product_id.product_tmpl_id')
    location_id = fields.Many2one(
        'stock.location', 'Source Location',
        auto_join=True, index=True, required=True,
        check_company=True,
        help="Sets a location if you produce at a fixed location. This can be a partner location if you subcontract the manufacturing operations.")
    location_dest_id = fields.Many2one(
        'stock.location', 'Destination Location',
        auto_join=True, index=True, required=True,
        check_company=True,
        help="Location where the system will stock the finished products.")
    picking_id = fields.Many2one('stock.picking', 'Transfer', index=True, states={
                                 'done': [('readonly', True)]}, check_company=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('assigned', 'Ready'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', copy=False, index=True, readonly=True, store=True, tracking=True)
    reference = fields.Char(compute='_compute_reference',
                            string="Reference", store=True)
    contract_id = fields.Many2one(
        'stock.contract', 'Contract', required=True)
    vehicle_id = fields.Many2one(
        'stock.vehicle', 'Vehicle', required=True, readonly=True)
    location_usage = fields.Selection(
        string="Source Location Type", related='location_id.usage')
    location_dest_usage = fields.Selection(
        string="Destination Location Type", related='location_dest_id.usage')
    description_picking = fields.Text('Description of Picking')

    @api.depends('picking_id', 'name')
    def _compute_reference(self):
        for move in self:
            move.reference = move.picking_id.name if move.picking_id else move.name
