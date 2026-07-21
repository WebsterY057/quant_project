# 书籍小红书系列台账

每本书由 `02_social_context_agent.md` 在此目录生成一份主题台账：

```text
book_series/<book_slug>.md
```

台账完整记录该书的全部知识点、各自对应的社会现状、可用事实来源、小红书主题句与发布状态。`03_xiaohongshu_action_agent.md` 每次运行时读取首个 `pending` 主题，生成一篇成稿并更新状态。

成稿保存位置：

```text
book_series/posts/<book_slug>/<topic_id>_<YYYY-MM-DD>.md
```

默认采用“按请求日更”的方式：用户说“生成今天的下一篇”时，生成下一条待发布主题。若需要在固定时间自动执行，需要另行配置自动化任务和发布时间。
