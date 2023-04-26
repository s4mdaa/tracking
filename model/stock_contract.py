from odoo import fields, models
import requests
from datetime import datetime, timedelta
import pytz


class Contract(models.Model):
    _name = 'stock.contract'
    _description = "Stock Contract"
    _order = 'sequence, id'

    name = fields.Char('Name')
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
    date = fields.Datetime('Date')
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
    total_qty = fields.Integer('Quantity')
    amount = fields.Float('Amount')

    _sql_constraints = [
        ('name_uniq', 'unique (name)',
         "Contract already exists.")
    ]

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
                            'name': trade['id'],
                            'amount': trade['amount'],
                            'price': trade['value'],
                            'auction': trade['auction'],
                            'date':  tradeDate,
                            'total_qty': 6400 * trade['amount'],
                        }
                        self.env['stock.contract'].sudo().create(
                            stock_contract_vals)
