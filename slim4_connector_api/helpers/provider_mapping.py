DEFAULT_EXPORT_PROVIDER = 'slim4.export.provider'

# Add an entry only when an interface actually needs its own provider.
PROVIDER_BY_INTERFACE = {
    'S4Import_PurchaseOrder': 'slim4.export.provider.purchase.order',
    'S4Import_Logistics': 'slim4.export.provider.logistics',
    'S4Import_ConfirmedDemand': 'slim4.export.provider.confirmed.demand',
    'S4Import_Suppliers': 'slim4.export.provider.suppliers',
    'S4Import_BillOfMaterial': 'slim4.export.provider.bill.of.material',
}


def get_export_provider(env, interface):
    """Return the provider configured for an interface, or the generic one."""
    interface.ensure_one()
    provider_name = PROVIDER_BY_INTERFACE.get(
        interface.technical_name,
        DEFAULT_EXPORT_PROVIDER,
    )
    return env[provider_name]
