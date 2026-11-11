# IS6400 小组项目推进与同步

本库每批实质推进完成后，必须完成三处更新：本批成果与当前进度提交并推送 GitHub、核验远端 → 回传总监督更新并回读本地看板 → 发布线上看板并回读。晚到补件、验收状态与任务变化也适用，不能只上传文件而保留旧待办。

- 提交前 fetch，先核组员远端新提交；只纳入本批已核范围，不覆盖他人工作、不 force push、不绕过钩子。仅本人署名，不添加 AI trailer。
- 课程会话维护本课记录，总监督维护共享看板，约定单一写者；无法直接完成某端时明确回传收尾，不能只在本会话结束。
- 完成回执分别列 GitHub 仓库／分支／远端提交、本地看板回读、线上版本和回读结果。任何一处未完成须写原因及下一步，不笼统称“已同步”。
- 普通提交、推送和既定看板发布已获本人持续授权，不重复询问；本人当次明确仅本地、先验收或暂缓某端时例外。仓库可见性及共享范围保持既定设置，原件与第三方私人材料按既有规则保护。
- 本规则不授权代发群消息、邮件、正式提交课程作业或改变访问权限。

本机统一规则：[SUPERVISION.md](D:/上课资料/CityU/_meta/assignment-board/SUPERVISION.md)。线上步骤：[ONLINE-SYNC.md](D:/上课资料/CityU/_meta/assignment-board/ONLINE-SYNC.md)。离开本机时可从[课程库规则](https://github.com/CercaTrovato/cityu-ai-course-notes/blob/main/_meta/assignment-board/SUPERVISION.md)读取同一流程。

## 时间线维护

每批维护 `progress/timeline.json` 的事实、状态变化、依赖与未来计划，并同源生成 `TIMELINE.md` 和 `progress/daily-plan.json`。本人资料库中的本课 `timeline.json` 与此版本保持一致；更新前先核远端，不能用旧本地覆盖新稿。实际完成日期未知留 null，建议日期明确 proposed，history 追加变化。个人助手按 `ASSISTANT-README.md` 使用候选事项，不自动承诺交期或代发消息。
