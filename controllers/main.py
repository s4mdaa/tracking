from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError
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

            # user = request.env.user
            # management_menu = request.env.ref('base.menu_management')
            # administration_menu = request.env.ref(
            #         'base.menu_administration')
            # if user.login == 'superadmin':
            #     management_menu.sudo().write({'active': True})
            #     administration_menu.sudo().write({'active': True})
            # else:
            #     management_menu.sudo().write({'active': False})
            #     administration_menu.sudo().write({'active': False})
            return request.redirect('/web#model=stock.picking&view_type=list')

    @http.route('/contracts/create', type='http', auth='user', website=True, sitemap=False)
    def _get_trade_info(self):
        contract_obj = request.env['stock.contract']
        contract_obj._get_contract_info()
        return request.redirect('/scenario')

    @http.route('/transfer/create/ett', type='http', auth='user', website=True, sitemap=False)
    def create_transfer_delivery(self, company_id=False, contract_id=False, scheduled_date=False):
        if company_id == False:
            scheduled_date = datetime.now()
            company_id = request.env.user.company_id.id
            contract_id = request.env['stock.contract'].search(
                [('company_id', '=', company_id)], order='id ASC', limit=1)
            transfer_qty = 70
            stock_vehicles = request.env['stock.vehicle'].search([
                ('company_id.parent_id', '=', company_id)])
        else:
            stock_vehicles = request.env['stock.vehicle'].search([
                ('company_id.parent_id', '=', company_id)])
            transfer_qty = contract_id.total_qty/len(stock_vehicles)
        picking_id = request.env['stock.picking'].create({
            'contract_id': contract_id.id,
            'company_id': company_id,
            'scheduled_date': scheduled_date
        })
        is_first_iteration = True

        for stock_vehicle in stock_vehicles:
            if is_first_iteration:
                is_first_iteration = False
            else:
                # add two seconds to the scheduled date
                scheduled_date += timedelta(seconds=2)

            request.env['stock.picking.line'].create({
                'vehicle_id': stock_vehicle.id,
                'transfer_qty': transfer_qty,
                'picking_id': picking_id.id,
                'scheduled_date': scheduled_date,
            })
        picking_id.action_done()
        return request.redirect('/scenario')

    @ http.route('/transfer/create/tsh', type='http', auth='user', website=True, sitemap=False)
    def create_transfer_receipt(self, company_id=False, contract_id=False, transfer_qty=0, scheduled_date=False):
        if company_id == False:
            scheduled_date = datetime.now() + timedelta(seconds=30)
            company_id = request.env.user.company_id.id
            contract_id = request.env['stock.contract'].search(
                [('company_id', '=', company_id)], order='id ASC', limit=1)
            transfer_qty = 70
            stock_vehicles = request.env['stock.vehicle'].search([
                ('company_id.parent_id', '=', company_id)])
        else:
            stock_vehicles = request.env['stock.vehicle'].search([
                ('company_id.parent_id', '=', company_id)])
            transfer_qty = contract_id.total_qty/len(stock_vehicles)
        picking_id = request.env['stock.picking'].create({
            'contract_id': contract_id.id,
            'company_id': contract_id.location_dest_id.company_id.id,
            'picking_type': 'receipt',
            'scheduled_date': scheduled_date
        })
        is_first_iteration = True

        for stock_vehicle in stock_vehicles:
            if is_first_iteration:
                is_first_iteration = False
            else:
                # add two seconds to the scheduled date
                scheduled_date += timedelta(seconds=2)

            request.env['stock.picking.line'].create({
                'vehicle_id': stock_vehicle.id,
                'transfer_qty': transfer_qty,
                'picking_id': picking_id.id,
                'scheduled_date': scheduled_date,
            })
        picking_id.action_done()
        return request.redirect('/scenario')

    @ http.route('/remove_datas', type='http', auth='user', website=True, sitemap=False)
    def remove_datas(self):
        stock_pickings = request.env['stock.picking'].sudo().search([])
        stock_pickings.unlink()
        stock_moves = request.env['stock.move'].sudo().search([])
        stock_moves.unlink()
        stock_quants = request.env['stock.quant'].sudo().search([])
        stock_quants.unlink()
        stock_contracts = request.env['stock.contract'].sudo().search([
        ])
        stock_contracts.unlink()
        stock_contract_lines = request.env['stock.contract.line'].sudo().search([
        ])
        stock_contract_lines.unlink()
        return request.redirect('/scenario')

    @http.route(['/scenario', '/scenarios'], type='http', auth='user', website=True, sitemap=False)
    def scenario(self):
        # Check if the current user has the 'tracking.group_tracking_admin' group
        if not request.env.user.has_group('tracking.group_tracking_admin'):
            raise AccessError("You are not authorized to access this page.")

        current_url = request.httprequest.path
        if current_url == '/scenarios':
            return request.redirect('/scenario')

        stock_pickings = request.env['stock.picking'].sudo().search([])
        stock_moves = request.env['stock.move'].sudo().search([])
        stock_quants = request.env['stock.quant'].sudo().search([])
        stock_contracts = request.env['stock.contract'].sudo().search([])
        values = {
            'stock_pickings': stock_pickings,
            'stock_moves': stock_moves,
            'stock_quants': stock_quants,
            'stock_contracts': stock_contracts,
        }
        return request.render('tracking.scenario_page', values)

    @ http.route('/to_produce_mining_company', type='http', auth='user', website=True, sitemap=False)
    def to_produce_mining_company(self, company_id=False, scheduled_date=False):
        if company_id == False:
            company_id = request.env.user.company_id.id
            scheduled_date = datetime.now()
        location_source = request.env['stock.location'].sudo().search(
            [('company_id', '=', company_id), ('usage', '=', 'production')], limit=1)
        location_destination = request.env['stock.location'].sudo().search(
            [('company_id', '=', company_id), ('usage', '=', 'internal')], limit=1)
        product_id = request.env['product.product'].search(
            [('company_id', '=', company_id)], order='id ASC', limit=1)
        default_lang = request.env['res.lang'].search(
            [('active', '=', True)])
        if location_destination.company_id.name == 'Энержи Ресурс ХХК':
            reference = 'Энержи Ресурс-Production'
            if default_lang.iso_code != 'en':
                reference = 'Энержи Ресурс-Үйлдвэрлэл'
        if location_destination.company_id.name == 'Эрдэнэс Тавантолгой ХК':
            reference = 'Эрдэнэс Тавантолгой ХК-Production'
            if default_lang.iso_code != 'en':
                reference = 'Эрдэнэс Тавантолгой ХК-Үйлдвэрлэл'
        if location_destination.company_id.name == 'Тавантолгой ХК':
            reference = 'Тавантолгой ХК-Production'
            if default_lang.iso_code != 'en':
                reference = 'Тавантолгой ХК-Үйлдвэрлэл'
        stock_move_vals = {
            'name': str(location_source.name) + '-' + str(location_destination.name),
            'location_id': location_source.id,
            'location_dest_id': location_destination.id,
            'product_id': product_id.id,
            'product_qty': 100000,
            'product_uom': product_id.uom_id.id,
            'description_picking': product_id.name,
            'company_id': location_source.company_id.id,
            'date': scheduled_date,
            'state': 'moved',
            'reference': reference
        }
        request.env['stock.move'].sudo().create(stock_move_vals)
        stock_quant_vals = {
            'location_id': location_destination.id,
            'product_id': product_id.id,
            'quantity': 100000,
            'scheduled_date': datetime.now()
        }
        request.env['stock.quant'].sudo().create(stock_quant_vals)
        return request.redirect('/scenario')

    @ http.route('/create_big_data', type='http', auth='user', website=True, sitemap=False)
    def create_big_data(self):
        # create contract
        companies = request.env['res.company'].search(
            [('name', 'in', ('Энержи Ресурс ХХК', 'Тавантолгой ХК'))])
        amount = 2
        first_loop = True
        for i in range(2):
            index = 2
            for company in companies:
                scheduled_date = datetime.now() - timedelta(weeks=4)
                if i != 1:
                    self.to_produce_mining_company(
                        company_id=company.id, scheduled_date=scheduled_date - timedelta(seconds=2))
                location_dest_ids = request.env['stock.location'].sudo().search(
                    [('usage', '=', 'internal'), ('company_id.company_type', '=', 'warehouse'), ('company_id.parent_id', '=', company.id)])
                for location_dest_id in location_dest_ids:
                    if i == 1 and len(location_dest_ids) != 1:
                        scheduled_date += timedelta(weeks=4)
                    if i == 1 and len(location_dest_ids) == 1:
                        scheduled_date += timedelta(weeks=12)
                    product_id = request.env['product.product'].sudo().search(
                        [('company_id', '=', company.id)], limit=1)
                    location_id = request.env['stock.location'].sudo().search(
                        [('usage', '=', 'internal'), ('company_id', '=', company.id)], limit=1)
                    delivery_date = scheduled_date.date()
                    stock_contract_vals = {
                        'reference_id': f'3768586c-8ccc-46ff-b0f5-8633e509fc{company.id}{amount}',
                        'amount': amount,
                        'product_id': product_id.id,
                        'symbol': f'20240{index}COAL',
                        'location_id': location_id.id,
                        'location_dest_id': location_dest_id.id,
                        'trade_date': scheduled_date,
                        'delivery_date': delivery_date.replace(month=scheduled_date.month + 1),
                        'total_qty': 6400 * amount,
                    }
                    contract_id = request.env['stock.contract'].sudo().create(
                        stock_contract_vals)
                    amount += 1
                    if scheduled_date + timedelta(weeks=3) < datetime.now():
                        scheduled_date += timedelta(days=1)
                    # create transfer
                        if not first_loop:
                            scheduled_date += timedelta(minutes=1)
                        self.create_transfer_delivery(
                            company_id=company.id, contract_id=contract_id, scheduled_date=scheduled_date)
                        scheduled_date += timedelta(seconds=30)
                        self.create_transfer_receipt(
                            company_id=company.id, contract_id=contract_id, scheduled_date=scheduled_date)
                        first_loop = False
                index += 1
        return request.redirect('/scenario')
    
    @http.route(['/dashboard'], type='http', auth='user', website=True, sitemap=False)
    def dashboard(self):
        return request.render('tracking.dashboard_page')
