from odoo import _, api, fields, models
import base64


class Company(models.Model):
    _inherit = "res.company"

    def _default_confirmation_mail_template(self):
        try:
            return self.env.ref('stock.mail_template_data_delivery_confirmation').id
        except ValueError:
            return False

    # used for resupply routes between warehouses that belong to this company
    company_type = fields.Selection(
        [('transport', 'Transport'), ('mining', 'Mining'), ('warehouse', 'Warehouse')], "Company Type", required=True)
    internal_transit_location_id = fields.Many2one(
        'stock.location', 'Internal Transit Location', ondelete="restrict", check_company=True)
    stock_move_email_validation = fields.Boolean(
        "Email Confirmation picking", default=False)
    stock_mail_confirmation_template_id = fields.Many2one('mail.template', string="Email Template confirmation picking",
                                                          domain="[('model', '=', 'stock.picking')]",
                                                          default=_default_confirmation_mail_template,
                                                          help="Email sent to the customer once the order is done.")
    annual_inventory_month = fields.Selection([
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], string='Annual Inventory Month',
        default='12',
        help="Annual inventory month for products not in a location with a cyclic inventory date. Set to no month if no automatic annual inventory.")
    annual_inventory_day = fields.Integer(
        string='Day of the month', default=31,
        help="""Day of the month when the annual inventory should occur. If zero or negative, then the first day of the month will be selected instead.
        If greater than the last day of a month, then the last day of the month will be selected instead.""")

    @api.model
    def create_company_user(self):
        tracking_ett_user_group = self.env.ref(
            'tracking.group_tracking_ett_user')
        tracking_tsh_user_group = self.env.ref(
            'tracking.group_tracking_tsh_user')
        tracking_admin_group = self.env.ref('tracking.group_tracking_admin')
        companies = self.env['res.company'].search(
            [('company_type', 'in', ('mining', 'warehouse'))])
        with open("../erdenesit/tracking/static/icon/ett_profile.png", "rb") as image_file:
            ett_profile_image = base64.b64encode(image_file.read())
        user_admin = self.env['res.users'].browse(2)
        user_admin.write({'image_1920': ett_profile_image})
        user_admin.write({'groups_id': [(4, tracking_admin_group.id)]})
        for company in companies:
            image_1920 = False
            if company.company_type == 'mining':
                login = 'ganzo@garuda.mn'
                name = 'Д.Ганзориг'
                company_ids = [(6, 0, [company.id])]
                company_id = company.id
                groups_id = [(4, tracking_ett_user_group.id),
                             (4, self.env.ref('base.group_user').id)]
                image_1920 = ett_profile_image
            else:
                login = 'amarsanaa@garuda.mn'
                name = 'С.Амарсанаа'
                company_id = company.id
                groups_id = [(4, tracking_tsh_user_group.id),
                             (4, self.env.ref('base.group_user').id)]
                company_ids = [(6, 0, [company.id])]
            self.env['res.users'].create({
                'name': name,
                'login': login,
                'password': '123',
                'company_ids': company_ids,
                'company_id': company_id,
                'groups_id': groups_id,
                'image_1920': image_1920,
            })

    def _create_transit_location(self):
        '''Create a transit location with company_id being the given company_id. This is needed
           in case of resuply routes between warehouses belonging to the same company, because
           we don't want to create accounting entries at that time.
        '''
        parent_location = self.env.ref(
            'tracking.stock_location_locations_transit', raise_if_not_found=False)
        for company in self:
            location = self.env['stock.location'].create({
                'name': company.name,
                'usage': 'transit',
                'location_id': parent_location and parent_location.id or False,
                'company_id': company.id,
            })

            company.write({'internal_transit_location_id': location.id})

    def _create_inventory_loss_location(self):
        parent_location = self.env.ref(
            'tracking.stock_location_locations_virtual', raise_if_not_found=False)
        for company in self:
            inventory_loss_location = self.env['stock.location'].create({
                'name': 'Inventory adjustment',
                'usage': 'inventory',
                'location_id': parent_location.id,
                'company_id': company.id,
            })

    def _create_production_location(self):
        parent_location = self.env.ref(
            'tracking.stock_location_locations_virtual', raise_if_not_found=False)
        for company in self:
            production_location = self.env['stock.location'].create({
                'name': 'Production',
                'usage': 'production',
                'location_id': parent_location.id,
                'company_id': company.id,
            })

    def _create_scrap_location(self):
        parent_location = self.env.ref(
            'tracking.stock_location_locations_virtual', raise_if_not_found=False)
        for company in self:
            scrap_location = self.env['stock.location'].create({
                'name': 'Scrap',
                'usage': 'inventory',
                'location_id': parent_location.id,
                'company_id': company.id,
                'scrap_location': True,
            })

    def _create_scrap_sequence(self):
        scrap_vals = []
        for company in self:
            scrap_vals.append({
                'name': '%s Sequence scrap' % company.name,
                'code': 'stock.scrap',
                'company_id': company.id,
                'prefix': 'SP/',
                'padding': 5,
                'number_next': 1,
                'number_increment': 1
            })
        if scrap_vals:
            self.env['ir.sequence'].create(scrap_vals)

    @api.model
    def create_missing_warehouse(self):
        """ This hook is used to add a warehouse on existing companies
        when module stock is installed.
        """
        company_ids = self.env['res.company'].search([])
        company_with_warehouse = self.env['stock.warehouse'].with_context(
            active_test=False).search([]).mapped('company_id')
        company_without_warehouse = company_ids - company_with_warehouse
        for company in company_without_warehouse:
            self.env['stock.warehouse'].create({
                'name': company.name,
                'code': company.name[:5],
                'company_id': company.id,
                'partner_id': company.partner_id.id,
            })

    @api.model
    def create_missing_transit_location(self):
        company_without_transit = self.env['res.company'].search(
            [('internal_transit_location_id', '=', False)])
        company_without_transit._create_transit_location()

    @api.model
    def create_missing_inventory_loss_location(self):
        company_ids = self.env['res.company'].search([])
        inventory_loss_product_template_field = self.env['ir.model.fields']._get(
            'product.template', 'property_stock_inventory')
        companies_having_property = self.env['ir.property'].sudo().search(
            [('fields_id', '=', inventory_loss_product_template_field.id), ('res_id', '=', False)]).mapped('company_id')
        company_without_property = company_ids - companies_having_property
        company_without_property._create_inventory_loss_location()

    @api.model
    def create_missing_production_location(self):
        company_ids = self.env['res.company'].search([])
        production_product_template_field = self.env['ir.model.fields']._get(
            'product.template', 'property_stock_production')
        companies_having_property = self.env['ir.property'].sudo().search(
            [('fields_id', '=', production_product_template_field.id), ('res_id', '=', False)]).mapped('company_id')
        company_without_property = company_ids - companies_having_property
        company_without_property._create_production_location()

    @api.model
    def create_missing_scrap_location(self):
        company_ids = self.env['res.company'].search([])
        companies_having_scrap_loc = self.env['stock.location'].search(
            [('scrap_location', '=', True)]).mapped('company_id')
        company_without_property = company_ids - companies_having_scrap_loc
        company_without_property._create_scrap_location()

    @api.model
    def create_missing_scrap_sequence(self):
        company_ids = self.env['res.company'].search([])
        company_has_scrap_seq = self.env['ir.sequence'].search(
            [('code', '=', 'stock.scrap')]).mapped('company_id')
        company_todo_sequence = company_ids - company_has_scrap_seq
        company_todo_sequence._create_scrap_sequence()

    def _create_per_company_locations(self):
        self.ensure_one()
        self._create_transit_location()
        self._create_inventory_loss_location()
        self._create_production_location()
        self._create_scrap_location()

    def _create_per_company_sequences(self):
        self.ensure_one()
        self._create_scrap_sequence()

    def _create_per_company_picking_types(self):
        self.ensure_one()

    def _create_per_company_rules(self):
        self.ensure_one()

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        for company in companies:
            company.sudo()._create_per_company_locations()
            company.sudo()._create_per_company_sequences()
            company.sudo()._create_per_company_picking_types()
            company.sudo()._create_per_company_rules()
        self.env['stock.warehouse'].sudo().create([{
            'name': company.name,
            'code': self.env.context.get('default_code') or company.name[:5],
            'company_id': company.id,
            'partner_id': company.partner_id.id
        } for company in companies])
        return companies

    def _get_security_by_rule_action(self):
        return {}
