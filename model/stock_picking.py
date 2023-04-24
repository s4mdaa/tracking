from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES


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

    contract_id = fields.Many2one(
        'stock.contract', 'Contract', required=True, readonly=True,
        states={'draft': [('readonly', False)]})

    total_qty = fields.Integer(
        'Quantity', related='contract_id.total_qty', readonly=True)
    transfer_qty = fields.Integer('Demand', required=True, default=1, readonly=True,
                                  states={'draft': [('readonly', False)]})
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
        index=True, default=fields.Datetime.now, tracking=True,
        states={'done': [('readonly', True)]})
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
        return True

    @ api.depends('contract_id')
    def _compute_delivery_point(self):
        for rec in self:
            rec.delivery_point_id = rec.contract_id.location_dest_id.id

    @ api.depends('contract_id')
    def _compute_source_location(self):
        for rec in self:
            rec.location_id = rec.contract_id.location_id.id

    @ api.depends('contract_id')
    def _compute_dest_location(self):
        for rec in self:
            destination_location = self.env['stock.location'].search(
                [('usage', '=', 'transit'), ('company_id', '=', rec.location_id.company_id.id)], order='id ASC', limit=1)
            rec.location_dest_id = destination_location.id

    @ api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
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
                    'company_id': self.env.company.id,
                })
            vals['name'] = sequence.next_by_id()
        pickings = super().create(vals_list)
        return pickings
