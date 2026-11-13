# 2号 v1.1 定向补件独立审查

日期：2026-11-13。独审身份：未参与成员补件或主代理验收说明撰写的独立子代理，`gpt-6.1-sol / high`。

审查根为 `private/extracted/Round3_role02/`；对照原v1（2026-11-12真实收件）及前批课程衍生修正版。只读源码、文档、聚合；没有执行成员main、训练、模型新评分或四月评分，没有重开14字段/56效应/429品类的全套原始重建。

## 定向结论

**本次20行区间支持人数修正及约定的解释补件可接受。** 它关闭2号该项数值修复/本人重交缺口，不是3号模型补件，不关闭模型组合尚未测试、3号CV/metadata、5号错误命中CI等其他问题。用户D14本地报告主线已采用，具体模型、主指标和其他待答决定维持未定。

## 源码与数值核实

1. `scripts/r3_evidence.py:93–114` 保留全scope n1/n0用于总分母，先 `ok=np.isfinite(s)`，再按 `yy[ok]` 计算 `pn/qn` 并传入 `d_se`；同时将该pn/qn写入positives_nonmissing/negatives_nonmissing。`r3_common.py` 的cohens_d同样按finite过滤，故SE与点d使用相同观测群体，修法正确。
2. 将新 `training-feature-evidence.csv` 按 `candidate_id+scope` 对照前批 `audit/role02-evidence-recomputed-corrected.csv`：56键唯一且逐键匹配；SE最大绝对差 **0**，下界最大差约 **1.19e-15**、上界约 **1.22e-15**，只是数值序列化级差异。
3. 与原v1相比，该56行表只有 `d_se/d_ci_lo/d_ci_hi` 3列改变；按1e-14绝对容差计，每列恰20行改变，涉及C03/C07/C08/C10/C12 × ALL/0/1/2。`cohens_d`、`auc`变化均 **0行**，其他字段相同。
4. `candidate-screening.csv`、`tables/r3_retained_fields.csv`、`tables/r3_fold_selection.csv`、`field-correlation.csv`、`group-comparison.csv` 按DataFrame值与v1完全相同。`candidate-definitions.csv`仅note变化，字段公式未改。
5. 定向源码diff：`r3_build_candidates.py`无差异；`r3_evidence.py`仅SE支持人数一处修法与注释；`r3_common.py`只改自报说明、SPEC_VERSION及C03已经log警告，筛选阈值未改。原S1–S6不读取CI，故本次改区间不意味着重新选字段或得到新模型收益。推荐仍为G1两数值+缺失指示、G2两数值+缺失指示。

## 解释补件核实

|事项|当前原包位置|结论|
|---|---|---|
|已有log与防重复变换|`feature-spec.md:129`、`HANDOFF.md:60`、`README.md:7–10`、common中C03 note|明确delivery_days_log已经log1p，下游应从通用log步骤排除，不能静默变为双log；这只是接入警告，不表示3号已接入或实际修过模型。|
|区间性质|`feature-spec.md:9`|明确非缺失人数、大样本描述近似、无多重比较校正，不是因果效应/筛选门槛。当前修复不消除缺失选择和跨期稳定性限制。|
|组合外推边界|`feature-spec.md:139`、`README.md:91`、HANDOFF补充说明|明确3号F1/F2与本包组合不同，3号未测本包组合；旧配送/评价比较不能证明本包建议无效。所谓Top10主指标仅是成员旧比较语境，不替代用户尚未确认的最终主指标。|
|自报冻结|`README.md:3–4`、`feature-spec.md:3–5,29`、`HANDOFF.md:5,14`及common文件头|明确21:35为成员自报版本声明，不是事前冻结证明；正式采用及时间另由6号真实登记。没有据该声明推定之前未见结果。|
|既有限制|`README.md:84–92`、`feature-spec.md:131–139`|保留没有模型/分数/命中、已见开发窗口、预计承诺历史版本/源完整性待核、私有候选表未公开等限制。|

## 仍需准确记录的身份与行政边界

- 用户称“之前线3号补一份”，但附件内部版本、源码及内容为 **2号 `R3-role02-feature-v1.1`**；应按真实附件身份收件，不改名成3号模型补件。
- `README.md:90`、`HANDOFF.md:14` 写“收稿已宽限11/14”，这是附件内成员声明。当前未见用户直接确认或权威改期记录，不能自动修改正式截止时间，也不据此回写看板DDL。
- 本包没有新增3号分数/模型/配置证据，因此3号metadata生成、全十月固定群映射CV条件、2号完整组合未测试等记录保持。它也不修正5号另一个命中数CI公式。
- 成员重新交了修正数据，可将2号20行区间“待作者重交”改为“已收到v1.1并定向数值核验”；不能把未见的接收方本人回签、私有逐人表原字节或正式采用一并写成完成。
- 不依据本次补件启动组合测试或挑最终模型；D14线级采用保持，其他问题按用户“稍后回答”处理。

## 后续范围

来源独审完成。等待主代理简短根README候选后，只对该新增验收说明完整顺读一次，之后仅定向复核；最终SHA绑定由同目录回执记录。96项附件hash、smoke全量可行性及图的实际显示由主代理负责，不由本独审冒称重做。
