{
    # Theme information

    'name': 'Tracking',
    'category': 'Inventory',
    'summary': 'Product transfort tracking managment module',
    'version': '1.0.0',
    'license': 'OPL-1',
    'depends': ['product', 'mail', 'web'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',

        'data/stock_data.xml',
        'data/ir_cron_data.xml',

        'views/menu_view.xml',
        'views/product_view.xml',
        'views/stock_picking_view.xml',
        'views/stock_warehouse_view.xml',
        'views/stock_location_view.xml',
        'views/stock_move_view.xml',
        'views/stock_quant_view.xml',
        'views/stock_contract_view.xml',
        'views/stock_vehicle_view.xml',
        'views/res_company_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            '/tracking/static/src/xml/base.xml',
            "/tracking/static/src/scss/sidemenu.scss",
        ]
    },


    # Author
    'author': 'ErdenesIT',
    'website': 'www.erdenesit.mn',
    'maintainer': 'Samdaa',

    # Technical
    'installable': True,
    'auto_install': False,
}
