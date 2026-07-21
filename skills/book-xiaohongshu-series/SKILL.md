---
name: book-xiaohongshu-series
description: Create and continue a book-based Xiaohongshu content series with a persistent topic ledger and daily post files. Use when the user asks to generate a Xiaohongshu/小红书 post for a book, create today's next article, continue a book series, build a book topic ledger, or produce book-reading notes that must be serialized, tracked, and saved under book_series/.
---

# Book Xiaohongshu Series

## Purpose

Use this skill to turn a book into a durable Xiaohongshu post series. Maintain a ledger of book topics, generate one post per request from the first pending topic, save the post, and update the ledger so the next request continues correctly.

Default language is Chinese. Write for ordinary adult readers interested in personal growth, finance, society, and practical judgment.

## Directory Contract

Use this layout unless the project already defines a different one:

```text
book_series/<book_slug>.md
book_series/posts/<book_slug>/<topic_id>_<YYYY-MM-DD>.md
```

Use a short ASCII `book_slug`, such as `financial_logic`.

If `book_series/README.md` or project instructions exist, read them first and follow the more specific local convention.

## Workflow

### 1. Resolve the book and ledger

1. Identify the requested book title.
2. Find the matching ledger under `book_series/<book_slug>.md`.
3. If no ledger exists, create one before writing a post:
   - Verify the book title, author, and edition from user-provided notes or credible public sources.
   - Do not invent chapters, page numbers, quotes, or statistics.
   - Build a topic queue that covers the book's main argument, not only viral topics.
   - Give each topic a stable `topic_id` such as `01`, `02`, `03`.
   - Mark every new topic as `pending`.

### 2. Select the next topic

Read the ledger mechanically:

1. Select the lowest-numbered topic with `发布状态：\`pending\``.
2. Do not skip, reorder, or rewrite published topics unless the user explicitly requests it.
3. If the user requests a specific topic number, use that topic and explain if it is already published.

### 3. Write the post

Use the selected topic fields as the source of truth:

- book knowledge point
- underlying logic
- social context
- life scenario
- contrarian angle
- boundaries and forbidden claims

Do not introduce fresh claims that require current data unless you verify and cite them. If no verified external data is used, say so in the fact source section.

### 4. Save and update

1. Save the post to:

```text
book_series/posts/<book_slug>/<topic_id>_<YYYY-MM-DD>.md
```

2. Update that topic in the ledger:
   - `发布状态：\`published\``
   - `发布日期：<YYYY-MM-DD>`
   - `成稿文件：book_series/posts/<book_slug>/<topic_id>_<YYYY-MM-DD>.md`

3. Verify the ledger now points to the saved post and the next topic remains `pending`.

## Post Style

The target is not a short casual note. Write a complete, concise, logically strong, professionally grounded Xiaohongshu article with enough concrete cases to remain readable.

Prefer this structure:

1. **Title**: Use the topic's core concept directly when it gives the series stronger identity, e.g. `金融是跨期安排`. Avoid clickbait.
2. **Opening**: Start from a real-life problem, but do not overdo emotional setup.
3. **Core concept**: Define the book idea precisely in plain Chinese.
4. **Mechanism**: Explain why the concept works. Use terms such as cash flow, risk transfer, credit, contract, liquidity, opportunity cost, incentives, or institutional constraints where relevant.
5. **Case**: Use one concrete everyday case to make the mechanism visible.
6. **Framework**: Provide a small reusable judgment framework, checklist, or classification.
7. **Boundaries**: State what the article is not claiming.
8. **Discussion prompt**: End with one specific question that invites comments.

Good articles should feel worth saving: complete enough to teach a concept, concise enough to finish, and practical enough to use.

## Voice Rules

- Do not mention the author's name in public-facing post text unless the user asks for it. Use only the book title, e.g. `《金融的逻辑》`.
- Do not use exaggerated titles, fear marketing, group antagonism, or absolute claims.
- Do not make personalized financial, investment, insurance, medical, legal, or credit-repair advice.
- Do not recommend specific stocks, funds, insurance products, loans, platforms, or grey-market services.
- Avoid generic advice such as `提升自己`, `做好规划`, or `多学习`; replace it with a concrete action and its boundary.
- Avoid making the post too colloquial. Keep it readable, but preserve conceptual precision and professional vocabulary.

## Output Format

Use this Markdown format for every post:

```markdown
# 标题

# 正文
正文内容

# 话题
#标签1 #标签2 #标签3 #标签4 #标签5

# 事实来源说明
书中观点来自《书名》。如未使用时效性统计数据，写明：本文未使用时效性统计数据。补充必要的非建议声明。
```

Use 5 to 8 relevant hashtags. Do not use the author's name as a hashtag.

## Ledger Template

When creating a new ledger, use this topic block structure:

```markdown
### [01] 知识点名称
- 书中知识点（白话）：
- 底层逻辑：
- 首选社会现状：
- 社会现状的具体表现：
- 受影响人群：
- 形成机制：
- 可核验事实与来源：
- 书中知识点与现状的连接：
- 小红书主题句：
- 生活化场景：
- 反常识切口：
- 内容边界与禁用表述：
- 发布状态：`pending`
- 发布日期：
- 成稿文件：
```

The ledger is an internal control file. It may include author and source details for verification, but public posts should follow the voice rules above.

## Quality Checks

Before final response, check:

- The selected topic was the first `pending` topic unless the user overrode it.
- The post file exists at the expected path.
- The ledger status, date, and post path were updated.
- Public post text does not contain the author's name unless requested.
- The article includes a concept, mechanism, case, framework, and boundaries.
- The fact source section matches what the article actually used.

In the final response, give the saved post path, ledger path, topic title, and next pending topic when useful.
