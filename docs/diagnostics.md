# 诊断代码

`DiagnosticCode` 定义于 `src/mathlens/enums.py`，覆盖整个项目的长期诊断语义。
按问题性质分组，不按 S1、功能上线顺序或某个界面的文案划分。
诊断、补充项和边界异常内部均引用该枚举，不再散写字符串。

## 1. code、status、severity 和 stage

| 字段 | 回答的问题 |
|---|---|
| code | 具体发生了什么 |
| status | 本次处理最终处于什么状态 |
| severity | 这条消息的级别 |
| stage | 问题发生在哪个阶段 |
| field_paths / field_path | 涉及哪个输入字段 |

同一原因码不固定绑定一种状态或级别。例如 divergence_detected 可以伴随
成功的发散判定；steps_unavailable 可以只是计算成功后的提示。
capability_unavailable 表达当前后端、配置或安装环境缺少必要能力，既适用于
长期可选后端，也可用于开发中的能力边界，不为图片、定义域等分别增加一批
临时的 *_not_supported 代码。具体能力由 stage、字段位置和 message 说明。

## 2. 请求、协议和容量

| code | 使用场景 |
|---|---|
| invalid_request | 模型、字段类型、枚举值或结构无效 |
| invalid_json | JSON 文本、编码、重复键或数值表示不合法 |
| schema_version_mismatch | 公开契约版本缺失、类型错误或不兼容 |
| protocol_version_mismatch | worker 协议版本缺失、类型错误或不兼容 |
| resource_limit_exceeded | 输入、输出、像素数、阶数、精度等超过允许限制 |
| capability_unavailable | 当前后端或配置不能提供请求所需能力 |

字段类型错误统一为 invalid_request，用字段位置区分 input、latex、operation
等，不再同时使用 invalid_input。语法或数学含义问题使用对应领域的原因码。

## 3. 图片与 OCR

| code | 使用场景 |
|---|---|
| media_not_found | 图片资源标识未知、失效或已释放 |
| invalid_image | 图片内容损坏或不能作为图像解码 |
| invalid_image_region | 区域坐标、尺寸或范围不合法 |
| recognition_failed | 有效图片中未能识别出可用公式 |
| ocr_confirmation_required | 存在候选或不确定识别结果，需要用户确认 |

ImageInput 的字段类型错误仍属于 invalid_request。无效图片不等于识别失败；
没有接入 OCR 也不等于图片损坏。OCR 确认后创建带 source 的 LatexInput，
后续公式语法问题才属于 invalid_latex。

## 4. 公式与数学参数

| code | 使用场景 |
|---|---|
| invalid_latex | 公式为空或语法不合法 |
| ambiguous_expression | 公式存在多个可能的数学解释，需要确认 |
| parser_failed | 解析器发生非预期故障，不能据此判定输入有错 |
| missing_field | 必要参数缺失，没有更具体的缺失代码时使用 |
| missing_operation | 需要用户选择运算 |
| missing_variable | 需要用户指定目标变量 |
| missing_bound | 定积分等请求缺少必要边界 |
| ambiguous_operation | 有多个可能的运算意图，需要用户选择 |
| conflicting_arguments | 原式、显式参数或符号声明相互矛盾 |

latex=123 属于 invalid_request；latex="" 属于 invalid_latex。合法但后端
无法处理的数学结构属于 capability_unavailable，不能说公式语法无效。
已知缺失代码可同时用于 Diagnostic 和 InputRequest；需要用户修改时使用
InputRequest 明确字段或候选，不强制重复创建内容相同的 Diagnostic。

## 5. 数学计算与结果

| code | 使用场景 |
|---|---|
| symbolic_not_completed | 符号方法返回未完成的数学内容 |
| numeric_not_converged | 数值方法未满足收敛要求，不代表没有数学解 |
| computation_failed | 数学后端或算法执行异常，不能作为无解结论 |
| divergence_detected | 已有依据确认发散，不表示普通执行错误 |
| result_validation_failed | 候选结果未通过适用的数学约束或代回检查 |
| steps_unavailable | 无法提供请求的推导步骤，不自动使答案失败 |
| approximation_unavailable | 无法提供附加近似值，不自动使精确答案失败 |

无解、全集、精确值和部分解首先通过结果模型表达，不另造错误码。
诊断代码也不替代 completeness、conditions 或 steps.status。

## 6. 执行、任务与输出

| code | 使用场景 |
|---|---|
| deadline_exceeded | 总执行预算耗尽 |
| cancelled | 已取消的执行或任务 |
| worker_failed | worker 崩溃、EOF 或未能正常交付结果 |
| cleanup_failed | 无法在清理预算内确认资源回收 |
| job_not_found | 后台任务标识未知或已过期 |
| serialization_failed | 结果无法转换或编码成合法公开数据 |
| internal_error | 边界捕获的非预期内部故障，无法归入更具体原因 |

先使用能够确定的具体原因，不把所有异常归为 invalid_latex 或 internal_error。
任务接收取消请求时不提前宣称 cancelled；状态仍遵循任务回收约定。

## 7. Python 与 JSON 的兼容规则

内部写法：

```python
code=DiagnosticCode.INVALID_IMAGE
```

JSON 中仍为 `"code": "invalid_image"`。枚举值一旦使用不得随文案或开发阶段
改名。message 可以改进或本地化，调用方只根据稳定原因码处理。

Diagnostic.code 和 InputRequest.code 保留 str 类型：StrEnum 成员是字符串，
同时允许消费者保存未来版本的未知代码。codec 对已知代码恢复枚举，
未知代码保留原字符串，不把未知诊断原因当成非法模型标签。
枚举使用 unique 禁止意外的同值别名。
