# Slim4 Connector API - Inbound

Provides the `/slim4/api/v1/orders` endpoint through which Slim4 sends its order proposals to Odoo, storing each line as an inbound message. A scheduled action (or a manual action) then turns these messages into draft purchase orders, grouped per supplier and warehouse.

See the [full documentation](../slim4_connector_base/README.md) in `slim4_connector_base`.
