from odoo import _, api, fields, models
import requests
from datetime import datetime, timedelta
import pytz


class Contract(models.Model):
    _name = 'stock.contract'
    _description = "Stock Contract"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id'

    name = fields.Char('Name')
    contract_id = fields.Char('Contract ID', related='name')
    reference_id = fields.Char('Ref ID')
    sequence = fields.Integer('Sequence', default=10)
    company_id = fields.Many2one(
        'res.company', 'Company', related='location_id.company_id')
    product_id = fields.Many2one('product.product', 'Product')
    state = fields.Selection([
        ('draft', 'New'),
        ('open', 'Running'),
        ('close', 'Expired'),
        ('cancel', 'Cancelled')
    ], string='Status', group_expand='_expand_states', copy=False,
        tracking=True, help='Status of the contract', default='draft')
    trade_date = fields.Datetime('Trade Date', default=fields.Datetime.now)
    delivery_date = fields.Date(
        'Delivery Date', default=fields.Datetime.now)
    source_company_id = fields.Many2one('res.company',
                                        'Source Company', related='location_id.company_id')
    symbol = fields.Char('Symbol')
    destination_company_id = fields.Many2one('res.company', 'Destination Company',
                                             related='location_dest_id.company_id')
    active = fields.Boolean(default=True)
    location_id = fields.Many2one(
        'stock.location', 'Source Location', domain=[('usage', '=', 'internal')])
    location_dest_id = fields.Many2one(
        'stock.location', 'Destination Location', domain=[('usage', '=', 'internal')])
    total_qty = fields.Integer(
        'Contract Amount', compute='_compute_qty', store=True)
    delivered_qty = fields.Integer(
        'Delivered Quantity', compute='_compute_qty', store=True)
    incoming_qty = fields.Integer(
        'Incoming Quantity', compute='_compute_qty', store=True)
    available_qty = fields.Integer(
        'Available Quantity', compute='_compute_qty', store=True)
    depreciation_qty = fields.Integer(
        'Depreciation Quantity', compute='_compute_qty', store=True)
    surplus = fields.Integer(
        'Surplus Quantity', compute='_compute_qty', store=True)
    amount = fields.Float('Amount')
    contract_line_ids = fields.One2many(
        'stock.contract.line', 'contract_id', string="Contract Lines", copy=True)
    parent_company_id = fields.Many2one(
        'res.company', 'Company', related='company_id.parent_id')

    _sql_constraints = [
        ('name_uniq', 'unique (name)',
         "Contract already exists.")
    ]

    @ api.depends('amount', 'contract_line_ids')
    def _compute_qty(self):
        for rec in self:
            rec.total_qty = rec.amount * 6400
            delivered_contract_lines = self.env['stock.contract.line'].search(
                [('contract_id', '=', rec.id), ('location_id', '=', rec.location_dest_id.id)])
            income_contract_lines = self.env['stock.contract.line'].search(
                [('contract_id', '=', rec.id), ('location_id', 'not in', [rec.location_dest_id.id, rec.location_id.id])])
            rec.incoming_qty = sum(
                income_contract_lines.mapped('quantity'))
            rec.delivered_qty = sum(
                delivered_contract_lines.mapped('quantity'))
            delivered_picking = self.env['stock.picking'].search(
                [('contract_id', '=', rec.id), ('company_type', '=', 'mining')], limit=1)
            surplus_or_depreciation = sum(
                delivered_picking.picking_line_ids.mapped('transfer_qty')) - (rec.delivered_qty + rec.incoming_qty)
            if surplus_or_depreciation > 0:
                rec.depreciation_qty = surplus_or_depreciation
            elif surplus_or_depreciation < 0:
                rec.surplus = abs(surplus_or_depreciation)
            else:
                rec.depreciation_qty = 0
                rec.surplus = 0
            rec.available_qty = rec.total_qty - (sum(
                delivered_contract_lines.mapped('quantity')) + surplus_or_depreciation + rec.incoming_qty)

    def _get_contract_info(self):
        session = requests.Session()

        # Login
        login_url = 'http://demo.erdenesit.mn:9000/login'
        payload = {
            'username': 'admin01',
            'password': 'a'
        }
        response = session.post(login_url, data=payload)

        # Check login response status code
        if response.status_code == 200:

            # Get contract info using the same session object
            trade_url = 'http://demo.erdenesit.mn:8070/ts/trade/public/all'
            response = session.get(trade_url)

            trade_url = 'http://demo.erdenesit.mn:8070/ts/trade/public/all'
            response = session.get(trade_url)

            mining_company = self.env['res.company'].search(
                [('company_type', '=', 'mining')], order='id ASC', limit=1)
            warehouse_company = self.env['res.company'].search(
                [('company_type', '=', 'warehouse')], order='id ASC', limit=1)

            location_id = self.env['stock.location'].search(
                [('company_id', '=', mining_company.id), ('usage', '=', 'internal')], order='id ASC', limit=1)
            location_dest_id = self.env['stock.location'].search(
                [('company_id', '=', warehouse_company.id), ('usage', '=', 'internal')], order='id ASC', limit=1)
            product_id = self.env['product.product'].search(
                [('name', '=', 'Коксжих')], order='id ASC', limit=1)

            if response.status_code == 200:
                data = response.json()
                for trade in data:
                    contractObj = self.env['stock.contract'].search(
                        [('name', '=', trade['id'])], limit=1)
                    if not contractObj:
                        date = datetime.strptime(
                            trade['date'], '%Y-%m-%dT%H:%M:%S.%f%z')
                        tradeDateTime = date.replace(
                            tzinfo=None) - timedelta(hours=8)
                        deliveryDate = tradeDateTime.date()
                        stock_contract_vals = {
                            'reference_id': trade['id'],
                            'amount': trade['amount'],
                            'product_id': product_id.id,
                            'symbol': trade['instrument'],
                            'location_id': location_id.id,
                            'location_dest_id': location_dest_id.id,
                            'trade_date':  tradeDateTime,
                            'delivery_date':  deliveryDate.replace(month=date.month+1),
                            'total_qty': 6400 * trade['amount'],
                        }
                        self.env['stock.contract'].sudo().create(
                            stock_contract_vals)

    @ api.model_create_multi
    def create(self, vals_list):
        contracts = super().create(vals_list)
        for contract, vals in zip(contracts, vals_list):
            now = fields.Date.today().strftime('%y%m%d')
            prefix = f'CT-{now}-'
            sequence = self.env['ir.sequence'].sudo().search([
                ('code', '=', 'stock.contract'),
                ('prefix', 'like',  prefix)
            ], limit=1)
            if not sequence:
                sequence = self.env['ir.sequence'].sudo().create({
                    'name': _('Sequence'),
                    'code': 'stock.contract',
                    'padding': 2,
                    'prefix': prefix,
                    'number_increment': 1,
                    'company_id': vals.get('company_id'),
                })
            contract.write({'name': sequence.next_by_id()})
        return contracts

    def _get_security_by_rule_action(self):
        return {}


class ContractLine(models.Model):
    _name = 'stock.contract.line'
    _description = "Stock Contract Line"

    contract_id = fields.Many2one(
        'stock.contract', 'Contract')
    product_id = fields.Many2one(
        'product.product', 'Product')
    product_tmpl_id = fields.Many2one(
        'product.template', string='Product Template',
        related='product_id.product_tmpl_id')
    product_uom_id = fields.Many2one(
        'uom.uom', 'Unit',
        readonly=True, related='product_id.uom_id')
    company_id = fields.Many2one(
        related='location_id.company_id', string='Company', store=True, readonly=True)
    location_name = fields.Char('Location', related='location_id.name')
    location_id = fields.Many2one(
        'stock.location', 'Location', auto_join=True, ondelete='restrict', required=True, index=True)
    quantity = fields.Float(
        'Quantity',
        help='Quantity of products in this quant, in the default unit of measure of the product',
        readonly=True, digits='Product Unit of Measure')
