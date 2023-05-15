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
        domain="[('type', 'in', ['product', 'consu']), '|', ('company_id', '=', False), ('company_id', '=', company_id)]", index=True, required=True,
        states={'moved': [('readonly', True)]})
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
        help="Sets a location if you produce at a fixed location. This can be a partner location if you subcontract the manufacturing operations.")
    location_name = fields.Char(compute='_compute_location_name')
    source_company_id = fields.Many2one(
        'res.company', 'Dest Company', related='location_id.company_id')
    location_dest_id = fields.Many2one(
        'stock.location', 'Destination Location',
        auto_join=True, index=True, required=True,
        help="Location where the system will stock the finished products.")
    location_dest_name = fields.Char(compute='_compute_location_name')
    dest_company_id = fields.Many2one(
        'res.company', 'Source Company', related='location_dest_id.company_id')
    picking_id = fields.Many2one('stock.picking', 'Transfer', index=True, states={
                                 'moved': [('readonly', True)]})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('moving', 'Moving'),
        ('moved', 'Moved'),
    ], string='Status', default='draft', copy=False, index=True, readonly=True, store=True, tracking=True)
    reference = fields.Char(compute='_compute_reference',
                            string="Reference", store=True, translate=True)
    contract_id = fields.Many2one(
        'stock.contract', 'Contract')
    vehicle_id = fields.Many2one(
        'stock.vehicle', 'Vehicle', readonly=True)
    location_usage = fields.Selection(
        string="Source Location Type", related='location_id.usage')
    location_dest_usage = fields.Selection(
        string="Destination Location Type", related='location_dest_id.usage')
    description_picking = fields.Text('Description of Picking')

    @api.depends('picking_id', 'name')
    def _compute_reference(self):
        for move in self:
            if not move.reference:
                move.reference = move.picking_id.name if move.picking_id else move.name

    @api.depends('location_id')
    def _compute_location_name(self):
        for move in self:
            if move.location_id.usage == 'transit':
                move.location_name = move.location_id.location_id.name
                move.location_dest_name = move.location_dest_id.name
            else:
                if 'Үйлдвэрлэл' in move.reference or 'Production' in move.reference:
                    default_lang = self.env['res.lang'].search(
                        [('active', '=', True)])
                    if default_lang.iso_code == 'en':
                        move.location_name = 'Production'
                    else:
                        move.location_name = 'Үйлдвэрлэл'
                    move.location_dest_name = move.location_dest_id.name
                else:
                    move.location_name = move.location_id.name
                    move.location_dest_name = move.location_dest_id.location_id.name

    @api.depends('product_id')
    def _compute_product_uom(self):
        for move in self:
            move.product_uom = move.product_id.uom_id.id
