# 生成图与发布字节的校验说明

`plot-manifest.json`及独审最终绑定记录的是本地生成阶段文件字节。公开导出为UTF-8/LF，并移除3张SVG的行尾空白；形状、标签、数值和PNG没有变化。原始生成文件不覆写，因此这里保留原生成哈希。

下载GitHub文件时，请用[public-evidence-manifest.json](public-evidence-manifest.json)的`files`检验**已发布字节**；对照原生成与规范化的3项SHA，见[normalization-receipt.json](normalization-receipt.json)。它们不是两个模型/实验版本，也不改变独审的科学结论或任何候选采用状态。

课程回传绑定的本地原公共清单仍作为最初生成证据保留；本GitHub清单额外纳入这两份发布说明。无训练/重算/四月评价/正文改写或元数据更新，路线仍待全组投票。
