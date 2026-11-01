# 模型组织说明

`src/mathlens/schemas/` 保存整个项目的公开数据模型。模型按数据类型和用途
分组，服务函数仍位于 application、execution、jobs、ocr 等业务模块。
当前只定义结构和接口，模型中的约束要由未来的 codec、准备和计算过程落实。

阅读项目职责见[项目架构](architecture.md)，字段规则与状态语义见
[接口契约](interfaces.md)。本文说明模型在哪里、怎样组合，以及如何扩展。

## 1. 分组原则与导入

- 同一类模型集中存放，例如积分上下限和积分规格都放在 operations.py；
  数学答案、成立条件和计算步骤集中在 results.py。
- 按用途分组，不按字符串、整数、数组等 Python 基础类型分文件。
- 不为每个类单独建文件；只有同类模型足够多或形成独立职责时再拆分。
- `__init__.py` 是统一导出入口，仅显式导入类型并声明 `__all__`，不实现业务。

业务代码继续使用：

```python
from mathlens.schemas import ComputeRequest, DifferentiateSpec, LatexInput
```

schemas 子模块内部使用具体来源，避免循环导入：

```python
# schemas/requests.py
from .inputs import InputSpec
from .operations import OperationSpec
```

原来的 schemas.py 已改为同名包。已有 `from mathlens.schemas import ...`
形式保留；模型字段、默认值、标签、版本和 JSON 示例未因文件拆分而变化。
类的定义模块会变为所属子模块，例如 ComputeRequest.__module__ 为
`mathlens.schemas.requests`。不承诺旧 pickle 或依赖旧模块反射信息的兼容性，
持久化与 IPC 契约使用 JSON。

## 2. 文件和完整类型索引

### base.py：基础表示与版本

| 定义 | 用途 |
|---|---|
| SCHEMA_VERSION | 公开数据契约版本 |
| PROTOCOL_VERSION | worker 通信协议版本 |
| JSONValue | JSON 可表达的递归值类型，不等于业务模型或运行时校验器 |
| MathExpression | 数学内容的 latex/text 展示表示 |

MathExpression 不保存 SymPy 对象，不承诺 text 可执行或 latex 可无损恢复 AST。

### inputs.py：输入和图片资源

| 定义 | 用途 |
|---|---|
| ImageRegion | 原图坐标中的矩形区域 |
| MediaResource | 图片资源标识、格式和尺寸 |
| ImageInput | 图片标识及可选识别区域 |
| LatexInput | 公式原文及可选图片来源 |
| InputSpec | LatexInput 或 ImageInput |

图片字节由 media 服务注册，模型只传 media_id。资源管理函数不放在 schemas。

### operations.py：运算规格及参数

| 定义 | 用途 |
|---|---|
| Substitution | 符号及其 LaTeX 代入值，也可表达数值初值 |
| EvaluateSpec | 求值及代入规格 |
| SimplifySpec | 化简规格 |
| DifferentiationTarget | 单次求导的变量与阶数 |
| DifferentiateSpec | 按顺序执行的求导目标 |
| IntegrationLimit | 积分变量与上下限 |
| IntegrateSpec | 从内到外的积分规格 |
| SearchInterval | 指定变量的数值搜索区间 |
| NumericOptions | 数值求解精度、搜索区间和初值 |
| SolveSpec | 未知量、解集范围与可选数值参数 |
| LimitSpec | 极限变量、趋近点和方向 |
| OperationSpec | 所有运算规格的联合类型 |

这里描述“做什么运算、使用哪些数学参数”。方法策略位于请求的结果偏好中，
执行超时与容量位于 tasks.py。不得把三类参数混入一个任意 options 字典。

### requests.py：请求和问题快照

| 定义 | 用途 |
|---|---|
| SymbolAssumptions | 实数、整数、正数等符号假设 |
| SymbolDeclaration | 稳定符号名、LaTeX 写法与假设 |
| ResultPreferences | 方法策略、近似展示精度及步骤偏好 |
| ComputeRequest | 允许待推断或待补充信息的用户意图 |
| NormalizationChange | 公式规范化的修改记录 |
| PreparedProblem | 参数充分且已经确认的问题快照 |

ComputeRequest 与 PreparedProblem 都描述输入侧问题，因此集中存放；
PreparationResponse 描述准备阶段如何结束，单独位于 preparation.py。

### diagnostics.py：诊断和交互项

| 定义 | 用途 |
|---|---|
| Diagnostic | 稳定代码、提示、级别、阶段与字段位置 |
| InputChoice | 用户可选的公式或运算候选 |
| InputRequest | 需要用户补充、修正或确认的请求项 |

Diagnostic 说明发生了什么；InputRequest 说明用户接下来能做什么。
两者可被准备与计算响应复用，不依赖具体响应类。
两者的 code 内部统一引用 enums.DiagnosticCode，完整分类见
[诊断代码](diagnostics.md)。字段保留 str 以兼容未来的未知诊断代码。

### preparation.py：准备响应

| 定义 | 用途 |
|---|---|
| PreparationResponse | 准备状态、快照、预览、交互项与诊断 |

ready 必须带 PreparedProblem；needs_input 必须有可操作的 InputRequest。
此文件只保存响应模型，prepare 函数位于 application.py。

### recognition.py：OCR 识别

