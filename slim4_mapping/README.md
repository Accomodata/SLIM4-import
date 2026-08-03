# Slim4 Mapping Configuration

This module adds a configuration screen to prepare the mappings between Odoo and Slim4.

## What the module does

From the menu:

Slim4 > Configuration > Interfaces

users can review each Slim4 interface, for example:

- Article Filter
- Article Code Master
- Logistics
- Purchase Order
- Confirmed Demand
- Stock Details
- Transactions

For each interface, users can see:

- the Odoo model used as source;
- the domain applied to the data;
- the number of matching records;
- the Slim4 fields to fill;
- the planned mapping for each field;
- the points still requiring validation.

## Available actions

The module adds a few useful actions:

- **Refresh Count**: counts the Odoo records matching the interface configuration;
- **Open Matching Records**: opens the matching Odoo records directly;
- **Validate Mapping**: checks that the basic mapping configuration is coherent.
