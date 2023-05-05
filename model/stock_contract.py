from odoo import _, api, fields, models
import requests
from datetime import datetime, timedelta
import pytz


class Contract(models.Model):
    _name = 'stock.contract'
    _description = "Stock Contract"
    _order = 'sequence, id'

    name = fields.Char('Name')
    reference = fields.Char('Reference')
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
    date = fields.Datetime('Date', default=fields.Datetime.now)
    source_company_id = fields.Many2one('res.company', 'Source Company')
    auction = fields.Char('Auction')
    price = fields.Float('Price')
    destination_company_id = fields.Many2one(
        'res.company', 'Destination Company')
    active = fields.Boolean(default=True)
    location_id = fields.Many2one(
        'stock.location', 'Source Location', domain=[('usage', '=', 'internal')])
    location_dest_id = fields.Many2one(
        'stock.location', 'Destination Location', domain=[('usage', '=', 'internal')])
    total_qty = fields.Integer(
        'Quantity', compute='_compute_total_qty', store=True)
    amount = fields.Float('Amount')
    contract_line_ids = fields.One2many(
        'stock.contract.line', 'contract_id', string="Contract Lines", copy=True)
    parent_company_id = fields.Many2one(
        'res.company', 'Company', related='company_id.parent_id')

    _sql_constraints = [
        ('name_uniq', 'unique (name)',
         "Contract already exists.")
    ]

    @ api.depends('amount')
    def _compute_total_qty(self):
        for rec in self:
            rec.total_qty = rec.amount * 6400

    def _get_contract_info(self):
        session = requests.Session()

        # Login
        login_url = 'http://spectre-dev.online:9000/login'
        payload = {
            'username': 'admin01',
            'password': 'a'
        }
        response = session.post(login_url, data=payload)

        # Check login response status code
        if response.status_code == 200:

            # Get contract info using the same session object
            trade_url = 'http://spectre-dev.online:8080/ts/trade/public/all'
            response = session.get(trade_url)

            trade_url = 'http://spectre-dev.online:8080/ts/trade/public/all'
            response = session.get(trade_url)

            if response.status_code == 200:
                data = response.json()
                for trade in data:
                    contractObj = self.env['stock.contract'].search(
                        [('name', '=', trade['id'])], limit=1)
                    if not contractObj:
                        date = datetime.strptime(
                            trade['date'], '%Y-%m-%dT%H:%M:%S.%f%z')
                        tradeDate = date.replace(
                            tzinfo=None) - timedelta(hours=8)
                        stock_contract_vals = {
                            'reference': trade['id'],
                            'amount': trade['amount'],
                            'price': trade['value'],
                            'auction': trade['auction'],
                            'date':  tradeDate,
                            'total_qty': 6400 * trade['amount'],
                        }
                        self.env['stock.contract'].sudo().create(
                            stock_contract_vals)

    @api.model_create_multi
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
            stock_contract_line_source_vals = {
                'location_id': contract.location_id.id,
                'product_id': contract.product_id.id,
                'quantity': contract.total_qty,
                'contract_id': contract.id
            }
            self.env['stock.contract.line'].sudo().create(
                stock_contract_line_source_vals)
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
    location_id = fields.Many2one(
        'stock.location', 'Location', auto_join=True, ondelete='restrict', required=True, index=True)
    quantity = fields.Float(
        'Quantity',
        help='Quantity of products in this quant, in the default unit of measure of the product',
        readonly=True, digits='Product Unit of Measure')
