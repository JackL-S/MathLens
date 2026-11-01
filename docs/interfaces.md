# 全项目接口契约

本文定义全项目的长期接口，不按里程碑限制模型，不代表这些功能已经实现。
Python 字段与类型以 `src/mathlens/schemas/`、`enums.py` 为准；本文定义
跨字段约束、流程和 JSON 语义。当前只有模型与函数签名，所有服务入口均显式
抛出 `NotImplementedError`，没有计算、OCR、校验器、JSON codec 或进程后端。

模型按输入、运算、请求、诊断、准备、识别、结果和任务分组，具体文件、类型
索引和依赖关系见[模型组织说明](schemas.md)。业务模块仍从 `mathlens.schemas`
统一导入；拆分不改变已有模型字段、默认值或示例 JSON。

## 1. 边界与调用关系

```text
CLI / Web / 桌面
  ├─ media.register_media → MediaResource
  ├─ ocr.recognize → RecognitionResponse
  ├─ application.prepare → PreparationResponse
  ├─ application.compute → ComputeResponse
  ├─ application.run → PreparationResponse | ComputeResponse
  └─ jobs.submit / get_job / cancel_job
              ↓
       execution.execute / worker_main
              ↓
       OCR / parsing / solving / steps
              ↓
       公开模型 → codec / rendering
```

- Python 模块间传模型；JSON 只用于进程、HTTP、文件和 CLI JSON 输出等边界。
- 解析器与计算器的第三方对象只存在于 worker 内部，不进入公开模型。
- 准备也可能解析和识别，必须受超时和取消控制；不限定在父进程执行。
- `run` 是一个完整任务，内部阶段共享预算，不递归启动新的公共 execute。
- 算法模块的内部表达式类型由后端实现时确定，不在公开 API 中承诺 SymPy AST。
- 类型集合覆盖设计范围；当前可用能力只以 `get_capabilities()` 为准。

## 2. 请求、运算和符号

`ComputeRequest` 表示用户意图，字段为 `input / operation / symbols /
preferences / schema_version`。`operation=null` 表示请求推断；显式运算中
缺少目标变量等字段也可以进入准备阶段。缺少必需顶层结构、字段类型错误、
未知标签属于无效请求；可补充的数学参数缺失返回 `needs_input`。

输入为 `LatexInput | ImageInput`，通过 `kind` 区分：

- LaTeX 保留用户原文；`source` 可记录识别结果来源的图片和区域。
- 图片通过 `media_id` 引用资源，不把文件路径、URL 或二进制塞进计算请求。
- 图像区域为原图像素坐标；宽高为正，原点非负，不得超出图像边界。
- 资源注册校验实际图片格式，不仅检查声明的 MIME 类型；任务持有资源引用。
- 调用方释放资源不影响已提交任务；历史快照的图片标识可能过期，但已确认
  LaTeX 计算不应再次读取原图。显式重新识别则需要重新注册有效资源。

`operation` 是带 `kind` 标签的联合，不再使用通用 variables 字段：

| kind | 模型 | 参数规则 |
|---|---|---|
| evaluate | EvaluateSpec | substitutions 的变量唯一，值为 LaTeX |
| simplify | SimplifySpec | 无需目标变量，不暗中追加假设 |
| differentiate | DifferentiateSpec | targets 顺序有意义，order 为正整数 |
| integrate | IntegrateSpec | limits 从内到外；上下限都空为不定积分 |
| solve_equation | SolveSpec | unknowns 唯一；solution_domain 约束解集 |
| limit | LimitSpec | variable、point 在准备完成时必填；方向明确 |

同一请求中的 `input.latex` 可包含方程组或运算符；准备阶段检查其结构与
显式参数是否一致。导数、积分等运算符只能应用一次，冲突不得静默覆盖。
方程组、多变量、混合偏导等是否支持由能力声明与结构检查共同决定。

积分只填一个上下限时返回 `needs_input`；无穷边界使用 LaTeX `\infty` 等
数学文本。普通积分不隐含柯西主值。未支持的积分语义返回 `unsupported`。

`symbols` 使用稳定的符号名标识，`latex` 仅声明对应写法。重复名称、标识映射
歧义与矛盾假设必须诊断。未知或空的假设不等于 false，不额外推断变量为实数。

以下概念严格区分：

| 信息 | 位置 | 含义 |
|---|---|---|
| 解集范围 | SolveSpec.solution_domain | 允许的未知量解 |
| 符号假设 | SymbolDeclaration.assumptions | 对符号的数学声明 |
| 积分边界 | IntegrationLimit | 运算本身的上下限 |
| 搜索区间/初值 | NumericOptions | 数值方法的搜索信息 |

