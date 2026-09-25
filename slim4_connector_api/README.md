# Slim4 Connector API

Exposes the Slim4 interfaces (articles, logistics, suppliers, purchase orders, confirmed demand, stock and transactions)
as REST endpoints under `/slim4/api/v1`, so Slim4 can pull its data from Odoo. The content of each endpoint is driven by
the interface and field-mapping configuration of `slim4_connector_base`.

See the [full documentation](../slim4_connector_base/README.md) in `slim4_connector_base`.
