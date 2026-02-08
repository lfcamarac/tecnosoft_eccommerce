# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.9.19] - 2024-11-19
### Author: jatin tomer odoo <jatintomer.odoo990@webkul.in>

### Added
- Cron to clear Sucessfull data. ref: https://webkul.chatwhizz.com/share/screenshot/673c88afe684fb2030932571

## [2.8.19] - 2025-11-03
### Author: adil ali <adilali.odoo366@webkul.in>

### Fixed
- Forecast qty sync using product "update qty" button if auto stock sync enable

## [2.8.18] - 2024-12-27
### Author: ashish varshney odoo <ashishvarshney.odoo231@webkul.in>

### Added
- Dashboard Menu ref: https://prnt.sc/aonT5EcBqqLr

## [2.7.18] - 2024-11-13
### Author: adil ali <adilali.odoo366@webkul.in>

### Patch
- If a salesperson is configured as the default, the same salesperson will be set on the order import. ref: https://prnt.sc/UyCVfUQVBIz9

## [2.7.17] - 2024-07-15
### Author: ashish varshney odoo <ashishvarshney.odoo231@webkul.in>

### Added
- Display failed feed count on the dashboard view. ref: https://prnt.sc/gtGCF-LmgsOB


## [2.6.17] - 2024-05-01
Author: rohit kumar odoo <rohitkumar.odoo828@webkul.in>

### Patch
- Removed dashboard menu from 'Channel' parent menu and created it as a single menu as 'Channels'.


## [2.6.16] - 2024-04-23
Author: rohit kumar odoo <rohitkumar.odoo828@webkul.in>

### Patch
- Optimized & Improved the import cron method(`cron_import_all`).


## [2.6.15] - 2024-04-23
Author: rohit kumar odoo <rohitkumar.odoo828@webkul.in>

### Patch
- Just Optimized the module.

## [2.6.14] - 2024-04-19
Author: rohit kumar odoo <rohitkumar.odoo828@webkul.in>

### Patch
- Optimize compute method to render the count of imported records in kanban view ref: https://prnt.sc/tPwTND-B6vK1.


## [2.6.13] - 2024-04-19
Author: rohit kumar odoo <rohitkumar.odoo828@webkul.in>

### Patch
- Updated Gloabl configuration view & added clear sync history cron reference button.


## [2.6.12] - 2024-04-16

### Author: ashish varshney odoo <ashishvarshney.odoo231@webkul.in>

### Fixed
- Error while invoice processing.UnboundLocalError("local variable 'res' referenced before assignment") in account_invoice.py file


## [2.6.11] - 2024-04-15

### Author: ashish varshney odoo <ashishvarshney.odoo231@webkul.in>

### Added
- Translation for  Arabic(ar)


## [2.6.10] - 2024-04-12
Author: rohit kumar odoo <rohitkumar.odoo828@webkul.in>

### Fixed
- Managing duplicate combination issue of product update in case of avoid duplicity, feed will be in error state.


## [2.6.9] - 2024-04-09
Author: rohit kumar odoo <rohitkumar.odoo828@webkul.in>

### Fixed
- Fixed feed evaluation cron.


## [2.6.8] - 2024-04-09

### Author: ashish varshney odoo <ashishvarshney.odoo231@webkul.in>

### Changed
- Kanban view (More option text and icon) in multichannel.xml


## [2.6.7] - 2024-04-08

### Author: ashish varshney odoo <ashishvarshney.odoo231@webkul.in>

### Added
- Shipment date field in feed and it mapped with odoo delivery date_done field.

### Changed
- Product stock sync history message


## [2.6.6] - 2024-04-5

### Author: ashish varshney odoo <ashishvarshney.odoo231@webkul.in>

### Added
- Realtime sales order status sync history (Invoice, Shipment, Cancel) And Product stock sync history.
- Style (bottom:0;) in multi_channel_sale.xml (kanban view) .


## [2.6.5] - 2024-04-5

### Author: ashish varshney odoo <ashishvarshney.odoo231@webkul.in>

### Added
- Track Visibility in fields (url ,email,api_key,channel,state,pricelist_id ,default_category_id,warehouse_id,company_id,sync_cancel,sync_invoice,sync_shipment, auto_sync_stock).


## [2.6.4] - 2024-03-28
Author: rohit kumar odoo <rohitkumar.odoo828@webkul.in>