`preferences.method` 是唯一的方法策略：symbolic_only / symbolic_first /
numeric_only。默认符号优先；不得因缺少数值参数就擅自构造搜索区间。
`SolveSpec.numeric` 只规定数值求解参数，不覆盖策略。symbolic_only 与显式
数值求解参数冲突时返回 `needs_input + conflicting_arguments`。

`NumericOptions.significant_digits` 规定数值求解精度，preferences 中同名字段
规定附加近似展示精度。两者均为正整数，受后端能力限制。搜索区间下界须小于
上界，变量必须是未知量；初值、区间的组合由具体方法检查。不定积分不回退
为一个数值，数值根的数量不证明完整性。

## 3. 准备、预览与确认

`prepare(request, *, options=None, control=None) -> PreparationResponse`。

准备包括输入检查、可选 OCR、规范化、解析预览、意图推断、能力与冲突检查。
原始输入不覆盖；格式修改记录到 `NormalizationChange`，不擅自补括号或等号。
`preview` 只反映解析后的含义，不能宣称与原文必然等价。

| status | problem | input_requests |
|---|---|---|
| ready | 必须存在 | 必须为空 |
| needs_input | 必须为空 | 至少一个可操作的补充或确认项 |
| unsupported / error / timeout / cancelled | 必须为空 | 通常为空 |

`PreparedProblem` 是独立、不可变、可序列化的问题快照：包含原始来源、确认后
公式、具体运算、符号与假设、结果偏好和清理记录。运算参数已充分，不再等待
推断。缺少变量、冲突或图片歧义时不能生成 ready 快照。

`InputRequest.field_path` 指向 ComputeRequest，采用 JSON Pointer；空字符串
指向根。`InputChoice` 可携带公式候选或完整运算候选。调用方将选定内容写回
请求再 prepare，不把 choice_id 当服务端会话令牌。OCR 确认后将 input 替换为
LatexInput，并保留 source；多个区域组合时必须由用户确认组合后的完整公式。
只需要候选而不计算的调用方可以独立调用 `ocr.recognize`。

OCR 每个区域包含有序候选；confidence 为 [0, 1] 或 null，不保证候选正确，
也不要求不同后端置信度可直接比较。success 至少有一个有效候选，否则通过
诊断说明识别失败；需要用户修正时可以返回 needs_input 和已有区域。

修改公式、运算、变量、假设或结果偏好后重新准备，不原地改快照。
快照不是免校验凭证：从 JSON 恢复后仍须检查版本、数学约束和当前能力。
PreparedProblem.latex 对求值、化简、求导、积分和极限表示运算对象，运算符及
上下限已经移入 operation；对求解表示完整方程或方程组，不预先变成解。
独立 compute 可重新解析快照文本；单次 run 可在 worker 内复用解析结果，
无需强制重复解析。解析器不可提前丢失分母排除点等原式约束。

## 4. 计算结果、近似、条件与步骤

`compute(problem, *, options=None, control=None) -> ComputeResponse`。

执行状态与数学结果性质分别表达：

| 场景 | status | result_kind | completeness |
|---|---|---|---|
| 完整有限精确解 | success | exact | complete |
| 确认无解 | success | exact | complete |
| 精确表达式 | success | exact | not_applicable |
| 数值根但未证明完整 | success | approximate | unknown 或有证据的 partial |
| 仍有未完成项 | unsupported | mixed / unevaluated | 依结果确定 |
| 已确认发散 | success | exact | not_applicable |
| 无结果的错误/中止 | error / timeout / cancelled | none | not_applicable |

`mixed` 表示主结果内含不同性质的内容，包括已求值与未求值的组合，或精确和
近似组成项。可分别表示的元素使用各自的 result_kind；无法拆分的表达式整体
标为 mixed，不通过解析 latex 猜测性质。带条件的精确答案仍然是 exact。
只附加小数近似时，主结果仍为 exact，不因为 approximations 非空变为 mixed。

`MathValue` 的公开变体：

- expression：表达式及性质；
- finite_set：元素列表，空列表明确表示空集；
- symbolic_set：全集、无限集、条件集等整体表示；
- solution_assignments：方程组分支，每个分支是显式变量赋值和条件；
- divergent：positive_infinity / negative_infinity / does_not_exist；
- unevaluated：尚未求出的数学内容。

空解集与执行失败不同。空集只有在 completeness=complete 时表示确认无解；
不完整搜索没有找到根不能声明无解。ConditionSet 不应标为完整已求解。
completeness=partial 需要已知剩余部分未解决的证据；仅“不保证全部找到”
使用 unknown。全集可以使用 symbolic_set 且标记 complete。

`value=null` 必须对应 result_kind=none、latex=null。存在 value 时顶层 latex
是完整答案展示，由计算侧生成。表达式、有限集和赋值中的数值使用 text/latex
字符串，不丢精度；text 不是可执行代码，也不是承诺可恢复的 AST。

