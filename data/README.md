# 原始数据已经包含在仓库

文件：`olist-v2.zip`。它是从 Olist 官方 Kaggle 下载接口取得的完整原始包，44,717,580字节，解压后9个CSV共126,186,995字节。无需Kaggle账号即可使用仓库中已有副本。

运行 `python scripts/extract_data.py` 后，CSV出现在 `data/raw/`。该脚本先验证哈希和ZIP完整性；遇到已被修改的原件会停止。

| 文件 | 行数 | 列数 |
|---|---:|---:|
| olist_orders_dataset.csv | 99,441 | 8 |
| olist_order_items_dataset.csv | 112,650 | 7 |
| olist_customers_dataset.csv | 99,441 | 5 |
| olist_order_payments_dataset.csv | 103,886 | 5 |
| olist_order_reviews_dataset.csv | 99,224 | 7 |
| olist_products_dataset.csv | 32,951 | 9 |
| olist_sellers_dataset.csv | 3,095 | 4 |
| olist_geolocation_dataset.csv | 1,000,163 | 5 |
| product_category_name_translation.csv | 71 | 2 |

来源：[Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)，发布者Olist；下载于2026-09-30，API版本2。平台更新日不等于业务发生时间，数据反映2016–2018年。

许可：**CC BY-NC-SA 4.0**，[许可摘要](https://creativecommons.org/licenses/by-nc-sa/4.0/)。原始包未修改。重新分享或衍生使用请保留来源、注明改变，并遵守非商业及相同方式共享条件。每个文件的SHA-256在 [source-manifest.json](source-manifest.json)。

完整字段解释见 [九表说明](../docs/02-data-guide.md)。匿名买家编号不能用于识别或联系现实中的个人；公开研究数据不等于真实营销联系名单。
