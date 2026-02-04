# Data Folder Overview

This document provides a brief overview of the files located in the `data/` directory. These files appear to be exports representing a data warehouse schema, split into **Dimensions** (descriptive data) and **Facts** (transactional data).

## Dimensions (`dim_*.csv`)

Dimension files contain static or slowly changing reference data.

- **`dim_users.csv`**: Contains user and customer profiles, including contact info, roles, and preferences.
- **`dim_places.csv`**: Represents stores or restaurants. Contains configuration, location, settings, and operational details.
- **`dim_items.csv`**: The master catalog of sellable items (menu items), including prices, descriptions, and settings.
- **`dim_menu_items.csv`**: Likely a specific view or subset of menu items, possibly related to display sorting or ratings.
- **`dim_add_ons.csv`**: Modifiers or extras that can be added to items (e.g., "Extra Cheese").
- **`dim_menu_item_add_ons.csv`**: Junction table defining which add-ons are available for which menu categories.
- **`dim_skus.csv`**: Stock Keeping Units for inventory management. Linked to `dim_items`.
- **`dim_stock_categories.csv`**: Categories for organizing inventory SKUs.
- **`dim_campaigns.csv`**: Definitions of marketing campaigns, discounts, and promotions.
- **`dim_bill_of_materials.csv`**: Recipes or composition rules defining how SKUs are used to build other SKUs or Items.
- **`dim_taxonomy_terms.csv`**: Metadata tags or categorization terms.

## Facts (`fct_*.csv`)

Fact files contain transactional events and historical data.

- **`fct_orders.csv`**: The central sales table. Records individual transactions, totals, status, and customers.
- **`fct_order_items.csv`**: Line items for each order, detailing exactly what was purchased, quantity, and price.
- **`fct_invoice_items.csv`**: Detailed items for billing or invoicing purposes, separate from the raw order log.
- **`fct_cash_balances.csv`**: contributions to the cash register (open/close balances) for shifts.
- **`fct_campaigns.csv`**: Likely records of campaign usage, redemptions, or performance metrics over time.
- **`fct_inventory_reports.csv`**: Snapshots or logs of inventory counts and audit reports.
- **`fct_bonus_codes.csv`**: Usage tracking for bonus point codes or loyalty redemptions.

## Other

- **`most_ordered.csv`**: An aggregated report showing the most popular items per place.
