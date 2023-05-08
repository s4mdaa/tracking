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
        states={'draft': [('readonly', False)]}, default='delivery')

    contract_id = fields.Many2one(
        'stock.contract', 'Contract', required=True, readonly=True,
        states={'draft': [('readonly', False)]})

    total_qty = fields.Integer(
        'Total Quantity', related='contract_id.total_qty', readonly=True)
    available_qty = fields.Integer(
        'Available Quantity', compute='_compute_available_qty', readonly=True)
    delivery_company = fields.Char(
        'Delivery Point', compute='_compute_company_name', readonly=True)
    source_company = fields.Char(
        'Source Point', compute='_compute_company_name', readonly=True)
    product_id = fields.Many2one(
        related='contract_id.product_id', readonly=True)
    priority = fields.Selection(
        PROCUREMENT_PRIORITIES, string='Priority', default='0',
        help="Products will be reserved first for the transfers with the highest priorities.")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('moving', 'Moving'),
        ('moved', 'Moved'),
    ], string='Status', default='draft', copy=False, index=True, readonly=True, store=True, tracking=True)

    parent_company_id = fields.Many2one(
        'res.company', 'Company', related='company_id.parent_id')

    def action_edit(self):
        self.state = 'moving'
        return True

    def action_done(self):
        for rec in self:
            if len(rec.picking_line_ids) == 0:
                raise UserError('Шилжүүлгийн мэдээлэл хоосон байна')
            if sum(rec.picking_line_ids.mapped('transfer_qty')) > rec.available_qty:
                raise UserError(
                    'Transfer quantity cannot be greater than available quantity.')
            rec.state = 'moved'
            for picking_line in rec.picking_line_ids:
                if picking_line.state != 'moved':
                    picking_line.state = 'moved'
                    locations = [
                        {'source': self.env['stock.location'].search([('usage', '=', 'transit'), ('company_id', '=', picking_line.vehicle_id.company_id.id)], order='id ASC', limit=1),
                         'destination': picking_line.vehicle_id.location_id,
                         'is_destination': True},
                        {'source': self.env['stock.location'].search([('usage', '=', 'internal'), ('company_id', '=', rec.company_id.id)], order='id ASC', limit=1),
                         'destination': self.env['stock.location'].search([('usage', '=', 'transit'), ('company_id', '=', rec.company_id.id)], order='id ASC', limit=1),
                         'is_destination': False}
                    ]
                    for location in locations:
                        scheduled_date = picking_line.scheduled_date
                        if (rec.picking_type != 'receipt' and not location['is_destination']) or (rec.picking_type == 'receipt' and location['is_destination']):
                            scheduled_date = picking_line.scheduled_date - \
                                timedelta(seconds=1)
                        if rec.picking_type == 'receipt':
                            temp = location['destination']
                            location['destination'] = location['source']
                            location['source'] = temp
                            location['is_destination'] = not location['is_destination']

                        rec._create_per_contract_line(
                            location['destination'] if location['is_destination'] else location['source'],
                            rec, picking_line, location['is_destination'])
                        rec._create_per_stock_move(
                            location['source'], location['destination'], rec, picking_line, scheduled_date)
                        rec._create_per_stock_quants(
                            location['source'], location['destination'], picking_line, rec)
            return True

    def _create_per_stock_move(self, source_location, destination_location, rec, picking_line, scheduled_date):
        print("WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW")
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

    def _create_per_contract_line(self, location, rec, picking_line, is_destination):
        if location.usage == 'internal':
            stock_contract_line = self.env['stock.contract.line'].search(
                [('location_id', '=', location.id), ('contract_id', '=', rec.contract_id.id)], limit=1)
            if stock_contract_line:
                if is_destination == True:
                    stock_contract_line.quantity += picking_line.transfer_qty
                else:
                    stock_contract_line.quantity -= picking_line.transfer_qty
            else:
                stock_contract_line_dest_vals = {
                    'location_id': location.id,
                    'product_id': rec.product_id.id,
                    'quantity': picking_line.transfer_qty,
                    'contract_id': rec.contract_id.id,
                }
                self.env['stock.contract.line'].sudo().create(
                    stock_contract_line_dest_vals)

    def _create_per_stock_quants(self, source_location, destination_location, picking_line, rec):
        quant_params = [
            {
                'location_id': source_location.id,
                'product_id': rec.product_id.id,
                'quantity': -(picking_line.transfer_qty),
            },
            {
                'location_id': destination_location.id,
                'product_id': rec.product_id.id,
                'quantity': picking_line.transfer_qty,
            },
        ]
        for params in quant_params:
            stock_quant = self.env['stock.quant'].search(
                [('location_id', '=', params['location_id'])], limit=1)
            if stock_quant:
                stock_quant.quantity += params['quantity']
            else:
                stock_quant_vals = {
                    'location_id': params['location_id'],
                    'product_id': params['product_id'],
                    'quantity': params['quantity'],
                }
                self.env['stock.quant'].sudo().create(stock_quant_vals)

    @ api.depends('contract_id')
    def _compute_company_name(self):
        for rec in self:
            rec.source_company = rec.contract_id.location_id.sudo().company_id.name
            rec.delivery_company = rec.contract_id.location_dest_id.sudo().company_id.name

    @ api.depends('contract_id', 'state')
    def _compute_available_qty(self):
        for rec in self:
            picking_lines = self.env['stock.picking.line'].search(
                [('picking_id', '=', rec.id), ('state', '=', 'moved')])
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
    transfer_qty = fields.Float(
        'Demand',
        digits='Product Unit of Measure',
        default=0.0, required=True)
    note = fields.Html('Note')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('moved', 'Moved'),
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
