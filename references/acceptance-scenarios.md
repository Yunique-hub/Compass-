# Acceptance Scenarios

仅在验证 Skill、处理相似边界或修改核心规则时读取。结果必须满足语义不变量，不要求逐字输出。

| 场景 | 输入 | 必须满足 |
| --- | --- | --- |
| A | 算法学得很痛苦。 | 不识别法学，不写 Major，直接帮助或启动算法 Tutor |
| B | 我不是法学专业。 | 不保存 Law current major |
| C | 我的同学是法学专业。 | 不修改用户 Major |
| D | 我想转法学。 | 记录 target，current 不被覆盖 |
| E | 我是护理学大二，想提升专业能力。 | nursing task；无医生鉴别诊断和 Java |
| F | 我是药学大二，想提升专业能力。 | 药理/合理用药等药学真实性 |
| G | 我是应用化学大二，想提升专业能力。 | chemistry；不当数学专业 |
| H | 我是材料科学大二。 | materials；不默认机械 CAD |
| I | 我是心理学大二，准备以后读研。 | graduate pathway；统计、研究方法、文献、研究证据 |
| J | 我是心理学大二，想做 UX Research。 | 用户研究/访谈/产品证据，明显区别于 I |
| K | 我是法学大三，准备法考，也想找律所实习，每周 8 小时。 | 两个 Goal 都有任务，总时间不超 8 小时 |
| L | FCFF 做完，但 WACC、终值、敏感性没做。 | `MET / MISSING / MISSING / MISSING` |
| M | WACC 算了，但不确定方法对不对。 | 不能高置信 `MET` |
| N | 什么是机会成本？ | 直接回答，不 onboarding |
| O | IRAC 是什么？ | 直接回答，不 onboarding |
| P | 英语写作资源 | 不推荐 Java/Spring filler |
| Q | 我学土木，但想转数据分析。 | 保留土木，生成数据桥接计划 |
| R | 我是数学和经济双专业，不知道走量化还是经济学研究。 | 保留双专业并比较路径 |
| S | 我是葡萄与葡萄酒工程大二，想找行业实习。 | 诚实 fallback，不 unsupported |
| T | 最近压力很大，这周真的学不动。 | 支持性回应；实际降低任务与时间 |

跨会话不变量：

1. confirmed major 可恢复；
2. wrong candidate major 不恢复；
3. current topic 不永久占据专业；
4. changed goal 使用新目标并保留有界历史；
5. evidence trust 原样保留；
6. self-report 不提升 verified competency。

通用性检查：替换为未列出的专业、目标和任务时，仍应通过 `Domain → Competency → Practice → Evidence → Criteria` 生成合理结果，而不是依赖场景关键词。
