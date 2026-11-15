# A初稿v2：本次局部修改核验

用户要求：第4页改用3号提供的ranking-comparison CSV，展示其他模型比较及选择weighted LR的依据；3号主讲第5页。

## 本次实际完成

- 第4页为七方法原生横向柱图，数据按命中数排列，weighted LR50高亮。其余为LR46、CatBoost45、Random forest44、weighted RF36、weighted CB35、Recency30。
- 输入CSV SHA-256为`0c441cba15087c84c24f77a540b040675ad9eab0bebc05083e1ab8b4d4f5bb9a`，与保存的H04 v0.2原包内同名表逐字节一致。7行N/正例/K一致，precision/recall/随机期望均按分母核对。
- weighted LR的命中及AP最高，ROC-AUC最高为CatBoost。因此选型限定为固定Top10%容量目标，不称全部指标都胜出。
- 第4页明确为早期H04筛选，第5页转后续R3。分数、名单、AP/AUC的版本差异保留；R3群体73席等数值没有替换为旧H04全局79。
- 3号第4、5页合150秒，5号第6页55秒；其他分工不变，总460秒+20秒缓冲。当前英文正文964词，尚未真人计时。
- PPTX可见页面XML只有第4、5页发生改变；第5页仅增加R3阶段提示，图表数值不变。第4/5/8页notes、JSON、讲稿及分工/16问答/群稿已同步。
- 两张原生图表保留。第4页图表的Excel工作簿有7行方法数据，系列、区域、缓存与CSV一致；后续R3图表与工作簿原字节未变。
- 本机PowerPoint原生打开并导出12页PDF，全部页面可搜索文字；第4、5页已实际渲染查看。初稿v1的未变页面视觉证据按原版本承接，没有无意义地重做全篇审查。
- 50项定向核验无失败，OfficeCLI schema通过、issues为0；一位未参与修改的审查者完成定向独审，见[v2定向报告](v2-targeted-review.md)。

PPTX SHA-256：`67c776aa8013a397ff5073050bdc9a68d10de9ac4edd4c18cc73592a823144ed`。

PDF SHA-256：`ad48d7edf1bed4441fbd45dc7df1cba46f65b0a760b1b210c3e75d9f0a7f4495`。

原始CSV只读。本次没有重训、新实验、四月新评价或Canvas操作。仍是待小组审阅修改的草稿，不是定稿，也没有提交授权。
