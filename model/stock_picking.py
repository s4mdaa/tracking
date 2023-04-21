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

    contract_id = fields.Many2one(
        'stock.contract', 'Contract', required=True, readonly=True,
        states={'draft': [('readonly', False)]})

    total_qty = fields.Integer('Quantity', related='contract_id.total_qty', readonly=True,
                               states={'draft': [('readonly', False)]})
    transfer_qty = fields.Integer('Demand', required=True, default=1, readonly=True,
                                  states={'draft': [('readonly', False)]})
    note = fields.Html('Note', readonly=True,
                       states={'draft': [('readonly', False)]})
    location_dest_id = fields.Many2one(
        'stock.location', 'Destination Location', compute='_compute_dest_location', readonly=True,
        states={'draft': [('readonly', False)]})
    location_id = fields.Many2one(
        'stock.location', 'Source Location', compute='_compute_source_location', readonly=True,
        states={'draft': [('readonly', False)]})
    product_id = fields.Many2one(
        related='contract_id.product_id', readonly=True,
        states={'draft': [('readonly', False)]})
    priority = fields.Selection(
        PROCUREMENT_PRIORITIES, string='Priority', default='0',
        help="Products will be reserved first for the transfers with the highest priorities.")
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
        return True

    @api.depends('contract_id')
    def _compute_source_location(self):
        for rec in self:
            rec.location_id = self.contract_id.location_id.id

    @api.depends('contract_id')
    def _compute_dest_location(self):
        for rec in self:
            destination_location = self.env['stock.location'].search(
                [('usage', '=', 'transit')], order='id ASC', limit=1)
            rec.location_dest_id = destination_location.id

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
