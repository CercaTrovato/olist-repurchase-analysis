> 原成员交付快照：以下自报状态和历史数字以根目录验收说明为准；课程修正版另列，未覆盖原 ZIP。

# 运行与输入边界

此ZIP为汇总交付，不是独立完整复跑包。没有原始数据、客户键、逐人分数或local_data。不要直接在解压目录运行分析脚本，否则会缺输入。

将scripts/run_round3.py放到已有项目根目录下的scripts中，准备以下外部输入（相对项目根目录）：

- data/H02_candidate_v2.zip：内含snapshot_features.csv、snapshot_labels.csv；指纹见audit/reference-input-versions.csv。
- outputs/H05-km3-v1/local_data/validation_clusters.csv：原H05逐人群号。
- outputs/feedback_round1/local_data/train_audit.local.csv：首轮既有训练群号与特征标签。
- outputs/feedback_round1/local_data/historical_pairs_train.local.csv、historical_pairs_validation.local.csv：历史客户品类缓存。只复用，不在本脚本重建。
- outputs/feedback_round1/results/segment-errors-recomputed.csv：旧模型汇总。本包不重复带入旧轮成果；需从既有项目取得。

所有实际使用输入哈希见audit/source-hashes.csv。H04 v0.4未作为本脚本输入，脚本运行成功不代表该版本验证成功。要重建历史品类缓存需旧轮脚本及原始Olist表，均不含在本包。

Python 3.12；依赖pandas、numpy、scipy、matplotlib。已记录版本见audit/environment.json；scipy版本见requirements.txt。字体依赖C:/Windows/Fonts/msyh.ttc，其他平台需修改为可用中文字体。

```powershell
# 在已有项目根目录执行；使用已安装上述依赖的Python环境
python scripts/run_round3.py
```

本机可用py -3.12，且需设置$env:PYTHONPATH='MEMBER_HOME/Dev\work\Lib\site-packages'。脚本仅重算聚合和图表，不训练模型或聚类；会刷新outputs/round3_role04的生成文件，因此先备份该目录。不会更新本次交付ZIP，也不自动加入交接附录。

本次打包没有运行分析脚本，所有画像及样本量文件按字节复制。打包源码为scripts/package_round3.py，参数是Role01附件所在目录；从原项目运行，目标已存在会拒绝覆盖。脚本中的日期为本次交付日期。
