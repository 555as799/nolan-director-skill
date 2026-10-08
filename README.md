# 诺兰导演 Skill

[English](README.en.md) · **4.1.2 release candidate** · CineMatrix

一个可以安装、持续交流的导演创作 Skill。它用第一人称和作者讨论剧本、表演、镜头、剪辑与声音，在相关时调用诺兰公开访谈和制作资料中的具体经验，把建议落实到眼前的作品。

这是基于公开资料的 **AI 角色演绎**，不是克里斯托弗·诺兰本人或其授权产品。项目提供文字对话、研究资料与工作流程，不包含真人声音克隆或专门训练的模型权重。它运行在客户已经使用的模型之上。

## 给 WorkBuddy 用户

下载 [WorkBuddy 安装包](https://github.com/555as799/nolan-director-skill/raw/refs/heads/main/downloads/nolan-director-4.1.2-workbuddy.zip)（本地构建位于 `dist/`），在 WorkBuddy 的技能页面选择“添加技能 → 上传技能”，导入后确认已经启用。打开新对话，明确调用：

> 使用“诺兰导演”技能，和我持续讨论这部作品。我想拍一个两分钟短片：一个人在海上漂流，感到自由和快乐。只有一位演员、一条小船。先和我聊开场，不急着列完整分镜。

后续像正常对话一样补充材料、追问或否定建议，无需每句重复技能名称。新对话应重新选择或调用技能。安装方式依据 [WorkBuddy 官方技能说明](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market)。客户截图已证明 4.1.0 被实际调用，同时暴露了不合格的对话；4.1.2 修正相关规则，仍待同一宿主复验。

普通使用无需 Python、GPU、额外数据库服务或另配 API 密钥。模型与联网额度沿用 WorkBuddy 账号。完整步骤与故障排查见[给客户的安装说明](给客户的安装说明.txt)。

支持本地 Skills 的其他宿主，可以导入 [通用安装包](https://github.com/555as799/nolan-director-skill/raw/refs/heads/main/downloads/nolan-director-4.1.2-portable.zip) 内完整的 `nolan-director` 文件夹；具体安装目录由宿主决定。应保留整个文件夹，单独复制 `SKILL.md` 会丢失资料库。两种包是不同宿主的包装，不必同时安装。

## 它怎样工作

- **稳定的角色与交谈方式**：首次读取简洁的会话核心，后续承接作者的决定、情绪和修改范围；不把每个故事都改成悬疑、创伤或多时间线。
- **有归属的经验**：明确区分诺兰公开自述、合作者回忆、编辑分析和原创练习。有据的本人经历可在已明确角色扮演的对话中用第一人称转述；其他人的贡献保留姓名。
- **围绕问题取资料**：从“画面漂亮却离人物很远”“预算不够”“演员准备方式不同”等创作困难找到相关资料。已有上下文够用时直接继续，不每轮重读全库。
- **可执行的创作建议**：从人物动作、观众知道什么、摄影位置、声画关系与资源条件推敲选择；作者要求只改一句，就限定修改范围。
- **可带走的项目记录**：作者明确要求保存时，把已确认设定、已采用决定和待选提案分别存入其项目。共享 Skill 不保存客户记忆。

知识库有两种读取路径：宿主直接打开文本索引和知识卡；或在已有 Python 的环境中使用本地 JSON / SQLite 检索。后者是词法检索与人工情境导航，不是向量语义检索服务，也不调用额外收费模型。

## 资料范围与核验

4.1.2 的资料清单为 **204 张卡、73 个来源条目、13 个影片入口**。卡片分为 46 张诺兰公开经历、12 张合作者经历、89 张创作研究及 57 张原创示例。本轮有 37 张卡的相关来源段落已核读；其余继承材料保留逐卡核验状态。

这些计数可以在 [构建摘要](validation/build-summary.json) 和 [规范资料库](skills/nolan-director/assets/library.json) 中复查。卡之间可能讨论同一经历，来源条目也包括工程文档，因此卡数不是独立经历数，来源数不是采访数量。没有声称所有来源已经全文重读。

资料新增包括《致命魔术》的改编与时代表演、《信条》的条件决策、《追随》的结尾自评、《星际穿越》的科学删减与演员准备，以及可核实的文学与电影影响。研究卡保存问题语境、事实短转述、来源定位和使用边界。完整图书、电影、付费采访或真人私下谈话不包含在包内。

文学影响除《Waterland》外，还核实了《双城记》的补读与群像结尾、《美国普罗米修斯》的研究索引与主观改编、奥本海默战后演讲集的阅读影响。最后一项的书名与版本没有在来源中给出，保留未知；这些是本人谈阅读的公开经历，并非我们已经收录或通读整本书。

## 当前验收状态

这是可构建、可安装试用的**发布候选版**。工程检查、检索回归与小样本独立 AI 对话试用用于发现具体问题，不能证明所有问题都能答好，也不能证明已经复制真人的创作能力。

4.1.2 在取消自动身份开场的基础上，补入六项有据的常驻工作偏好，改善简短确认、局部修改、多方帮助及动作呼应。新增两张经核读的合作与观看经历卡。独立代理分别按原专家和新版完成同组八轮提问，盲版本评审均未发现实质违约，也没有认定新版整体胜出；细节与后续窄修见 [本版验证](validation/release-4.1.2.json)。仍未训练模型权重。原始客户截图及真实创作记录不随公开源码分发；发布评测使用合成题。

| 已有证据 | 仍需验证 |
|---|---|
| 构建、资料关联、检索和打包的离线测试；4.1.0 客户调用截图 | 4.1.2 在客户 WorkBuddy 中的实际回复 |
| 独立编写的检索压力问题，以及发现问题后的回归 | 客户所选模型下的多轮稳定性与速度 |
| 保存真实输入输出的小样本 AI 对话试用及独立文本评审 | 人类创作者对实用性、自然度和长期协作的评价 |
| 来源主体与原创示例分离 | 更广泛的一手资料逐项复核与覆盖扩展 |

查看 [开发状态审计](validation/product-readiness.json)、[验收报告](validation/验收报告.md)、[独立对话记录](evals/independent-trials/) 和[行为评测题](evals/behavior-cases.json)。测试发现后用于修复的问题会成为回归题，不能再当作未见过的独立测评。

本版没有进行新的参数训练。旧项目记录过未通过质量验收的训练实验；那些权重没有装入本 Skill。资料检索、提示与流程优化和模型参数训练是不同工作。宿主模型的理解能力、文件访问和上下文长度仍会影响效果。

## 开发与复现

源码目录自包含，不依赖上级工作区、原始 ZIP、私人训练档案或开发者机器路径。使用 **Python 3.10+**，核心构建和检查使用标准库；生成 SQLite 索引需要 Python 所带的 SQLite 支持 FTS5。普通用户的文本读取路径不需要 Python。

在仓库根目录依次运行：

```sh
python build.py
python tests/run_all.py
python audit_readiness.py
python export_source.py
python tests/verify_source.py
```

生成的客户包和源码包位于 `dist/`，包摘要位于 `dist/SHA256.json`。最后一步验证导出的源码在隔离目录里可以重新构建，具体覆盖范围以测试报告为准。发布前应使用本次运行生成的报告，不复用旧版本“通过”的结论。

已有 Python 时，可在仓库根目录查询：

```sh
python skills/nolan-director/scripts/recall.py --query "两位演员需要不同的排练方式" --mode experience --limit 3
python skills/nolan-director/scripts/recall.py --query "预算有限但想保住空间感" --mode craft --backend json
```

`--budget` 限制序列化 JSON 的 Unicode 字符数，不是模型 token 数。结果若标记 `truncated: true`，需要读取其 `card_file` 完整卡片，不能把截断的导航结果当完整事实。

| 文件 / 目录 | 用途 |
|---|---|
| `skills/nolan-director/SKILL.md` | 可独立安装的技能入口 |
| `skills/nolan-director/references/session-core.md` | 会话核心与经验导航 |
| `skills/nolan-director/references/library-index.md` | 无需脚本的资料索引 |
| `skills/nolan-director/scripts/recall.py` | 只读本地检索 |
| `data/` | 自包含的构建输入与迁移记录 |
| `research/` | 已核资料扩充、开源方案取舍 |
| `evals/` | 行为题与实际试用记录 |
| `tests/`、`validation/` | 自动检查及其证据 |
| `release-files.json` | 源码发行允许清单 |

修改源数据后重新构建，不只修改生成的 SQLite。贡献方法见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 开源方法与许可

本项目吸收人物 Skill 的分层角色、按需资料读取、经验归属、持续会话和评估机制，独立实现本地检索与交付流程；没有把研究到的外部人物 Skill 实现代码整体打包进来。具体采用和拒绝的做法见[开源方案记录](research/方案与采用记录.md)与[运行机制审阅](research/runtime-adoption-review.md)。

本轮还按固定提交复核了 [五类人物／导演框架](research/upstream-review-20261008.md)，以及 [RoleLLM 与 Character-LLM 的训练路径](research/distillation-decision-20261008.md)。采用有据的人物判断、证据分级和相关记忆组合；不把合成人物回忆当真实经验，不捆绑未验证的权重或训练环境。当前交付是可安装的 Skill，不是独立训练完成的诺兰模型。

本项目原创代码、指令和编辑内容采用 [MIT License](LICENSE)。第三方电影、书籍、采访原文、名称及其他权利不因本仓库开放而获得授权，详见 [NOTICE.md](NOTICE.md)。数据与权限边界见 [SECURITY.md](SECURITY.md)。
