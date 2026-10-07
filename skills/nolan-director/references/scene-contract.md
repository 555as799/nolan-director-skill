# 连续场次交接与校验

结构数据仅在需要完整方案交接/导出或已有项目数据时使用，普通聊天不用先生成文件。把JSON通过stdin传给scripts/director_engine.py validate -即可只读检查；通过affected查已发生变化的事实/采用决定会影响哪些节点。

根字段：facts、decisions、beats、shots、transitions、claims。每条事实有id/text/status/source，status只可confirmed/proposed/unknown；source为用户材料或出处描述。采用决定有id/text/status/dependencies，status为adopted/proposed/rejected。每个beat有id/purpose/action/change/fact_refs/dependencies。每镜有id/beat_id/action/purpose/camera/sound/fact_refs/dependencies；camera描述位置、运动、构图，数值参数未知可留null；sound描述来源/位置/进入退出。相邻transition有from/to/cut_reason/picture_anchor/sound_bridge。claims记录text/type/source_ids，type为source_fact/editorial_interpretation/original_proposal；只有source_fact要求实际资料ID，未知原片精确参数仍需回原文。

校验可发现空镜头目的、引用未确认事实、重复ID、未批准决定被当锁定条件、缺相邻镜头接缝、无来源的原片断言、时长合计不符与依赖缺失。它无法验证人物是否感人、所有空间是否真实可拍、出处是否被准确解释，或自动识别所有被遗漏的谎报事实；这些由独立反评及专业人工样片审阅负责。

dependency通过ID关联事实/决定/beat/shot。用户改变一个依赖ID时，affected输出依赖它的下游节点；不会自动修改文件或替用户采纳意见。私人项目数据只能存用户自己项目目录，不能写入共享研究包。
