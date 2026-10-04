# 九张表与完整字段解释

## 先读懂统计单位

Olist不是一张客户大表。一次下单可以有多个商品、多个支付记录和多条评价。把表连接成功，不代表统计口径正确。

| 表 | 一行是什么 | 主要连接键 |
|---|---|---|
| orders | 一笔订单 | order_id、customer_id |
| customers | 一个订单侧客户编号 | customer_id、customer_unique_id |
| order_items | 一条订单商品明细 | order_id＋order_item_id；product_id；seller_id |
| order_payments | 一条支付记录 | order_id＋payment_sequential |
| order_reviews | 一条评价 | order_id；review_id也需核唯一性 |
| products | 一个商品 | product_id、product_category_name |
| sellers | 一个卖家 | seller_id |
| geolocation | 一条邮编前缀地理记录 | 邮编前缀不是唯一键 |
| translation | 一个品类名称映射 | product_category_name |

例如一笔订单有2条商品明细、2条支付，直接按订单号合并会得到4行；原金额可能被重复计算。先各自汇总到订单，再连接，最后按customer_unique_id汇总到客户。示例见 [教学Notebook](../notebooks/01-data-guide.ipynb)。

## 已核数据质量提醒

- 99,441行客户记录对应96,096个买家编号，不是同一个客户数定义。
- 775笔订单没有商品明细，1笔无支付记录，768笔无评价记录；不能把缺失直接当零。
- 547笔订单有多条评价；1,278笔订单涉及多个卖家。
- 地理表有261,831条完整重复行，邮编前缀也对应多行；直接连接会放大样本。
- 2018年9月仅16笔订单、10月仅4笔。不能由末期骤降直接判断业务崩溃。
- 预计送达字段多为日期零点；直接比较时间戳与按日历日期比较，延迟比例不同。
- 没有营销处理组、广告曝光、完整客户联系方式、完整退款损失或利润。

这些是原始版本的描述统计，不是分类实验筛选后的样本统计。正式分析要说明纳入和排除规则。

## 全部52个“表—字段”位置

同一个连接字段在多张表出现，所以52不等于52种互不重复的信息。读取类型是程序实际读入的类型，不一定等于业务类型。例如邮编在CSV中像整数，但应视为类别字符串保留前导零。

以下缺失数按pandas默认缺失识别计算；没有空值不代表没有异常或特殊编码。字段含义依据Olist说明与原始结构整理，角色与限制由项目补充。

### olist_customers_dataset.csv

99,441 行 × 5 列。

| 字段 | 读取类型 | 缺失数 | 人话说明 |
|---|---|---:|---|
| `customer_id` | object | 0 | 订单侧客户编号；连接订单与客户表 |
| `customer_unique_id` | object | 0 | 跨订单识别同一买家的匿名编号；不等于可确认的自然人身份 |
| `customer_zip_code_prefix` | int64 | 0 | 买家邮编前缀；类别标识，应保留前导零 |
| `customer_city` | object | 0 | 买家城市 |
| `customer_state` | object | 0 | 买家州代码 |

### olist_geolocation_dataset.csv

1,000,163 行 × 5 列。

| 字段 | 读取类型 | 缺失数 | 人话说明 |
|---|---|---:|---|
| `geolocation_zip_code_prefix` | int64 | 0 | 地理表邮编前缀；不是唯一键 |
| `geolocation_lat` | float64 | 0 | 纬度 |
| `geolocation_lng` | float64 | 0 | 经度 |
| `geolocation_city` | object | 0 | 地理记录城市 |
| `geolocation_state` | object | 0 | 地理记录州 |

### olist_order_items_dataset.csv

112,650 行 × 7 列。

| 字段 | 读取类型 | 缺失数 | 人话说明 |
|---|---|---:|---|
| `order_id` | object | 0 | 订单编号；订单表主键，其余订单相关表的连接键 |
| `order_item_id` | int64 | 0 | 同一订单内的明细序号；需与 order_id 合作复合键 |
| `product_id` | object | 0 | 商品编号 |
| `seller_id` | object | 0 | 卖家编号 |
| `shipping_limit_date` | object | 0 | 卖家交付物流的期限；不是实际发货时间 |
| `price` | float64 | 0 | 商品明细金额，巴西雷亚尔 BRL；不是 Olist 的净营收 |
| `freight_value` | float64 | 0 | 分配到该商品明细的运费 BRL；订单运费需汇总 |

