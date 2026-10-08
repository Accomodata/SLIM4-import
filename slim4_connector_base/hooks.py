from odoo.exceptions import UserError


def pre_init_hook(env):
    """Prevent installation when internal references are duplicated."""
    env.cr.execute("""
        SELECT default_code, COUNT(*)
          FROM product_product
          WHERE active IS TRUE
          AND default_code IS NOT NULL
          AND default_code != ''
         GROUP BY default_code
        HAVING COUNT(*) > 1
         LIMIT 10
    """)
    duplicates = env.cr.fetchall()

    if duplicates:
        details = '\n'.join(
            f'- {default_code}: {product_count} products'
            for default_code, product_count in duplicates
        )
        raise UserError(
            env._(
                'Slim4 Connector Base cannot be installed because some '
                'Internal References are duplicated:\n%(duplicates)s\n\n'
                'Make these references unique before installing the module.',
                duplicates=details,
            ),
        )


def initialize_warehouse_configs(cr):
    cr.execute("""
        INSERT INTO slim4_warehouse_config (
            product_id,
            warehouse_id,
            slim4_stocked_item
        )
        SELECT
            p.id,
            w.id,
            'y'
        FROM product_product p
        JOIN product_template pt ON pt.id = p.product_tmpl_id
        CROSS JOIN stock_warehouse w
        WHERE p.active
          AND w.active
          AND (
              pt.company_id IS NULL
              OR pt.company_id = w.company_id
          )
          AND NOT EXISTS (
              SELECT 1
              FROM slim4_warehouse_config config
              WHERE config.product_id = p.id
                AND config.warehouse_id = w.id
          )
    """)


def initialize_primary_suppliers(env):
    """Use matching suppliers as the initial Slim4 supplier selection."""
    products = env['product.product'].with_context(active_test=False).search([
        ('slim4_primary_supplier_ids', '=', False),
        ('slim4_matching_supplier_ids', '!=', False),
    ])
    for product in products:
        product.slim4_primary_supplier_ids = product.slim4_matching_supplier_ids[:1]


def post_init_hook(env):
    env.flush_all()
    initialize_warehouse_configs(env.cr)
    env.invalidate_all()
    initialize_primary_suppliers(env)
