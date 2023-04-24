from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES
from odoo.exceptions import UserError


class Picking(models.Model):
    _name = "stock.picking"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Picking Type"

    name = fields.Char(
        'Reference', default='/',
        copy=False, index='trigram', readonly=True)
    vehicle_id = fields.Many2one(
        'stock.vehicle', 'Vehicle', required=True, readonly=True,
        states={'draft': [('readonly', False)]})

    company_id = fields.Many2one(
        'res.company', string='Company', related='contract_id.company_id',
        readonly=True, store=True, index=True)

    picking_type = fields.Selection([
        ('receipt', 'Receipt'),
        ('delivery', 'Delivery')],
        string="Picking Type", required=True, default='receipt')

    contract_id = fields.Many2one(
        'stock.contract', 'Contract', required=True, readonly=True,
        states={'draft': [('readonly', False)]})

    total_qty = fields.Integer(
        'Total Quantity', related='contract_id.total_qty', readonly=True)
    available_qty = fields.Integer(
        'Available Quantity', compute='_compute_available_qty', readonly=True)
    transfer_qty = fields.Integer('Demand', required=True, default=1,
                                  states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    note = fields.Html('Note', readonly=True,
                       states={'draft': [('readonly', False)]})
    location_dest_id = fields.Many2one(
        'stock.location', 'Destination Location', compute='_compute_dest_location', readonly=True)
    location_id = fields.Many2one(
        'stock.location', 'Source Location', compute='_compute_source_location', readonly=True)
    delivery_point_id = fields.Many2one(
        'stock.location', 'Delivery Point', compute='_compute_delivery_point', readonly=True)
    product_id = fields.Many2one(
        related='contract_id.product_id', readonly=True)
    priority = fields.Selection(
        PROCUREMENT_PRIORITIES, string='Priority', default='0',
        help="Products will be reserved first for the transfers with the highest priorities.")
    scheduled_date = fields.Datetime(
        'Scheduled Date', store=True,
        index=True, default=fields.Datetime.now, tracking=True, readonly=True,
        states={'draft': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('assigned', 'Ready'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', copy=False, index=True, readonly=True, store=True, tracking=True)

    def action_assign(self):
        self.state = 'assigned'
        return True

    def action_cancel(self):
        self.state = 'cancel'
        return True

    def action_done(self):
        for rec in self:
            if rec.transfer_qty > rec.available_qty:
                raise UserError(
                    'Transfer quantity cannot be greater than available quantity.')
        self.state = 'done'
        stock_move_vals = {
            'name': str(self.location_id.name) + '-' + str(self.location_dest_id.name),
            'contract_id': self.contract_id.id,
            'vehicle_id': self.vehicle_id.id,
            'location_id': self.location_id.id,
            'location_dest_id': self.location_dest_id.id,
            'product_id': self.product_id.id,
            'product_qty': self.transfer_qty,
            'product_uom': self.product_id.uom_id.id,
            'description_picking': self.product_id.name,
            'company_id': self.company_id.id,
            'date': self.scheduled_date,
            'picking_id': self.id,
            'state': self.state,
        }
        self.env['stock.move'].sudo().create(stock_move_vals)
        stock_quant_source = self.env['stock.quant'].search(
            [('location_id', '=', self.location_id.id)], limit=1)
        stock_quant_dest = self.env['stock.quant'].search(
            [('location_id', '=', self.location_dest_id.id)], limit=1)
        if stock_quant_source:
            stock_quant_source.quantity -= self.transfer_qty
        if stock_quant_dest:
            stock_quant_dest.quantity += self.transfer_qty
        else:
            stock_quant_vals = {
                'location_id': self.location_dest_id.id,
                'product_id': self.product_id.id,
                'quantity': self.transfer_qty,
            }
        self.env['stock.quant'].sudo().create(stock_quant_vals)

        return True

    @ api.depends('contract_id')
    def _compute_delivery_point(self):
        for rec in self:
            rec.delivery_point_id = rec.contract_id.location_dest_id.id

    @ api.depends('contract_id', 'picking_type')
    def _compute_source_location(self):
        for rec in self:
            if rec.picking_type == 'delivery':
                source_location = self.env['stock.location'].search(
                    [('usage', '=', 'internal'), ('company_id', '=', self.env.user.company_id.id)], order='id ASC', limit=1)
                rec.location_id = source_location.id
            else:
                source_location = self.env['stock.location'].search(
                    [('usage', '=', 'transit'), ('company_id', '=', self.env.user.company_id.id)], order='id ASC', limit=1)
                rec.location_id = source_location.id

    @ api.depends('contract_id', 'picking_type')
    def _compute_dest_location(self):
        for rec in self:
            if rec.picking_type == 'delivery':
                destination_location = self.env['stock.location'].search(
                    [('usage', '=', 'transit'), ('company_id', '=', self.env.user.company_id.id)], order='id ASC', limit=1)
                rec.location_dest_id = destination_location.id
            else:
                destination_location = self.env['stock.location'].search(
                    [('usage', '=', 'internal'), ('company_id', '=', self.env.user.company_id.id)], order='id ASC', limit=1)
                rec.location_dest_id = destination_location.id

    @ api.depends('contract_id', 'state')
    def _compute_available_qty(self):
        for rec in self:
            done_pickings = self.env['stock.picking'].search(
                [('state', '=', 'done'), ('contract_id', '=', rec.contract_id.id)])
            total_qty = sum(done_pickings.mapped('transfer_qty'))
            rec.available_qty = rec.contract_id.total_qty - total_qty

    @ api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('transfer_qty') <= 0:
                raise UserError('Transfer quantity must be greater than zero.')
            now = fields.Date.today().strftime('%y%m%d')
            sequence = self.env['ir.sequence'].sudo().search([
                ('code', '=', 'stock.picking'),
                ('prefix', 'like', f'TS-{now}-')
            ], limit=1)
            if not sequence:
                sequence = self.env['ir.sequence'].sudo().create({
                    'name': _('Sequence'),
                    'code': 'stock.picking',
                    'padding': 3,
                    'prefix': f'TS-{now}-',
                    'number_increment': 1,
                    'company_id': self.env.user.company_id.id,
                })
            vals['name'] = sequence.next_by_id()
        pickings = super().create(vals_list)
        return pickings