### Optimized
- Added to_hide and to_show update in the available configs feature, also added two new fields in existing list.


## [2.6.3] - 2024-03-28
Author: rohit kumar odoo <rohitkumar.odoo828@webkul.in>

### Optimized
- Optimized the code, removed unneccessary code & libraries.


## [2.6.2] - 2024-03-27
Author: rohit kumar odoo <rohitkumar.odoo828@webkul.in>

### Added
- Filters & Groups in Channel view
- Added Avoid duplicity field in channel related to global https://prnt.sc/tmFMpFMkV_cp


## [2.6.1] - 2024-03-21
Author: jatin tomer odoo <jatintomer.odoo990@webkul.in>

### Added
- Tax on discount line based on configuration.


## [2.5.1] - 2024-03-21
Author: jatin tomer odoo <jatintomer.odoo990@webkul.in>

### Added
- Translation of module in Spanish and German language.


## [2.4.1] - 2024-03-15
Author: rohit kumar odoo <rohitkumar.odoo828@webkul.in>

### Fixed
- Creating product feed variants in one go.


## [2.4.0] - 2022-10-28

### Added
- Module is now supported to odoo version 16.0
- `description` field is introduced to the product feed to support the sync of product description.
- `wk_time_zone` field is introduced to channel configuration to fix issues in channel and odoo document date differences.
- Instance creation right from the kanban view of the instances.
- Direct record view button of Products, customers, categories & orders from the form view of the instance.
- Support update operation for mass export action via dashboard/instance export button.
### Fixed
- Order confirmation every time when the order feed is getting updated and evaluated.

## [2.3.14] - 2022-06-29

### Added
- `total_record_limit` field introduced to limit number of records to import in order to avoid timeout.
### Fixed
- Default product added for Delivery and Discount products.

## [2.3.13] - 2022-06-23

### Added
- `vat` field introduced in order and partner feed


## [2.3.13] - 2022-02-14

### Added
- `wk_default_code` field introduced for managing product template specific sku


## [2.3.12] - 2021-10-29

### Fixed
- Product Write


## [2.3.11] - 2021-05-28

### Fixed
- Default placeholder image render
## Added
- New alias image name controller


## [2.3.9] - 2021-04-07

### Fixed
- Instance Kanban View


## [2.3.8] - 2021-04-06

### Fixed
- Get Tax Ids from tax lines in order feed


## [2.3.7] - 2021-04-05

### Fixed
- Window Actions


## [2.3.6] - 2021-01-23

### Fixed
- Product/Partner/Order form view


## [2.3.5] - 2021-01-18

### Fixed
- Category & Product Feed view

## [2.3.4] - 2020-12-21

### Fixed
- Picking validation
- Feed contextualization


## [2.2.13] - 2020-09-25

### Changed
- demo.xml to data.xml
- Datetime format parsing

### Removed
- Feed sequence records from data.xml
- StockMove POS Order operation


## [2.2.12] - 2020-09-11

### Changed
- Stock move location checked with channel location and associated child locations

### Added
- Set need_sync to True, when pricelist_item is updated.


## [2.2.11] - 2020-09-08

### Added
- Unlink product variant mappings when unlinking product template mapping


## [2.2.10] - 2020-09-07

### Fixed
- Instance kanban view with large numbers
-
### Deprecated
- weight_unit in product.variant.feed


## [2.2.9] - 2020-09-01

### Fixed
- Variant feed write


## [2.2.8] - 2020-09-01

### Fixed
- Import Infinity loop when api_imit==1


## [2.2.7] - 2020-07-16

### Fixed
- Mapping button in feed form view


## [2.2.6] - 2020-07-15

### Fixed
- Dashboard name conflict with website
- Contextualized variant feed dictionary with template it


## [2.2.3] - 2020-07-10

### Changed
- Show parent partner record only in tree view
- Count parent partner record only in Customer count


## [2.2.2] - 2020-07-07

### Fixed
- Set invoice as 'paid' where state == 'posted'


## [2.2.1] - 2020-07-03

### Fixed
- Contextualized mapping with product_id


## [2.1.11] - 2020-06-23

### Fixed
- Duplicate order.line.feed when feed is updated.


## [2.1.10] - 2020-06-18

### Fixed
- On variant creation/updation, barcode unique error due to `barcode == ''`


## [2.1.9] - 2020-05-28

### Fixed
- In Instance Dashboard controller, month label obtained from db stripped.