| 定义 | 用途 |
|---|---|
| RecognitionCandidate | 候选公式、标识与可选置信度 |
| RecognizedRegion | 识别区域及有序候选 |
| RecognitionRequest | 独立 OCR 请求 |
| RecognitionResponse | OCR 状态、区域候选与诊断 |

识别结果不是计算问题。用户确认后用 LatexInput 保留公式和图片来源，再准备。

### results.py：数学答案和计算响应

| 定义 | 用途 |
|---|---|
| ExpressionValue | 表达式及其精确/近似/未完成性质 |
| FiniteSetValue | 有限集合，空元素数组可明确表示空集 |
| SymbolicSetValue | 全集、无限集或条件集的表示 |
| Assignment | 单个变量赋值 |
| MathCondition | 成立条件及作用范围 |
| SolutionBranch | 一个解分支的赋值与条件 |
| SolutionAssignmentsValue | 多变量解的分支集合 |
| DivergentValue | 已确认发散及方向 |
| UnevaluatedValue | 未完成的数学内容 |
| MathValue | 上述数学答案形状的联合类型 |
| Approximation | 指向主结果项的近似值、精度和已知误差界 |
| CalculationStep | 规则、前后表达式、条件与子步骤 |
| StepsResult | 步骤可用状态、步骤与诊断 |
| ComputationAttempt | 方法尝试、状态、耗时与诊断 |
| ComputeResponse | 完整计算响应 |
| ApplicationResponse | PreparationResponse 或 ComputeResponse |

结果形状 value.kind、数学性质 result_kind、处理状态 status 和解集完整性
completeness 是不同维度。步骤不可用不自动使已完成答案失败。

### tasks.py：执行、能力和任务协议

| 定义 | 用途 |
|---|---|
| ResourceLimits | 输入输出容量、深度、精度、图片像素与步骤等限制 |
| ExecutionOptions | 总预算、清理余量、部分结果策略与容量设置 |
| ProgressEvent | 阶段、提示与可选进度比例 |
| OperationCapability | 一种运算实际启用的方法、域与步骤能力 |
| Capabilities | 当前后端能力集合与限制 |
| PrepareTask | 准备任务，携带 ComputeRequest |
| ComputeTask | 计算任务，携带 PreparedProblem |
| RunTask | 一站式任务，携带 ComputeRequest |
| RecognizeTask | OCR 任务，携带 RecognitionRequest |
| WorkerTask | 四类 worker 任务的联合 |
| WorkerResponse | 准备、计算或 OCR 响应的联合 |
| WorkerRequest | 协议版本、任务载荷与执行选项 |
| WorkerResult | 协议版本与任务响应 |
| JobHandle | 后台任务标识 |
| JobSnapshot | 后台任务状态、进度、响应和诊断 |
| CancelResponse | 取消请求是否接受及当前状态 |

schemas/tasks.py 仅保存数据；包外的 execution.py 管单次执行，jobs.py 管后台
生命周期。ExecutionControl 和 CancellationToken 是运行时对象，留在
execution.py，不进入 schemas 或 JSON。

## 3. 依赖方向

下表只列 schemas 内部直接依赖，不含标准库和独立的 enums.py：

| 模块 | 直接依赖 |
|---|---|
| base | 无 |
| inputs | base |
| operations | 无 |
| requests | base、inputs、operations |
| diagnostics | operations |
| preparation | base、diagnostics、requests |
| recognition | base、diagnostics、inputs |
| results | base、diagnostics、preparation、requests |
| tasks | base、diagnostics、recognition、requests、results |

统一入口 __init__.py 最后汇总这些类型，子模块不能反向依赖它。模型模块也
不能导入任何业务服务，否则容易造成 application → schemas → application
这样的循环。类型注解中的跨模块名称要在所属模块可解析，不能只依赖统一
入口恰好导入过它们。

## 4. 从请求到结果

以二阶求导为例，以下代码只创建模型，可在当前阶段运行：

```python
from mathlens.schemas import (
    ComputeRequest,
    DifferentiationTarget,
    DifferentiateSpec,
    LatexInput,
)

request = ComputeRequest(
    input=LatexInput(latex="x^3"),
    operation=DifferentiateSpec(
        targets=(DifferentiationTarget(variable="x", order=2),),
    ),
)
```

未来准备成功后生成 PreparedProblem，compute 消费该快照，返回 ComputeResponse。
参数不足时返回 PreparationResponse 和 InputRequest，调用方修改请求再提交。
目前调用 prepare、compute、run 或 codec 仍会抛出 NotImplementedError。

对应 JSON 示例见 [求导请求](examples/differentiate-request.json)、
[完整有限解集](examples/solve-response.json) 和
[变量确认](examples/needs-input-response.json)。

## 5. 扩展与验证

新增运算时，先在 enums.py 声明名称，在 operations.py 定义专属参数并加入
OperationSpec；再更新统一导出、接口规则与示例。是否启用仍由能力接口决定，
不能因为枚举存在就自动宣称支持。

新增结果形状时，在 results.py 定义模型并加入 MathValue，明确它对性质和
完整性的影响；不要用通用字典绕过已有结构。所有模型继续使用 frozen、
kw_only dataclass 和 tuple 集合；边界校验由将来的 codec 实现。

移动模型之后运行完整契约测试，核对统一导入、嵌套类型解析、标签唯一性和
JSON 示例。文档中的目录、类型索引和本地链接也要同步。当前测试仅验证结构
与示例，不替代未来的数学、JSON 校验和任务执行测试。
