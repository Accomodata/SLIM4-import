from odoo.exceptions import UserError


def pre_init_hook(env):
    """Prevent installation when internal references are duplicated."""
    env.cr.execute("""
        SELECT default_code, COUNT(*)
          FROM product_product
         WHERE default_code IS NOT NULL
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
