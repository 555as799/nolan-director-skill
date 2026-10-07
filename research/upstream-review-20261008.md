# 人物 Skill 框架复核与本项目采用边界

核查日期：2026-10-08（Asia/Shanghai）。本次重新读取公开仓库的实际运行文件、说明和许可，并与本项目 4.1.1 的入口、会话核心、检索、项目续谈及更新协议对照。没有执行上游脚本，没有导入人物台词、模型权重、聊天记录或整套人物产物。本报告说明可复查的机制选择，不代表所有开源项目已研究、上游效果已复现或当前宿主对话已验收。

## 固定版本和实际读取范围

下列提交由各仓库 GitHub REST `commits?per_page=1` 返回；文件随后按该提交读取。提交日期是上游记录，本次读取日期不等于上游更新时间。

| 项目 | 固定提交 | 提交日期（UTC） | 许可检查 |
|---|---|---|---|
| Tomsawyerhu/Persona-Skill | `071297ce369d291db453b7376e9c94ff8e3e9383` | 2026-04-13 | 本次完整目录中未找到许可证文件；仓库 API 的 license 为 null，README 也未见授权条款。只研究机制，不将公开可读误写为已确认开源授权。 |
| agenmod/immortal-skill | `cdab91b37982d0d3ca78eb2da6727a8f75d8bca8` | 2026-04-15 | 已读 [MIT LICENSE](https://github.com/agenmod/immortal-skill/blob/cdab91b37982d0d3ca78eb2da6727a8f75d8bca8/LICENSE)。 |
| LC1332/Chat-Haruhi-Suzumiya | `290bf4ad22076156083804013012847a77c0646c` | 2024-02-16 | 已读根目录及 ChatHaruhi2.0 的 Apache-2.0 LICENSE；README 单列角色数据 CC BY-NC 4.0。代码与数据许可不可混同。 |
| momozi1996/DirectorAgents | `1a9e8047d9ed328968030341cfe146bd90712584` | 2026-05-11 | 已读 [MIT LICENSE](https://github.com/momozi1996/DirectorAgents/blob/1a9e8047d9ed328968030341cfe146bd90712584/LICENSE)。 |
| wuwangzhang1216/DirectorSKILL | `c65ae0d14457053efb1e354c7e7f7e120d97fad1` | 2026-08-31 | 已读 [MIT LICENSE](https://github.com/wuwangzhang1216/DirectorSKILL/blob/c65ae0d14457053efb1e354c7e7f7e120d97fad1/LICENSE) 与 README 的作品版权范围说明。 |

### Persona-Skill：人物判断先于场景检索

实际读取：[README](https://github.com/Tomsawyerhu/Persona-Skill/blob/071297ce369d291db453b7376e9c94ff8e3e9383/README.md)、[角色运行合约](https://github.com/Tomsawyerhu/Persona-Skill/blob/071297ce369d291db453b7376e9c94ff8e3e9383/skills/persona/references/runtime/roleplay_contract.md)、[维度目录](https://github.com/Tomsawyerhu/Persona-Skill/blob/071297ce369d291db453b7376e9c94ff8e3e9383/skills/persona/references/extraction/dimension_catalog.md)、[模块构建器](https://github.com/Tomsawyerhu/Persona-Skill/blob/071297ce369d291db453b7376e9c94ff8e3e9383/skills/persona/scripts/extraction/build_persona_modules.py)、[模块选择器](https://github.com/Tomsawyerhu/Persona-Skill/blob/071297ce369d291db453b7376e9c94ff8e3e9383/skills/persona/scripts/runtime/select_persona_modules.py)、[提示渲染器](https://github.com/Tomsawyerhu/Persona-Skill/blob/071297ce369d291db453b7376e9c94ff8e3e9383/skills/persona/scripts/runtime/render_roleplay_prompt.py)。

构建器将高优先级维度与 voice、contract 组成常驻部分，其余维度与情境按需加入。合约要求保留人物分类问题、判断取舍和说明理由的方式，而非仅保留名言；同时区分直接证据、证据支持的综合和新推演。选择器依赖外部 scene 标签，并非通用语义路由器；缺失模块还能被跳过或返回空内容，不能因为有代码便认定健壮性已验证。

本项目已有短入口、会话核心、条件读取、持续角色和事实归属。尚值得补齐的是：把有来源的诺兰判断偏好真正放进常驻核心，而不只把通用合作原则常驻、把人物事实全部藏在按需卡片中。不采用固定姓名前缀、人物融合和完整上游运行环境；未确认许可，不复制其源码。

### immortal-skill：多个维度和证据冲突

实际读取：[README](https://github.com/agenmod/immortal-skill/blob/cdab91b37982d0d3ca78eb2da6727a8f75d8bca8/README.md)、[merge-policy.md](https://github.com/agenmod/immortal-skill/blob/cdab91b37982d0d3ca78eb2da6727a8f75d8bca8/recipes/merge-policy.md)、[skill-assembler.md](https://github.com/agenmod/immortal-skill/blob/cdab91b37982d0d3ca78eb2da6727a8f75d8bca8/prompts/skill-assembler.md)。

它区分做事方法、互动、记忆、人格；公众人物入口先读取人格和互动。合并规则保留证据级别、跨维度冲突和增量记录。对本项目有价值的是独立记录观点、经历与新建议，不能用资料条数代替人物覆盖，也不能把较新的采访自动当成对旧电影制作事实的否定。

对应本项目 `update-protocol.md`、卡片事实/迁移/边界字段与项目续谈协议。已有这些机制，无须另装一套蒸馏引擎。没有采用模板直接给所有产物套 MIT、按新旧时间机械覆盖事实、从私人聊天记录提炼人格等路径。

### ChatHaruhi：角色、相关记忆、历史和当前问题分别组合

实际读取：[ChatHaruhi.py](https://github.com/LC1332/Chat-Haruhi-Suzumiya/blob/290bf4ad22076156083804013012847a77c0646c/ChatHaruhi2.0/ChatHaruhi/ChatHaruhi.py)、[README](https://github.com/LC1332/Chat-Haruhi-Suzumiya/blob/290bf4ad22076156083804013012847a77c0646c/README.md)、[根 LICENSE](https://github.com/LC1332/Chat-Haruhi-Suzumiya/blob/290bf4ad22076156083804013012847a77c0646c/LICENSE)、[运行目录 LICENSE](https://github.com/LC1332/Chat-Haruhi-Suzumiya/blob/290bf4ad22076156083804013012847a77c0646c/ChatHaruhi2.0/LICENSE)。

`chat()` 依次加入角色提示、检索故事、对话历史和当前问题；`add_story()` 以向量搜索取得故事并限制故事预算，`add_history()` 使用独立历史预算。这里是模型调用和检索组装，不是把安装动作变成训练。

本项目对应角色核心、`recall.py` 的有预算检索以及宿主提供的历史；项目卡负责经用户确认的跨次续谈。没有接入它的向量服务、旧模型接口、角色下载器或角色数据。当前没有证据表明再加入它会比现有文件读取/SQLite 更改善这次开场和泛化问题；需在相同模型与新问题上分别比较角色核心、资料检索的增益。

### 两个现成 Nolan 模块：可借交付方式，不能当完整人物资料

DirectorAgents 实读 [Nolan SKILL](https://github.com/momozi1996/DirectorAgents/blob/1a9e8047d9ed328968030341cfe146bd90712584/skills/christophernolan-perspective/SKILL.md) 和 [研究页](https://github.com/momozi1996/DirectorAgents/blob/1a9e8047d9ed328968030341cfe146bd90712584/skills/christophernolan-perspective/references/research/01-core-research.md)。前者以风格标签及固定五栏回答为主；后者主要回指 SKILL 与其他目录，没有给该人物模块补上可核采访经历。采用独立人物 Skill 的包装思路，未导入其人物陈述或未标来源的引语。

DirectorSKILL 实读 [README](https://github.com/wuwangzhang1216/DirectorSKILL/blob/c65ae0d14457053efb1e354c7e7f7e120d97fad1/README.md) 和 [Nolan 模块](https://github.com/wuwangzhang1216/DirectorSKILL/blob/c65ae0d14457053efb1e354c7e7f7e120d97fad1/references/director_styles/10_nolan.md)。它把制作流程和导演风格参数分开，给相同控制场景做不同风格版本，适合启发可比较的评估。本项目只在作者需要制作文件时调用相应工具；不把三条线倒计时、固定焦段/时长、禁止情绪散文等预设转为诺兰历史事实或本产品的硬规则。

## 此次建议补齐的两处

以下是对 4.1.1 的差距判断；是否在新版本完成应以该版本实际文件与验证记录为准，不能把建议当作已完成。

1. **常驻的、带证据的判断画像。** `session-core.md` 当前的创作立场主要是普适的良好协作原则。建议压缩加入四至六个公开工作偏好，每项同时给适用条件和核查入口，让人物判断在未触发某张经验卡时仍然成立。不要从作品猜私生活或潜意识，也不要把画像作为每答的固定栏目。
2. **把人物辨识度纳入同题对照。** 对同一个新问题分别加载通用导演协作原则、完整人物核心、人物核心加相关经历，再由不知道配置的评审判断：哪项取舍确实由资料支持，经验是否改变了具体建议，是否尊重作者更正。不是数电影名或第一人称句子，也不是给自己回答打一个总分。现有截图暴露的入口问题不能用此前静态通过或代理评审分数抵消。

### 可直接用于画像、已重新读到的公开依据

| 建议的工作偏好（本项目编辑综合，不是原话） | 本次实读依据 | 对原有过度简化的校正 |
|---|---|---|
| 允许先从抽象情绪和故事目标开始，再寻找可实现的技术方案 | [ASC 2023](https://theasc.com/articles/christopher-nolan-on-oppenheimer)，关于 Hoyte 创新的问答；同篇后段讨论 LED 互动照明 | 不能先声称抽象感受拍不出来；偏好胶片也不等于拒绝新技术。既有 EXP-ASC01/02 尚未专门覆盖这一段。 |
| 用相机所处的空间和人物视点组织观看 | 同一 ASC 问答的彩色/黑白视点段；[DGA 2012](https://www.dga.org/craft/dgaq/issues/1202-spring-2012/dga-interview-christopher-nolan) 关于跨片风格常量的回答 | 是主观关系的判断，不是所有题材套一套焦段；可连接 EXP-ASC01。 |
| 结构规定观看的时间经验，同时给演员探索的空间 | [DGA 2017](https://www.dga.org/craft/dgaq/issues/1703-summer-2017/wwii-dunkirk)，不同位置/时间结构以及 Rylance 即兴排练两段 | 严格结构和演员自由可以并存；不是凡事三条线，可连接 EXP-DGA17A/B。 |
| 文学、梦与记忆可以提供组织时间的方法；画框外仍有世界 | DGA 2012 关于 Waterland、The Wall 和 Blade Runner 的连续问答 | 允许主观联想，不先拿生理断言否定它；可连接 V4-N003、EXP-DGA12A。 |
| 表演方法随演员需要改变，技术效率不应吞掉有价值的尝试 | DGA 2012 关于 Guy Pearce 追加一条及 Pacino/Swank 准备差异的回答 | 不是统一强制表演方式，可连接 QA12-D01/D02。 |

BFI 页面本次首次打开返回了索引内容，后续定位读取返回错误；本报告没有把未重新取得的 BFI 段落算作本轮重新核验。上表依据是本轮实际读到的 ASC 与 DGA 正文，书籍本身未全本阅读。

## 可宣称与不可宣称

- 可以说已复核这五类相关实现，独立采用了人物常驻核心、按需资料、证据归属、项目与公共库分离等具体机制，并说明尚在补齐的环节。
- 不能说已融合所有人物 Skill、已验证上游全栈效果、已吸收真人全部经验，或把工程打包叫作模型权重训练。
- 本轮没有运行目标 WorkBuddy 模型的真实对话；也没有证明新版本整体超过原专家。版本交付与这些质量结论必须分别记录。
- 本项目源码不捆绑上游实现。公开访谈的必要研究转述保留来源，不把第三方采访、书籍、电影或角色数据重新授予 MIT。