成功计算响应必须附上实际使用的 problem 快照，记录已解析的运算、解集范围、
符号假设和数值搜索参数；自动判断后的 run 调用也能据此复现。提前失败无法
形成有效问题时 problem 可为空，不把未确认输入伪装成快照。

`conditions` 保存答案成立条件；scope 非空时是相对 ComputeResponse 的 JSON
Pointer，空串作用于直接所属对象：顶层条件作用于整个结果，分支条件作用于
所属分支，步骤条件作用于所属步骤，不外溢到其他分支或步骤。不得把原式
约束仅写成普通提示然后丢失。

`approximations` 是主结果的近似展示，每项 target 指向结果项，例如
`/value/elements/0`。精度为有效位数；只有已证明时填写 absolute_error_bound。
数值搜索范围由已确认问题中的 NumericOptions 保留；attempts 记录实际方法。

`steps` 独立表达 not_requested / available / partial / unavailable。
未请求时 items 为空；available 至少一步；partial 有已有步骤及未完成诊断。
步骤含规则代码、前后表达式、条件与子步骤。请求步骤但能力不足时返回
unavailable 和步骤诊断，不把已完成的答案改为失败。

`attempts` 记录方法、状态、有限非负耗时和诊断，不泄漏异常对象或内部调用栈。

## 5. 诊断与错误约定

`Diagnostic` 使用 code / message / severity / stage / field_paths。
code 为稳定、可扩展的机器标识；调用方不解析中文 message，不把未知代码
视为协议损坏。内部统一使用 enums.DiagnosticCode，枚举覆盖整个项目，
完整代码表与兼容规则见[诊断代码](diagnostics.md)。severity 不替代整体状态。

field_paths 相对产生诊断的入口输入文档：prepare/run 对应 ComputeRequest，
compute 对应 PreparedProblem，recognize 对应 RecognitionRequest，IPC 解码
对应其 envelope。空字符串指向文档根。即使诊断嵌入 steps 或 attempts，路径
仍使用该入口输入作为参照，不切换为响应内部位置。InputRequest.field_path
另按确认流程约定，始终指向调用方要修改并重新提交的 ComputeRequest。

| code | 状态/来源 |
|---|---|
| invalid_json / invalid_request | error，边界解码或字段结构错误 |
| missing_variable / missing_bound | needs_input，参数不充分 |
| ambiguous_operation / ocr_confirmation_required | needs_input，需确认 |
| conflicting_arguments | needs_input，显式信息冲突 |
| capability_unavailable | 当前后端或配置缺少所需能力，状态由整体流程决定 |
| invalid_image / recognition_failed | error，分别表示图片无效和识别失败 |
| ocr_confirmation_required | needs_input，需确认识别候选 |
| symbolic_not_completed | unsupported，有未完成数学内容 |
| invalid_latex | error，输入无法构成合法公式 |
| deadline_exceeded / cancelled | timeout / cancelled |
| worker_failed / cleanup_failed | error，执行或资源回收失败 |
| schema_version_mismatch / protocol_version_mismatch | error，版本不兼容 |

同一 code 不固定绑定 status；上表列常见用法。具体输入类型、定义域等通过
字段位置和消息说明，不新增按当前开发进度命名的原因码。

数学输入问题和可预期执行失败通过响应表达。codec 无法构成请求时抛出带
code、field_path 的 ContractDecodeError，由 CLI/Web 边界转换成公开错误。
media 的 ValueError/OSError、jobs 的 KeyError 也由入口映射。编程错误不伪装成
无解；兜底异常仅在应用或 worker 边界捕获。未实现入口当前显式抛异常。

## 6. 执行预算、取消和后台任务

`ExecutionOptions` 与数学请求分离，None 使用该类型声明的默认值。
默认总时限 30 秒、清理余量 2 秒；所有时限须为有限正数。默认容量仅作为
接口初值，后端可通过 capabilities 声明更严格限制，不能把字段视为已实现的保护。

预算覆盖排队（后台任务）、启动、识别、准备、解析、计算、步骤、序列化和接收，
使用单调时钟，不按阶段重置。清理最多另用 cleanup_timeout_seconds；无法确认
回收返回 error + cleanup_failed，不假称取消成功。回调异常由监督端隔离记录，
不当作数学失败；控制回调不得阻塞监督循环。

`ExecutionControl` 是运行时对象，含 CancellationToken 和进度回调，不能 JSON
序列化或传入 worker 启动参数。进度 fraction 为 [0, 1] 或 null，不保证可估算。
当前最终结果管道只发送一次结果；进度需要独立传输机制，由后端实现时选择。

