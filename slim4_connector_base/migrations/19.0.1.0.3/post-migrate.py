

def migrate(cr, version):
    cr.execute("""
        INSERT INTO slim4_warehouse_config (
            product_id,
            warehouse_id,
            slim4_stocked_item
        )
        SELECT
            p.id,
            w.id,
            'n'
        FROM product_product p
        CROSS JOIN stock_warehouse w
        WHERE p.active
          AND w.active
    """)
