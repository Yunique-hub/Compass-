# Compass 2.5.1 场景验收与平台 E2E 清单

## A—T 可重复场景验收（2026-08-10）

执行命令：`python -m pytest tests/e2e/test_manual_scenarios_v251.py -q -p no:cacheprovider`。最终结果：20/20 PASS。首次运行的两个失败均为验收代码误用了公开结构/固定文案，不是产品行为失败；修正断言后全部通过。完整断言与可复现输入见 `tests/e2e/test_manual_scenarios_v251.py`。

| 场景 | 结果 | 核心验收 |
| --- | --- | --- |
| A Major False Positive | PASS | “算法学得很痛苦”不写专业，直接启动算法 Tutor |
| B Major Negation | PASS | “不是法学”不保存当前专业 |
| C Third Party | PASS | 同学的专业不进入用户档案 |
| D Target Major | PASS | 法学只进入目标专业，当前专业不被覆盖 |
| E Nursing | PASS | 护理评估/患者安全，无医生鉴别诊断或 Java |
| F Pharmacy | PASS | 药理与合理用药任务，无临床专业串线 |
| G Chemistry | PASS | 化学实验能力，不当作数学专业 |
| H Materials | PASS | 材料 taxonomy，不默认机械 CAD |
| I Psychology Graduate | PASS | 读研路径包含统计、研究方法、文献与研究证据 |
| J Psychology UX | PASS | 就业路径生成用户研究/访谈/产品决策任务，明显区别于 I |
| K Multi Goal | PASS | 法考与律所实习都产生任务，总时长不超过 8 小时 |
| L Assessment Negation | PASS | FCFF=MET，其余三项=MISSING |
| M Assessment Uncertainty | PASS | WACC 不确定为 PARTIAL/UNCLEAR，置信度低于 0.9 |
| N Opportunity Cost | PASS | 直接回答，不进入 onboarding |
| O IRAC | PASS | 直接解释规则、分析与结论，不进入 onboarding |
| P Resource Isolation | PASS | 英语写作不补 Java/Spring 资源 |
| Q Cross Major | PASS | 保留土木，生成数据分析桥接项目 |
| R Double Major | PASS | 保留数学+经济并比较量化/经济学研究 |
| S Unknown Major | PASS | 进入学科族 fallback，并明确细节需验证 |
| T Stress Load | PASS | 实际容量至少减半、任务不超过一个，并给支持性回应 |

## 已运行的本地完整对话模拟（2026-08-10）

执行命令：`python -m scripts.demo.major_agnostic_scenarios`。结果：14/14 通过。

- [x] 计算机 + Python 后端实习：生成 FastAPI 接口与自动化测试任务。
- [x] 金融 + 投行：生成 DCF 估值模型任务，无后端模板串线。
- [x] 法学 + 法考 + 律所：保留多目标并生成 IRAC/法条任务。
- [x] 医学 + 内科学：进入临床推理 Tutor，不转职业规划。
- [x] 机械 + 机器人：生成 CAD/工程证据。
- [x] 生物 + 读研：生成论文证据提取与研究方法路线。
- [x] 心理 + 读研：生成研究设计任务。
- [x] 视觉设计 + UI/UX：生成用户流、线框和走查任务。
- [x] 英语 + 方向未知：输出差异化探索路径，不强行教师路线。
- [x] 教育 + 教学能力：生成目标—活动—评价教案。
- [x] 葡萄与葡萄酒工程：进入长尾 fallback，不报 unsupported。
- [x] 土木转数据分析：保留原专业并生成桥接数据项目。
- [x] 数学 + 经济双专业：保留双专业并比较量化/研究路径。
- [x] 大一未分流：进入低成本探索，不默认程序员路线。

## 平台 E2E 待执行 T01—T19

平台 E2E 只在实际上传后执行；以下是验收步骤，不是假装已测结果。每项记录输入、截图/原始 JSON、实际输出、通过/失败和问题编号。

- [ ] T01 新用户尚未确定就业方向：输出 2—4 个方向，不生成正式长期计划。
- [ ] T02 用户信息不足：只追问当前步骤缺失的 1—3 项，不编造。
- [ ] T03 用户确认主方向和备选方向：分别记录角色、时间与状态。
- [ ] T04 方向确认但未提供目的地：请求城市/区域，不冒充本地分析。
- [ ] T05 目的地招聘快照有效：展示样本、来源、区间、版本和可追溯技能统计。
- [ ] T06 招聘样本不足或过期：标低置信度并提供 JD/范围降级。
- [ ] T07 单份 Java 后端 JD：提取技能、经验、项目、学历、软技能和加分项。
- [ ] T08 多份 JD 累积：只按实际输入统计并保留 JD ID。
- [ ] T09 招聘需求与用户证据对比：无证据不判定掌握，输出差距与验证方式。
- [ ] T10 计划时间超预算：移除低优先核心任务，总时长回到预算。
- [ ] T11 用户改变方向或目的地：旧快照、差距和计划失效并重新确认。
- [ ] T12 成长档案重新导入：显式字段、确认状态、快照版本不丢失。
- [ ] T13 自动长期记忆写入：未确认方向仅临时，确认目标进入结构化存储。
- [ ] T14 记忆冲突：请求确认，不静默覆盖。
- [ ] T15 用户要求忘记：结构化、向量、索引、缓存和临时副本全部删除。
- [ ] T16 向量库不可用：降级到结构化字段 + 档案模式，流程继续。
- [ ] T17 普通压力表达：先关怀，任务降载，不诊断。
- [ ] T18 危机信号：停止学习引导并执行经过核验的安全转介。
- [ ] T19 脚本输出异常：stdout 保持结构化 JSON，诊断进入 stderr，提供降级。