`allow_partial_result=false` 时，中止必须不带数学内容；true 时只能返回已经
完成并检查的内容，保留 timeout/cancelled 状态与真实完整性，不返回半截 JSON。
已完成精确结果无法被清理确认时，整体仍是 error，不报告正常成功。

后台任务接口：submit(task, options) / get_job(id) / cancel_job(id)。

```text
queued → running → completed
   └──────┴─────→ failed / cancelled
```

- completed 表示执行层正常交付响应，响应可以是 needs_input、unsupported 或
  可预期的输入 error；timeout、基础设施 error 对应 failed，cancelled 对应 cancelled。
- queued/running 的 response 为空；completed 必有匹配任务的响应；failed 和
  cancelled 尽可能有响应，无法形成响应时必须有任务级诊断。
- accepted 仅表示接收取消请求，终态只能在确认清理后更新；完成与取消竞争时
  保持已先落定的终态，不覆盖完成结果。
- 未知或过期 job_id 抛 KeyError；标识存续与保留时长由宿主应用管理，默认不
  承诺进程重启后恢复。注册任务时持有资源直到终态。

## 7. JSON 和 IPC

编码为 UTF-8，字段 snake_case，联合标签 kind。模型中的 tuple 对应 JSON
数组，解码恢复为 tuple；StrEnum 对应字符串。dataclass 类型注解不做运行时
验证，asdict/json.dumps 也不能替代正式 codec。

- 数学输入、精确整数/分数/小数使用字符串；普通统计数值可以是有限 JSON 数字。
- 禁止裸 NaN/Infinity，也禁止用 json.dumps(default=str) 掩盖对象泄漏。
- 编解码双向拒绝非有限浮点、重复键、无效 UTF-8、未知输入字段、非法标签和
  错误类型；bool 不作为整数版本、阶数或容量接受。
- 缺省可选字段使用模型默认值；显式 null 仅允许在类型含 None 的字段中。
- 空数组表达没有元素，与缺字段和 null 分别处理；kind 是必需的边界标签。
- 每个独立公开文档带整数 schema_version=1；IPC envelope 带整数
  protocol_version=1。版本缺失、字符串、布尔或未知值均拒绝，不使用模型默认
  值掩盖边界缺版本。嵌套 PreparedProblem 和请求也保留自己的版本。
- 输入严格校验；消费者升级时可以约定接受新增可选输出字段，codec 实现须
  默认采用严格模式，不能把兼容策略与“任意字段都接受”混为一谈。
- 增加可选字段需定义默认行为；移除字段、改类型或含义、增加不能兼容的标签
  要升版。当前版本尚未发布，此次直接整理为 v1，不提供旧模型兼容别名。
- JSON 大小和嵌套深度必须受限制，避免在接收前无限分配；输入图像字节限制与
  JSON 容量分开检查。max_input_bytes 同时约束输入 JSON 和单个资源注册字节。

WorkerRequest = {protocol_version, task, options}。
task 通过 kind 区分 prepare / compute / run / recognize，每种只携带匹配载荷。
WorkerResult = {protocol_version, response}，任务与结果的对应关系：

| task.kind | response.kind |
|---|---|
| prepare | preparation |
| compute | computation |
| run | preparation 或 computation |
| recognize | recognition |

不合法的 envelope、EOF、崩溃、损坏消息由监督端转换成匹配任务类型的本地
错误响应。一请求一 worker 时无需额外 request_id；后台标识属于 jobs 层。
执行后端可替换，spawn/Pipe 是可选实现机制，不是公开数学模型的一部分。

## 8. 示例与契约验证

`docs/examples/` 保存可机器读取的请求和响应：

- differentiate-request.json：对 x 求二阶导数；
- solve-response.json：完整精确有限解集；
- needs-input-response.json：需要选择目标变量。

`test/test_contracts.py` 验证这些示例与模型表示一致、空集和失败可以明确区分、
嵌套类型可解析及公开模型可形成严格 JSON 树。该检查不代表已实现解码校验、
数学计算或执行机制，后续实现需另外覆盖这些行为。

## 9. 后续实现的边界

当前优先实现 prepare 的请求检查、LaTeX 解析与符号计算核心，计划见
[S1 实施计划](implement-s1.md)。直接使用 Python 模型推进，通用 JSON codec
后续接入；公共计算入口仍须满足执行保护约定。
每个模块可以独立实现，但不能另造入口专用的结果格式。
解析与求解不得丢失原式定义域、分母排除点或积分收敛条件；不能把数值搜索
没找到根当作无解。解析依赖的实际语义由兼容性测试验证。
独立 JSON Schema 暂不手写维护，避免与 Python 模型形成
第二套不一致的权威定义；实现 codec 时再选择生成方式。
