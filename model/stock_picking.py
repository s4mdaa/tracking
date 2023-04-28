from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES
from odoo.exceptions import UserError
from datetime import timedelta


class Picking(models.Model):
    _name = "stock.picking"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Picking Type"

    name = fields.Char(
        'Reference', default='/',
        copy=False, index='trigram', readonly=True)

    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.user.company_id.id,
        store=True, index=True)

    company_type = fields.Selection(related='company_id.company_type')

    picking_line_ids = fields.One2many(
        'stock.picking.line', 'picking_id', string="Picking Lines", copy=True)

    picking_type = fields.Selection([
        ('receipt', 'Receipt'),
        ('delivery', 'Delivery')],
        string="Picking Type", required=True, readonly=True,
        states={'draft': [('readonly', False)]}, default='receipt')

    contract_id = fields.Many2one(
        'stock.contract', 'Contract', required=True, readonly=True,
        states={'draft': [('readonly', False)]})

    total_qty = fields.Integer(
        'Total Quantity', related='contract_id.total_qty', readonly=True)
    available_qty = fields.Integer(
        'Available Quantity', compute='_compute_available_qty', readonly=True)
    delivery_point_id = fields.Many2one(
        'stock.location', 'Delivery Point', compute='_compute_main_location', readonly=True)
    source_point_id = fields.Many2one(
        'stock.location', 'Source Point', compute='_compute_main_location', readonly=True)
    product_id = fields.Many2one(
        related='contract_id.product_id', readonly=True)
    priority = fields.Selection(
        PROCUREMENT_PRIORITIES, string='Priority', default='0',
        help="Products will be reserved first for the transfers with the highest priorities.")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('edit', 'Edit'),
        ('done', 'Done'),
    ], string='Status', default='draft', copy=False, index=True, readonly=True, store=True, tracking=True)

    def action_edit(self):
        self.state = 'edit'
        return True

    def action_done(self):
        for rec in self:
            if len(rec.picking_line_ids) == 0:
                raise UserError('Шилжүүлгийн мэдээлэл хоосон байна')
            if sum(rec.picking_line_ids.mapped('transfer_qty')) > rec.available_qty:
                raise UserError(
                    'Transfer quantity cannot be greater than available quantity.')
            rec.state = 'done'
            for picking_line in rec.picking_line_ids:
                if picking_line.state != 'done':
                    picking_line.state = 'done'
                    source_location = self.env['stock.location'].search(
                        [('usage', '=', 'transit'), ('company_id', '=', picking_line.vehicle_id.company_id.id)], order='id ASC', limit=1)
                    destination_location = picking_line.vehicle_id.location_id
                    if rec.picking_type == 'receipt':
                        temp = destination_location
                        destination_location = source_location
                        source_location = temp
                        scheduled_date = picking_line.scheduled_date - \
                            timedelta(seconds=1)
                    else:
                        scheduled_date = picking_line.scheduled_date
                    print(source_location.company_id.name)
                    stock_move_vals = {
                        'name': str(source_location.name) + '-' + str(destination_location.name),
                        'contract_id': rec.contract_id.id,
                        'vehicle_id': picking_line.vehicle_id.id,
                        'location_id': source_location.id,
                        'location_dest_id': destination_location.id,
                        'product_id': rec.product_id.id,
                        'product_qty': picking_line.transfer_qty,
                        'product_uom': rec.product_id.uom_id.id,
                        'description_picking': rec.product_id.name,
                        'company_id': source_location.company_id.id,
                        'date': scheduled_date,
                        'picking_id': rec.id,
                        'state': picking_line.state,
                    }
                    self.env['stock.move'].sudo().create(stock_move_vals)
                    stock_quant_source = self.env['stock.quant'].search(
                        [('location_id', '=', source_location.id)], limit=1)
                    stock_quant_dest = self.env['stock.quant'].search(
                        [('location_id', '=', destination_location.id)], limit=1)
                    if stock_quant_source:
                        stock_quant_source.quantity -= picking_line.transfer_qty
                    if stock_quant_dest:
                        stock_quant_dest.quantity += picking_line.transfer_qty
                    else:
                        stock_quant_vals = {
                            'location_id': destination_location.id,
                            'product_id': rec.product_id.id,
                            'quantity': picking_line.transfer_qty,
                        }
                        self.env['stock.quant'].sudo().create(stock_quant_vals)
                    source_location = self.env['stock.location'].search(
                        [('usage', '=', 'internal'), ('company_id', '=', rec.company_id.id)], order='id ASC', limit=1)
                    destination_location = self.env['stock.location'].search(
                        [('usage', '=', 'transit'), ('company_id', '=', rec.company_id.id)], order='id ASC', limit=1)
                    if rec.picking_type == 'receipt':
                        temp = destination_location
                        destination_location = source_location
                        source_location = temp
                        scheduled_date = picking_line.scheduled_date
                    else:
                        scheduled_date = picking_line.scheduled_date - \
                            timedelta(seconds=1)
                    print(source_location.company_id.name)
                    stock_move_vals = {
                        'name': str(source_location.name) + '-' + str(destination_location.name),
                        'contract_id': rec.contract_id.id,
                        'vehicle_id': picking_line.vehicle_id.id,
                        'location_id': source_location.id,
                        'location_dest_id': destination_location.id,
                        'product_id': rec.product_id.id,
                        'product_qty': picking_line.transfer_qty,
                        'product_uom': rec.product_id.uom_id.id,
                        'description_picking': rec.product_id.name,
                        'company_id': source_location.company_id.id,
                        'date': scheduled_date,
                        'picking_id': rec.id,
                        'state': picking_line.state,
                    }
                    self.env['stock.move'].sudo().create(stock_move_vals)
                    stock_quant_source = self.env['stock.quant'].search(
                        [('location_id', '=', source_location.id)], limit=1)
                    stock_quant_dest = self.env['stock.quant'].search(
                        [('location_id', '=', destination_location.id)], limit=1)
                    if stock_quant_source:
                        stock_quant_source.quantity -= picking_line.transfer_qty
                    if stock_quant_dest:
                        stock_quant_dest.quantity += picking_line.transfer_qty
                    else:
                        stock_quant_vals = {
                            'location_id': destination_location.id,
                            'product_id': rec.product_id.id,
                            'quantity': picking_line.transfer_qty,
                        }
                        self.env['stock.quant'].sudo().create(stock_quant_vals)
            return True

    @ api.depends('contract_id')
    def _compute_main_location(self):
        for rec in self:
            rec.delivery_point_id = rec.contract_id.location_dest_id.id
            rec.source_point_id = rec.contract_id.location_id.id

    @ api.depends('contract_id', 'state')
    def _compute_available_qty(self):
        for rec in self:
            picking_lines = self.env['stock.picking.line'].search(
                [('picking_id', '=', rec.id), ('state', '=', 'done')])
            total_qty = sum(picking_lines.mapped('transfer_qty'))
            rec.available_qty = rec.contract_id.total_qty - total_qty

    @ api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            now = fields.Date.today().strftime('%y%m%d')
            company = self.env['res.company'].browse(vals.get('company_id'))
            prefix = f'{company.name[:3]}-{now}-'
            sequence = self.env['ir.sequence'].sudo().search([
                ('code', '=', 'stock.picking'),
                ('prefix', 'like',  prefix)
            ], limit=1)
            if not sequence:
                sequence = self.env['ir.sequence'].sudo().create({
                    'name': _('Sequence'),
                    'code': 'stock.picking',
                    'padding': 4,
                    'prefix': prefix,
                    'number_increment': 1,
                    'company_id': vals.get('company_id'),
                })
            vals['name'] = sequence.next_by_id()
        pickings = super().create(vals_list)
        return pickings


class PickingLine(models.Model):
    _name = "stock.picking.line"
    _description = "Picking Line"

    picking_id = fields.Many2one(
        'stock.picking')
    vehicle_id = fields.Many2one(
        'stock.vehicle', 'Vehicle', required=True)
    transfer_qty = fields.Integer('Demand')
    note = fields.Html('Note')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], string='Status', default='draft', copy=False, index=True, readonly=True, store=True, tracking=True)
    scheduled_date = fields.Datetime(
        'Scheduled Date', store=True,
        index=True, default=fields.Datetime.now)

    @ api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('transfer_qty') <= 0:
                raise UserError('Transfer quantity must be greater than zero.')
        picking_lines = super().create(vals_list)
        return picking_lines
