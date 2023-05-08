from odoo import http
from odoo.http import request
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from datetime import datetime, timedelta
import requests


class CustomAuthSignupHome(AuthSignupHome):
    @http.route('/web/login', type='http', auth="none")
    def web_login(self, redirect=None, **kwargs):
        response = super(CustomAuthSignupHome, self).web_login(
            redirect=redirect, **kwargs)
        if not request.session.uid:
            return response
        else:
            return request.redirect('/web#model=stock.picking&view_type=list')

    @http.route('/contracts/create', type='http', auth='user', website=True, sitemap=False)
    def _get_trade_info(self):
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
            trade_url = 'http://demo.erdenesit.mn:8070/ts/trade/public/all'
            response = session.get(trade_url)

            trade_url = 'http://demo.erdenesit.mn:8070/ts/trade/public/all'
            response = session.get(trade_url)

            mining_company = request.env['res.company'].search(
                [('company_type', '=', 'mining')], order='id ASC', limit=1)
            warehouse_company = request.env['res.company'].search(
                [('company_type', '=', 'warehouse')], order='id ASC', limit=1)

            location_id = request.env['stock.location'].search(
                [('company_id', '=', mining_company.id), ('usage', '=', 'internal')], order='id ASC', limit=1)
            location_dest_id = request.env['stock.location'].search(
                [('company_id', '=', warehouse_company.id), ('usage', '=', 'internal')], order='id ASC', limit=1)

            if response.status_code == 200:
                data = response.json()
                i = 1
                for trade in data:
                    product_id = request.env['product.product'].search(
                        [('name', '=', 'Нүүрс0'+str(i))], limit=1)
                    if not product_id:
                        i = 1
                        product_id = request.env['product.product'].search(
                            [('name', '=', 'Нүүрс0'+str(i))], limit=1)
                    i += 1
                    contractObj = request.env['stock.contract'].search(
                        [('name', '=', trade['id'])], limit=1)
                    if not contractObj and product_id:
                        date = datetime.strptime(
                            trade['date'], '%Y-%m-%dT%H:%M:%S.%f%z')
                        tradeDateTime = date.replace(
                            tzinfo=None) - timedelta(hours=8)
                        deliveryDate = tradeDateTime.date()
                        stock_contract_vals = {
                            'reference_id': trade['id'],
                            'amount': trade['amount'],
                            'product_id': product_id.id,
                            'price': trade['value'],
                            'symbol': trade['auction'],
                            'location_id': location_id.id,
                            'location_dest_id': location_dest_id.id,
                            'trade_date':  tradeDateTime,
                            'delivery_date':  deliveryDate.replace(month=date.month+1),
                            'total_qty': 6400 * trade['amount'],
                        }
                        request.env['stock.contract'].sudo().create(
                            stock_contract_vals)

    # @http.route('/products/create', type='http', auth='user', website=True, sitemap=False)
    # def _create_products(self):
    #     for i in range(1, 6):
    #         attribute = request.env['product.attribute'].create({
    #             'name': f'Attribute0{i}',
    #         })
    #         attribute_value = request.env['product.attribute.value'].create({
    #             'name': f'Value0{i}',
    #             'attribute_id': attribute.id
    #         })
    #         attribute_line_ids = []
    #         attribute_line_ids.append(
    #             (0, 0, {
    #                 'attribute_id': attribute.id,
    #                 'value_ids': [(6, 0, [attribute_value.id])]
    #             })
    #         )
    #         request.env['product.template'].create({
    #             'name': f'Нүүрс0{i}',
    #             'attribute_line_ids': attribute_line_ids,
    #             'detailed_type': 'product'
    #         })

    @http.route('/transfer/create/ett', type='http', auth='user', website=True, sitemap=False)
    def create_transfer_ett(self):
        contract_id = request.env['stock.contract'].search(
            [], order='id ASC', limit=1)
        stock_vehicles = request.env['stock.vehicle'].search([])
        picking_id = request.env['stock.picking'].create({
            'contract_id': contract_id.id,
            'company_id': request.env.user.company_id.id,
        })
        scheduled_date = datetime.now()  # get the current time

        for stock_vehicle in stock_vehicles:
            # add two seconds to the scheduled date
            scheduled_date += timedelta(seconds=2)
            request.env['stock.picking.line'].create({
                'vehicle_id': stock_vehicle.id,
                'transfer_qty': 100,
                'picking_id': picking_id.id,
                'scheduled_date': scheduled_date,
            })
        picking_id.action_done()

    @http.route('/tranfer/create/tsh', type='http', auth='user', website=True, sitemap=False)
    def create_transfer_tsh(self):
        contract_id = request.env['stock.vehicle'].search(
            [], order='id ASC', limit=1)
        stock_vehicles = request.env['stock.vehicle'].search([])
        picking_id = request.env['stock.picking'].create({
            'contract_id': contract_id.id,
            'company_id': request.env.user.company_id.id,
            'picking_type': 'receipt',
        })
        scheduled_date = datetime.now()  # get the current time

        for stock_vehicle in stock_vehicles:
            # add two seconds to the scheduled date
            scheduled_date += timedelta(seconds=2)
            request.env['stock.picking.line'].create({
                'vehicle_id': stock_vehicle.id,
                'transfer_qty': 100,
                'picking_id': picking_id.id,
                'scheduled_date': scheduled_date,
            })
        picking_id.action_done()

    @http.route('/remove_datas', type='http', auth='user', website=True, sitemap=False)
    def remove_datas(self):
        stock_pickings = request.env['stock.picking'].sudo().search([])
        stock_pickings.unlink()
        stock_moves = request.env['stock.move'].sudo().search([])
        stock_moves.unlink()
        stock_quants = request.env['stock.quant'].sudo().search([])
        stock_quants.unlink()
        stock_contract_lines = request.env['stock.contract.line'].sudo().search([
        ])
        stock_contract_lines.unlink()
