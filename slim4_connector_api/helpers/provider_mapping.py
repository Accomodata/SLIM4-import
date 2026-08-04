DEFAULT_EXPORT_PROVIDER = 'slim4.export.provider'

# Add an entry only when an interface actually needs its own provider.
PROVIDER_BY_INTERFACE = {
    'S4Import_PurchaseOrder': 'slim4.export.provider.purchase.order',

}


def get_export_provider(env, interface):
    """Return the provider configured for an interface, or the generic one."""
    interface.ensure_one()
    provider_name = PROVIDER_BY_INTERFACE.get(
        interface.technical_name,
        DEFAULT_EXPORT_PROVIDER,
    )
    return env[provider_name]
