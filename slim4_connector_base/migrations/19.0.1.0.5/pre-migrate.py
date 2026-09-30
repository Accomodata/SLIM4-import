def migrate(cr, version):
    # Keep the oldest active product for each non-empty reference.
    cr.execute("""
        WITH ranked_products AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY default_code
                    ORDER BY id
                ) AS occurrence
            FROM product_product
            WHERE active = TRUE
              AND default_code IS NOT NULL
              AND default_code != ''
        )
        UPDATE product_product AS product
           SET active = FALSE,
               write_date = NOW()
          FROM ranked_products AS ranked
         WHERE product.id = ranked.id
           AND ranked.occurrence > 1
        RETURNING product.product_tmpl_id
    """)
    template_ids = list({row[0] for row in cr.fetchall()})

    # Archive affected templates only when no active variant remains.
    if template_ids:
        cr.execute("""
            UPDATE product_template AS template
               SET active = FALSE,
                   write_date = NOW()
             WHERE template.id = ANY(%s)
               AND template.active = TRUE
               AND NOT EXISTS (
                   SELECT 1
                     FROM product_product AS product
                    WHERE product.product_tmpl_id = template.id
                      AND product.active = TRUE
               )
        """, (template_ids,))
