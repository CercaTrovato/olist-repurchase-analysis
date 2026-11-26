# IS6400 写作发布包：一次轻量独立抽检
日期：2026-11-27。审查者：/root/writing_release_review（gpt-6.1-sol；未参与本包撰写）。作者／合稿者：父代理 /root，具体人的贡献以 contributions-and-acceptance.md 为准。

结论：职责、结构、实验身份与所抽视觉内容可继续使用；发现两处应在本包发布前完成的局部修复（D1、D2），另有一处低风险一致性建议（S1）。无需重跑模型或重审全包。当前不能据此称“全包独审通过”或“正式报告完成”。

## 实际范围与阅读条件
先读候选 README、WRITING-RULES、STRUCTURE、ROLES、DELIVERY-TEMPLATE、六张岗位卡；重点顺读 2/3/5/6 号的“子节→交付→证据入口→交叉核对”，另读群稿、文献 README/CSV/BibTeX 与样张 tex。再核 writing-brief、contributions-and-acceptance、model-parameters.csv、课程入口、适用作业／独审规则和 Crossref 原始回执。派单已带来源路径和作者检查摘要，因此并非完全盲审；未将作者的链接／编译通过结论当作本次实做。

冻结清单 frozen-candidate.json 的 29 个文件实际重算 SHA-256，全部与清单一致。代表哈希：
- WRITING-RULES.md：803ef3f3fcdf9b72d9e75c30c9a7d39e621988000c0548dac0f3cdf0c969d553
- references/verified-journals.bib：c1e80f6a485bdf53df8cd2c830b9657d083936c1ab6e01d0ffecc86fc8733421
- template/IS6400_Report_Layout_Sample_v2.tex：5c46e5413d410aa844d338678f13a2c6e99c06df0fd9afc8642e5e0a6bfe9aaa
- template/IS6400_Report_Layout_Sample_v2.pdf：5f8eee0441511529b11db81b649962abb6419ceae4b1ec75f394850758997e7a

实际用 view_image 查看 v2-page-5.png、v2-page-6.png、v2-page-7.png。没有视觉查看其他四页，没有重新编译、重查全部 67 条链接、重跑任何实验，也没有全面复核十篇全文。教师模板 slide 4 和 Canvas 截止本轮承接主代理核验，未由本审查者重新打开；本结论不升级该来源的核验范围。

## 可直接使用的部分
1. 六章、封面、一页摘要、附录引用合计 23 页；按子节跨人协作，六名真实成员与编号对应正确。2 号不冒称新增模型为本人拟合；3 号区别 H04/R3、旧 one-hot 与独立扩展 native 输入；5 号交英文评价正文且核训练／开发／后期、配对和不确定性；6 号保留独立 80/20 概率／价值协议。与抽核的贡献表和参数表未见矛盾。
2. 11/30 22:00 HKT、12/2、12/4、12/5 均明确是内部建议；12/6 23:59 HKT 沿既存 Canvas 记录且要求定稿前再核。没有虚构团队已认领、已写稿、已通读或已提交。群稿同样请成员回报可行性。
3. 规则明确正式期刊与软件／数据原始来源的不同职责，DOI 存在性与论点支持分开；公式、图表用稳定 ID 交稿再统一自动编号。这套交件方式无需组员会 LaTeX，图表／底数据／图源／引用位置各有交付槽。
4. 第 5–7 页所见：Table I.、Table II.、Fig. 2. 标签及编号加粗，题注其余文字正常字重；正文 Table、Figure 写全字。第 5 页首次展开 limited-memory Broyden–Fletcher–Goldfarb–Shanno (L-BFGS)，第 6 页首次展开 average precision (AP) 与 area under the receiver operating characteristic curve (ROC AUC)。第 6 页 50/49/48 图表一致，正文不把 AUC 更高写成固定容量命中更高，也不把该开发比较写成新盲测或等效结论。