### olist_order_payments_dataset.csv

103,886 行 × 5 列。

| 字段 | 读取类型 | 缺失数 | 人话说明 |
|---|---|---:|---|
| `order_id` | object | 0 | 订单编号；订单表主键，其余订单相关表的连接键 |
| `payment_sequential` | int64 | 0 | 订单内支付记录序号；不是购买次数 |
| `payment_type` | object | 0 | 支付方式 |
| `payment_installments` | int64 | 0 | 分期期数；不是支付表的行数 |
| `payment_value` | float64 | 0 | 该支付记录金额 BRL |

### olist_order_reviews_dataset.csv

99,224 行 × 7 列。

| 字段 | 读取类型 | 缺失数 | 人话说明 |
|---|---|---:|---|
| `review_id` | object | 0 | 评价编号；是否唯一需实际检查 |
| `order_id` | object | 0 | 订单编号；订单表主键，其余订单相关表的连接键 |
| `review_score` | int64 | 0 | 1–5 星评分 |
| `review_comment_title` | object | 87,656 | 评价标题；缺失不代表没有评分 |
| `review_comment_message` | object | 58,247 | 评价正文；未做语言识别或文本情感分析 |
| `review_creation_date` | object | 0 | 评价问卷创建/发送相关日期；不是一定实际填写日期 |
| `review_answer_timestamp` | object | 0 | 评价答复时间 |

### olist_orders_dataset.csv

99,441 行 × 8 列。

| 字段 | 读取类型 | 缺失数 | 人话说明 |
|---|---|---:|---|
| `order_id` | object | 0 | 订单编号；订单表主键，其余订单相关表的连接键 |
| `customer_id` | object | 0 | 订单侧客户编号；连接订单与客户表 |
| `order_status` | object | 0 | 提取时的订单状态；不是订单确认时已知的最终结果 |
| `order_purchase_timestamp` | object | 0 | 下单时间 |
| `order_approved_at` | object | 160 | 支付/订单批准时间；建模时需选清预测时点 |
| `order_delivered_carrier_date` | object | 1,783 | 交给承运方的实际时间 |
| `order_delivered_customer_date` | object | 2,965 | 实际送达客户的时间 |
| `order_estimated_delivery_date` | object | 0 | 预计交付日期；多为零点，比较时须明确按日期还是时间戳 |

### olist_products_dataset.csv

32,951 行 × 9 列。

| 字段 | 读取类型 | 缺失数 | 人话说明 |
|---|---|---:|---|
| `product_id` | object | 0 | 商品编号 |
| `product_category_name` | object | 610 | 商品葡语品类名称 |
| `product_name_lenght` | float64 | 610 | 商品名称长度（原始列名保留 lenght 拼写） |
| `product_description_lenght` | float64 | 610 | 商品描述长度（不是完整描述文本） |
| `product_photos_qty` | float64 | 610 | 商品图片数量 |
| `product_weight_g` | float64 | 2 | 商品重量，克 |
| `product_length_cm` | float64 | 2 | 商品长度，厘米 |
| `product_height_cm` | float64 | 2 | 商品高度，厘米 |
| `product_width_cm` | float64 | 2 | 商品宽度，厘米 |

### olist_sellers_dataset.csv

3,095 行 × 4 列。

| 字段 | 读取类型 | 缺失数 | 人话说明 |
|---|---|---:|---|
| `seller_id` | object | 0 | 卖家编号 |
| `seller_zip_code_prefix` | int64 | 0 | 卖家邮编前缀 |
| `seller_city` | object | 0 | 卖家城市 |
| `seller_state` | object | 0 | 卖家州代码 |

### product_category_name_translation.csv

71 行 × 2 列。

| 字段 | 读取类型 | 缺失数 | 人话说明 |
|---|---|---:|---|
| `product_category_name` | object | 0 | 商品葡语品类名称 |
| `product_category_name_english` | object | 0 | 品类英文名称 |

来源：[Olist官方数据页](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)；本仓库 [来源及逐文件指纹](../data/source-manifest.json)。原始数据只读，生成的特征表不是官方原件。
