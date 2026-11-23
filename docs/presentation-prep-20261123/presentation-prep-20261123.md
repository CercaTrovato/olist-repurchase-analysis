---
course: IS6400
assignment: A06-group-project
type: presentation-preparation
updated: 2026-11-23
status: prepared-not-rehearsed
---

# 11 月 25 日展示：先理解整份故事，再讲第 1、2、9 页

你是 6 号，负责开场、总流程和结论。最终稿共 13 页，前 9 页主讲、后 4 页备查。下面的英文是按最终稿重新对齐的练习稿，中文是帮助理解的解释；都不是教师原话，也不是已经完成排练的记录。

来源：[已提交最终 PPTX](https://github.com/CercaTrovato/olist-repurchase-analysis/blob/main/slides/submitted-20261115/IS6400_Final_PPT_Team%20Six%20Sigma_20261115.pptx) · [最终 PDF](https://github.com/CercaTrovato/olist-repurchase-analysis/blob/main/slides/submitted-20261115/IS6400_Final_PPT_Team%20Six%20Sigma_20261115.pdf)。按最终稿物理页码使用本文，旧 14 页版的第 14 页现在是第 13 页。最终 PPTX 的 13 个 notesSlide XML 都没有讲稿文本，不能指望演讲者视图自动显示旧稿。

安排依据：11 月 17 日本人确认 Six Sigma 为 Week 13 第 2 组、11 月 25 日周三展示；准确钟点未核。教师 Guideline p.2 要求 8 分钟展示、另 2 分钟 Q&A，全员展示并参加问答。Slides 已由本人确认提交，独立回执仍待补存，不需要重交或修改附件。

## 1. 整个项目究竟想解决什么

设想经理最多能关注一小部分老客户。他需要一份“先关注谁”的名单。我们用 Olist 的历史订单给所有符合条件的客户排序，比较同样长的名单里，后来真正复购的人有多少。这里的“命中”只表示名单中的某人后来发生了合格复购。

数据先变成“每个客户在某个预测日的一行记录”。输入是这个日期以前 6 个自然月的购买行为；标签是这个日期开始、未来 90 天内是否出现有批准时间且商品金额为正的订单。训练时让模型同时看历史特征和后来结果，学习一套评分办法。真正排序时，只给模型当时已知的历史特征；未来标签等观察期走完后才用来核对。未来结果若提前混进输入，会造成信息泄漏（data leakage），让比较失真。

我们站在 2017 年 10 月的快照训练，在 2018 年 1 月的快照比较。十月有 21,160 人，其中 211 人后来复购；一月有 29,368 人，其中 230 人后来复购。这里的月份是数据中的历史时间，和 2026 年的上课日期不同。一月已经被反复用于开发，不能称为全新盲测。

两条分析线使用共同的历史资料，但回答不同的问题：

| 分析线 | 实际动作 | 交出的东西 | 怎样判断有用 |
|---|---|---|---|
| 预测 | 用十月已知结果学习评分，在一月给所有合格客户打分 | 按分数从高到低的名单 | 固定取前 10%，比较其中的真实复购人数 |
| 分群 | 把历史购买行为相近的人分在一起 | 客户群标签和群画像 | 查名单覆盖了哪些群、漏掉谁，并提出可检验的业务想法 |

前 10% 的容量向上取整为 2,937 人。加权逻辑回归（weighted logistic regression，简称 weighted LR）找到 50 位复购者，普通 LR 找到 46 位。逻辑回归可理解为“从历史案例学习各项线索怎样合成分数”；加权让少数复购案例的拟合错误得到更大重视，仍给全部客户评分。当前分数用于排序，未经专门校准，不能直接当成真实复购概率。

接着加入配送、评价和群信息，问“更复杂的办法能否在相同名额内多找人”。已测试的四类扩展得到 48、46、50、49，均没有超过加权基线的 50。这是针对实际测试版本、一月和 10% 容量的结论。它没有证明所有新字段都无用。

最后查分群：购买较久的单单群有 90 位真实复购者，当前全局加权名单只找到其中 2 位，漏掉 88 位。这个缺口给出了后续研究问题：是否值得测试更合适的内容？团队提出主题购物指南与通用购物指南的随机对照试验，但尚未执行。历史预测能找到谁，与联系客户后能多产生多少购买，是两个需要不同证据的问题。

## 2. 13 页怎么接成一条故事

| 最终页 / 主讲人 | 中文要点 | 它承接什么、把什么交给下一页 |
|---|---|---|
| 1 / 6 号 | 有限名额下先关注谁 | 提出经理的问题，交给总流程 |
| 2 / 6 号 | 预测与分群两条线相遇 | 先说明为什么既做模型又做群画像，再进入数据 |
| 3 / 1 号 | 历史输入、未来标签、同容量 | 建立后续所有数字的分母和时间边界 |
| 4 / 2 号 | 三群差异与特征想法 | 解释为什么想研究配送和评价，不宣称已有效 |
| 5 / 3 号 | 七方法筛选：加权 LR 的 50 最高 | 选出固定容量参照，再问扩展能否超过它 |
| 6 / 3 号 | 后续 R3：50 / 48 / 46 / 50 / 49 | 展示实际负结果，转向“名单漏了谁” |
| 7 / 5 号 | 久单群 90 人中只找到 2 人 | 把整体指标转成具体客户覆盖问题 |
| 8 / 4 号 | 尚未开展的内容试验与样本量 | 把覆盖问题转成业务假设，同时交代可行性 |
| 9 / 6 号 | 小幅观察优势、复杂度边界、覆盖缺口 | 收束三条发现，提出下一步，进入 Q&A |
| 10 / 备查 | 八个输入、加权 LR 配置与排序规则 | 被问方法时打开，不在主讲中逐项读参数 |
| 11 / 备查 | 多给群名额与群内排序分别评价 | 解释 73、518、79 的不同分母 |
| 12 / 备查 | 5% / 10% / 20% 与十月五折 | 回答容量选择和加权并非处处更好的问题 |
| 13 / 备查 | 已测字段与未测新提案 | 回答“你们是否已经验证所有配送/评价想法” |

读第 2 页原图时，从顶端数据检查和历史输入开始，沿左侧读“模型筛选→扩展核对→观察结果”，再沿右侧读“分群→群内诊断→业务想法”。中间横箭头表示把预测分数、事后结果和群标签连起来检查。右侧虚线表示诊断可能反馈出新特征想法，需要验证后才采用；它不代表所有反馈都已跑完。

## 3. 你负责的三页：中文理解、英文讲法和转场

三页合计目标约 95 秒，沿用既有全组预算；这只是练习目标，必须以真人计时为准。全组旧预算是 460 秒主讲加 20 秒转场，不是已经测出的用时。

### 第 1 页：说清问题，不急着报算法

你要让听众先知道：这是“容量有限时怎样排关注顺序”的项目。说完问题后，给出两个动作——比较同长度名单、检查漏掉的人。封面上的 Coordinator 是你的团队角色，不等于你亲自做了全部模型或每位成员已经完成排练。

建议英文（约 20–25 秒）：

> Hello everyone. We are Team Six Sigma. We ask which customers should receive attention when capacity is limited. Using Olist's historical orders, we compare equal-sized customer lists, then use customer groups to understand who the list misses.

中文意思：大家好，我们是 Six Sigma。关注客户的能力有限时，应该先关注谁？我们用历史订单比较同样长的客户名单，再用分群理解哪些人仍被漏掉。

接第 2 页：

> Let me show how these two parts connect.

### 第 2 页：你讲的是分析之间的关系

共同起点是已经核对时间和缺失情况的客户历史。左边预测线学习“谁更可能复购”，右边分群线描述“这些人有什么相似之处”。分群使用最近购买间隔（R）、历史订单数（F）和历史商品金额（M），合称 RFM。K-means 把这些数值接近的人分组；先用十月学习缩放和群中心，再把一月客户分到已有中心。

R 的单位是天、F 是笔数、M 是金额，数值尺度不同。缩放就是按训练数据把各项调整到可比较的尺度，避免金额仅因数大就支配“相似程度”。群中心是一个群在这些特征上的平均位置，可理解为该群的代表点；一月沿用十月学到的调整办法，分到距离最近的已有中心。群名是画像概括，37 天、135 天是群内中位数，不是人工划分阈值。

中间横箭头是关键：把一个人的模型分数、群标签和后来是否复购放在一起，才能查某群得到多少名额、找到多少人。事后结果用于检查，不能倒灌进该期预测输入。虚线则是“发现缺口后提出下一个待验证想法”。

建议英文（约 35–40 秒）：

> Our analysis has two connected paths. We start with audited historical customer data. On the left, predictive models rank customers and compare equal-sized lists. On the right, customer groups describe buying histories. We then combine scores, group labels and observed outcomes to check coverage and missed buyers. These diagnostics can suggest new features or a content trial. Those proposals still need validation; the content trial has not run.

不要逐框读英文。用“共同数据→两条线→诊断相遇→待验证建议”四个动作带听众看图。第 5 页是早期 H04 筛选，第 6 页后是后续 R3 核验，流程展示两阶段的关系，不表示它们是同一次运行。

交给 1 号第 3 页：

> Next, my teammate will explain how we built the customer snapshots and kept past information separate from future outcomes.

### 第 9 页：把三条发现收回来

4 号在第 8 页讲完未实施的内容试验后，你接回结论。先说观察到的小幅优势，再说已测扩展没超过参照，最后把漏掉的久单客户与待测试业务想法连起来。不要把下一步说成已完成的实验。

接回开头：

> To bring the findings together, we have three conclusions.

建议英文（约 35–40 秒）：

> Weighted logistic regression found fifty repeat buyers, versus forty-six for the unweighted baseline, within the same January development protocol. The tested extensions did not improve that top-ten-percent result. Groups also revealed a large coverage gap among long-inactive customers. Our next steps are to check reachability and sample size, evaluate on genuinely future data, and seek approval before running the content trial. Thank you.

中文意思：在相同一月开发口径下，加权 LR 找到 50 位复购者，普通 LR 为 46。已测扩展没有改善前 10% 的结果。分群揭示久单客户仍大量被遗漏。下一步先核可触达人数和样本量，再做真正未来评价，并在获批后开展内容试验。

进 Q&A：

> We are happy to take your questions.

## 4. 这些数字必须知道分母

| 数字 | 正确读法 | 常见误读 |
|---|---|---|
| 29,368 / 230 | 一月合格客户 / 其中真实复购者 | 不是训练人数，也不是被触达人数 |
| 2,937 | 每种方法同样长的前 10% 名单，容量向上取整 | 不是全部客户都只剩 2,937 人参与评分 |
| 50 / 46 | 两份同容量名单内观察到的复购人数 | 不是发消息新增 4 单，也未证明显著性 |
| 1.70% | 精确率（precision）：50 位命中占 2,937 位入选者的比例 | 不是全体客户的复购概率或整体准确率 |
| 21.74% | 召回率（recall）：230 位真实复购者中找到 50 位 | 不是名单里 21.74% 会购买 |
| 12,330 / 90 | 久单单单群客户 / 其中真实复购者 | 不是已同意参加试验人数 |
| 73 / 2 | 当前 R3 全局名单中的久单人数 / 其中命中 | 不是预先给久单群设置的配额 |
| 79 | 另一次只在久单群内取名单的固定容量 | 不能把它和全局 73 席混成一份名单 |
| 88 | 久单 90 位真实复购者中有 88 位不在当前全局名单 | 不代表这些人愿意接受营销 |
| 21,308 | 既有设计检测相对 +50% 所需两组合计样本 | 不是每组人数，不是 +50 个百分点 |

用同一批人的两个分母理解精确率和召回率：经理拿到 2,937 人名单，后来发现其中 50 人复购，所以精确率为 $50/2937\approx1.70\%$。再看全体真实复购的 230 人，这份名单找到 50 人，所以召回率为 $50/230\approx21.74\%$。两者问的是不同问题。

样本规划用久单历史率 $90/12330\approx0.730\%$ 作假设基线。相对提高 50% 是乘以 1.5，约变为 1.095%，绝对增加约 0.365 个百分点。既有近似规划采用双侧 5% 显著性水平、80% 功效、1:1 分组，需要总计 21,308 人，多于历史池 12,330 人。功效指“目标差异确实存在时，按设计有多大机会检出它”；这些数值是规划条件，不能当试验已有效的证据。

## 5. Q&A：先给一句判断，再展开依据

以下为练习用参考回答。建议你先练第 1、2、3、4、9、12 题；技术追问交对应成员补充，全员参加 Q&A。

### 1. Does finding fifty instead of forty-six prove marketing uplift?（你主答，第 9 页）

中文：没有。这里是在历史数据里换一种排序后，多找到 4 位后来复购者。我们没有实施营销干预，无法知道其中多少人因营销才购买。

> No. These are observed repeat buyers in historical lists. We did not run a marketing intervention, so four additional hits do not establish four incremental purchases caused by marketing.

### 2. Why compare lists of the same size? Why ten percent?（你主答，第 3、12 页）

中文：多选人通常会找到更多人，固定 2,937 个名额才能比较排序。10% 是统一比较点，未证明为最佳业务预算；实际预算还要看触达成本、可触达资格和实测反应。

> Equal-sized lists keep capacity comparable. Ten percent is our comparison point, not a proven operating optimum. We also checked five and twenty percent; actual capacity needs business evidence.

备查第 12 页：5% 的 1,469 人名单为 31 / 31；10% 的 2,937 人名单为 46 / 50；20% 的 5,874 人名单为 73 / 75，顺序均为普通 / 加权。

### 3. What does the dashed arrow mean?（你概述，第 2、13 页）

中文：分群诊断可以提出新字段，但提案需要经过匹配口径的测试，才知道有没有用。它不表示所有反馈已完成或改善模型。

> The dashed arrow represents feature ideas suggested by group diagnostics. Those ideas require validation. It does not mean every proposal was implemented or improved the model.

### 4. Is January an unseen final test?（你概述，1/3 号补充，第 3、9 页）

中文：一月是已经多次检查的开发窗口。已有四月研究也被看过，不能换名字后又叫新盲测。我们需要真正未来数据来检验稳定性。

> No. January has already been examined during development. Previously examined April results are not a fresh blind test either. We need genuinely future evaluation before claiming stable performance.

### 5. Why choose weighted LR when CatBoost has a higher ROC-AUC?（3 号主答，第 5 页）

中文：ROC-AUC 衡量跨许多阈值的整体区分排序能力；本次问题只给 2,937 个名额，看该容量内命中多少。加权 LR 在七方法筛选中命中最多，AP 也最高，但没有赢所有指标。AP 是综合观察不同名单长度下，复购者是否能靠前出现的指标；这里无需把它当另一种命中人数。

> Our decision fixes the list at 2,937 customers. Weighted LR finds the most buyers at that capacity and has the highest AP in the screening table. CatBoost has the highest ROC-AUC. The choice is specific to our capacity objective.

### 6. Is fifty versus forty-six statistically significant?（3/5 号主答，第 5、9 页）

中文：现有材料支持描述“观察到多找到 4 人”，没有证明统计显著或未来稳定优于。不能仅靠这两个计数补出显著性结论，也不采用旧错误区间。

> We report four additional observed buyers descriptively. The current evidence does not establish statistical significance or stable superiority on future data.

### 7. Are the screening and R3 baseline the same run?（3/5 号主答，第 5–7 页）

中文：不是。第 5 页来自 H04 v0.2 筛选，第 6 页后用 R3。两份加权名单都命中 50，但 2,937 人名单共同只有 2,920 人、各替换 17 人；旧全局久单 79 席、R3 为 73 席。不要混用 AP、AUC 和群席位。

> No. They are separate saved stages. Both weighted lists find fifty buyers, but their scores and selected customers differ. The group diagnostics use the later R3 list with seventy-three long-inactive places.

### 8. Did clustering improve prediction?（4/5 号主答，第 7、11 页）

中文：分群帮助解释客户和漏选情况，但“加群号”全局仍为 50，分群建模为 49，没有超过 50。群模型给久单 518 席、找到 4 人，不能直接和基线 73 席、2 人说成群内排序更好；另固定取 79 人时，分群模型为 1、基线为 2。

> Clustering helped diagnosis and customer profiles. Adding the group label tied fifty hits, and separate group models found forty-nine. More places for a group do not by themselves prove better ranking within that group.

### 9. What would the content trial actually test?（你概述，4 号补充，第 8 页）

中文：两组都接受联系，一组主题指南、一组通用指南；同渠道、版式和时间。它测试内容主题之差，没有不联系组，因此不能回答联系相对不联系的总效果。90 天复购率的分母是所有随机分配的人，不仅是打开或点击的人，避免只看主动响应者造成偏差。试验尚未开展。

> It would compare a themed guide with a generic guide, with both groups contacted. The denominator is all randomized customers. It tests the difference between content themes, not contact versus no contact. The trial has not run.

### 10. Can the trial detect a fifty-percent improvement?（4 号主答，第 8 页）

中文：既有假设下需总计 21,308 人，超过久单历史池。历史池又不等于已同意、可触达的池，不能承诺当前可行。+25%、+50%、+100% 的既有总样本规划分别是 76,784、21,308、6,380，都是假设效果量，不是观察提升。

> Under the existing planning assumptions, a fifty-percent relative improvement needs 21,308 people in total. That exceeds the historical pool, and reachability is unknown. Feasibility must be checked before launch.

### 11. Does cross-validation show weighting always helps?（3 号主答，第 6、12 页）

中文：没有。十月五折平均命中普通为 7.0、加权为 6.8。五折是把十月数据分成五份，轮流留一份核对，其余训练；每个核对折 4,232 人，只取 424 人，所以不能直接与一月取 2,937 人的 50 命中比较。± 是五折样本标准差，表示折间波动，不是置信区间，也不是五个独立未来月份。群模型 CV 另有固定全十月群映射条件，不能称整个聚类流程完全折内隔离。

> No. October five-fold mean hits are 7.0 unweighted and 6.8 weighted. These are internal folds with smaller lists. The reported spread is sample standard deviation, not a confidence interval or five future tests.

### 12. What is the next practical step?（你主答，第 9 页）

中文：先核客户是否可联系、愿不愿参加，再核样本是否足够检出目标差异；明确未来评价和业务审批，才考虑实施。材料准备完成不等于已经触达、开展试验或确认利润。

> First check reachability and sample size. Then arrange genuinely future evaluation and obtain explicit approval before a content trial. Profit and incremental marketing impact remain unestablished.

## 6. 可以马上开始的互动练习

先不看下面答案，按顺序做。每次只练一个动作，助手依据你的实际回答再追问，不将材料已写好记录为你已掌握。

1. 用中文 30 秒讲清：经理要什么、我们怎样比较、分群补充了什么。
2. 用手指着最终第 2 页，说出“共同起点、左右两线、中间相遇、虚线反馈”，并解释为什么未来结果只用于核对。
3. 回答：老师问“你们多找到 4 人，所以营销多带来 4 单，对吗？”先一句英文判断，再给一句理由。
4. 合上资料，解释 73 与 79，以及 precision 和 recall 的分母。
5. 真人计时读第 1、2 页，按转场交给 1 号；由 4 号讲完第 8 页后接第 9 页。记录真实用时、卡词和漏讲，不先填“排练完成”。

<details><summary>练习 3、4 的核对要点</summary>

3：No。Historical list hits are not incremental purchases caused by marketing；没有随机干预结果。

4：73 是当前全局名单里的久单人数，79 是另一次群内固定容量。Precision 的分母是入选 2,937 人，recall 的分母是全体真实复购 230 人。

</details>

排练记录留空：实际日期____；第 1 页____秒；第 2 页____秒；第 9 页____秒；全组____秒；仍答不清的问题____。

## 7. 数字与版本来源

- 最终 PPTX SHA-256：`9452af19a145bc491532fb414c2d1704eecb9362998ca14eed59814486cbd8b2`；PDF：`5c4d6e65fafd5842edccc74b2f240f34ab85ab775add796abc1162abdeeedbee`。已读全部 13 页文字、查看两张全页联系图，并单独查看第 1、2、9 页；未修改原件。
- [H04 七方法原表](https://github.com/CercaTrovato/olist-repurchase-analysis/blob/a80de7a4ad7f44188b70abe8e432b548f69765d1/slides/a-draft-20261115/source/ranking-comparison.csv)：第 5 页；不能用早期 `results/classification/model-comparison.csv` 的其他人数口径替代。
- [后续 R3 容量表](https://github.com/CercaTrovato/olist-repurchase-analysis/blob/a80de7a4ad7f44188b70abe8e432b548f69765d1/research/route-comparison-20261114/data/team-capacity-results.csv) · [十月 CV 表](https://github.com/CercaTrovato/olist-repurchase-analysis/blob/a80de7a4ad7f44188b70abe8e432b548f69765d1/research/route-comparison-20261114/data/team-cv-diagnostics.csv)：第 6、12 页。
- [两份加权名单的版本差异](https://github.com/CercaTrovato/olist-repurchase-analysis/blob/a80de7a4ad7f44188b70abe8e432b548f69765d1/research/team-round3-20261112/audit/h04-v02-vs-round3-F0.csv)；[R3 群诊断、试验设计及样本规划](https://github.com/CercaTrovato/olist-repurchase-analysis/blob/a80de7a4ad7f44188b70abe8e432b548f69765d1/research/team-round3-20261112/README.md)：第 7、8、11 页。
- 原 Guideline p.2 与课程 `notes/supervision-report.md` 的 11 月 17 日日期更正。2026-11-23 侧栏浏览器返回不可用，Canvas 本日未重新回读；准确展示钟点继续待核。

本文准备和核对了讲法，没有训练模型、重新评分、实施营销或替本人完成练习。