## 文献定向抽样（三篇）
- Cox 1958：Crossref 原回执的作者、题名、20(2)、215–232、DOI 与候选相符。出版者检索可读结果确认历史期刊副标题 Methodological，并明列 1959、21(1)、238 勘误；当前 Crossref 新品牌另存字段的做法合理。仅接受作二元回归背景，候选已要求引用细节前读勘误。[OUP 原文](https://academic.oup.com/jrsssb/article/20/2/215/7027376)、[1959 出版者更正页](https://rss.onlinelibrary.wiley.com/doi/10.1111/j.2517-6161.1959.tb00334.x)。直接 open 原文发生工具重定向不可访问，未读原文／勘误全文。
- Van Calster 等 2019：Crossref 与本次实际打开的 [BMC Medicine 出版者页](https://link.springer.com/article/10.1186/s12916-019-1466-7) 对上 17:230、题名、DOI 和五位个人作者；页面明标 Opinion。实读 Background／Main text 中校准与判别力区别，候选限制于校准概念、不过推电商收益恰当。作者字段抽取却有 D1。
- Friedman 2001：Crossref 原回执对上 Annals of Statistics 29(5)、1189–1232、题名、作者和 DOI。出版者文献记录／摘要说明梯度提升家族；候选未冒称 CatBoost 原论文，支持范围合理。[正式出版者入口](https://projecteuclid.org/journals/annals-of-statistics/volume-29/issue-5/Greedy-function-approximation-A-gradient-boosting-machine/10.1214/aos/1013203451.full)。本次 open 仅返回 iframe，元数据和支持范围承接其可读出版记录摘要及原 Crossref；未审全文。

## 必要局部修复
### D1：Van Calster 的空作者进入可用 BibTeX
位置：references/verified-journals.bib:86 的 author = { and Ben Van Calster ...}；CSV:9 同为以分号开头的作者串，JSON 同源记录也需保持一致。
Crossref 第一条是只有 name 的集体署名，不是 given/family，因此被生成器转换成空人。直接给成员使用会把空作者传入 BibTeX，可能错误排作者、出现警告或不完整引用。最小修复：按已核出版者顺序保留五位个人作者并清除空项；STRATOS 集体署名如保留，放单独 note／corporate 字段，不能生成空作者。同步 CSV／JSON／BibTeX 同一记录即可，不必重审其余九篇。验收：三个载体无空作者项、五人顺序对上出版者；BibTeX author 不以 and 开头。

### D2：编号公式 (2)、(3) 没有被正文明确引用
位置：样张 tex:124–127（第 5 页）。两式已有 label，但 For F0 的演算说明没有引用它们；当前正文只显式引用了 Equation (1)。这与 WRITING-RULES §3“每个编号公式均在正文明确引用”不一致，容易让组员沿用漏引样式。
最小修复：在第 127 行把开头改成 Using Equations~\eqref{eq:precision} and~\eqref{eq:recall}, ... 或等价自然英文，其余数字不变。验收：重编译后正文显示 Equations (2) and (3)，无 ??，第 5 页显示正常。纯交叉引用修复由主代理核差异和该页即可，不要求新教学复审。

## 非阻塞建议
S1：样张 [1] Olist 与 [2] 本组结果网页引用（tex:158–159）目前有 URL 而无访问日期，和 WRITING-RULES §5 自定“网页资料保留官方 URL 和访问日期”不齐。可补实际读取／核验日；未实际核到的日期不要编写。本问题不改变实验或学术引用真实性，不扩大为来源全文审核。

本报告仅写 scratch；候选、课程正式文件、Git、网站和外部消息均未改动。无新增拟合，不推定用户已理解或团队已接受。

## 2026-11-27 定向复核与关闭结论
本节承接原抽检，仅复核 D1、D2、S1。前文为冻结初审的真实发现，保留不覆盖；当前处置以本节为准。未重做整包审查、实验、全文文献审查或外部访问。

- D1 已关闭。实际重新读 verified-journals.bib/csv/json 的 Van Calster 记录，并对照原 Crossref 中具有 given/family 的五位个人作者，CSV 和 JSON 作者串逐项一致，BibTeX 无前导 and 或空作者；原始 name 团体署名单独存入 corporate_author_note，CSV/JSON 均与原回执一致，未混作空的个人作者。
- D2 已关闭。tex:127 已使用两个 eqref；实际查看 fixed-v2-page-5.png，正文显示 Using Equations (2) and (3)，公式编号和页面无 ??、截断或明显挤压，原 50、2937、230 及精度未改。
- S1 已关闭。tex:158–159 和实际查看的 fixed-v2-page-7.png 均增加 accessed Nov. 27, 2026。日期依据是主代理本日实际打开 Kaggle/GitHub 的记录；本审查者只核写入与显示，未代称自己又访问两站。Kaggle 无可读正文不被此访问日期升级为数据内容重读／核验，原内容边界保持。

以上三个参考资料载体及样张 tex/PDF 共五个变化文件的当前 SHA-256 均与更新后的 frozen-candidate.json 相符。最新 PDF SHA-256：7de04c1546984cea960f02c30c7c5a1d120cf638e02896156f94b2245e8c3c36。
追加前独审报告 SHA-256：24d17cf138accd1298aa5c221a0da1f2f722774dc827fdb13499e695d99b3b8a。追加后的最终报告哈希由回传与父代理外部绑定记录，避免在报告正文中写自引用哈希。

本次抽检发现的必要缺陷现均已关闭，可基于本报告继续本轮写作发布。结论仍只覆盖已明示样本及上述三处变化，不声称全包独审、十篇全文通过或最终报告可提交。候选未由审查者修改。
