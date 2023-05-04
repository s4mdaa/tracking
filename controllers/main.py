from odoo import http
from odoo.http import request
from odoo.addons.auth_signup.controllers.main import AuthSignupHome


class CustomAuthSignupHome(AuthSignupHome):
    @http.route('/web/login', type='http', auth="none")
    def web_login(self, redirect=None, **kwargs):
        response = super(CustomAuthSignupHome, self).web_login(
            redirect=redirect, **kwargs)
        if not request.session.uid:
            return response
        else:
            print("SSSSSSSSSSSSSSSSSSSSSSSSSSSS")
            return request.redirect('/web#action=191&model=stock.picking&view_type=list&cids=1&menu_id=113')
