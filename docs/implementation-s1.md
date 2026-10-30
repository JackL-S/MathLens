# S1 实现方案

当前已建立项目配置、包目录和空文件，计算逻辑与测试用例尚未实现。本文只定义 S1 的范围、接口、实现方法和验收；整体职责见[项目架构](architecture.md)，项目路线见 [README](../README.md)。

**S1 直接采用项目架构的模块划分、依赖方向和数据边界。** 本文只规定这些模块在 S1 中实现的能力，不设计独立的原型架构或临时调用链；架构定义以 `architecture.md` 为准。

## S1 交付范围

交付 Python API、CLI、测试与运行说明，完成“显式运算的 LaTeX → 符号计算 → LaTeX / JSON”。

- 支持化简、求导、不定/定积分、单变量方程求解；仅开放 real 域，使用最小语法白名单。
- 求导、积分和方程求解须显式给出一个目标变量；其他自由符号可作参数，化简无需目标变量。
- 包含解析/计算超时保护和失败诊断。S1 不包含自动类型识别、数值回退、OCR、计算步骤与图形界面。

## 开发顺序

1. 在 `pyproject.toml` 固定依赖并记录环境，安装验证后建立测试基线。变更版本时同步更新锁文件并重跑验证。
2. 定义请求、结果和诊断模型，测试 JSON 往返与下表的结果分类。
3. 验证固定依赖组合的解析语义，实现白名单和数学结构校验，再接入符号计算。
4. 接入独立 worker 与超时清理，然后提供 CLI；无超时的求解调用不进入验收版本。
5. 跑通算例、异常与超时回归，补安装和使用说明。变更依赖组合时更新版本记录、锁文件并重跑基线。

## 架构落地

项目架构与代码模块对应如下，S1 按此组织实现：

| 架构职责 | 代码位置 | S1 实现内容 |
|---|---|---|
| 输入与解析 | `parsing/` | LaTeX 清理、白名单、解析与数学结构校验 |
| 应用编排 | `application.py`、`execution.py` | 准备问题、调用计算、超时与资源回收 |
| 计算 | `solving/` | 符号计算、结果分类、约束检查、数学内容序列化 |
| 展示 | `rendering/`、`cli.py` | 输出格式与命令行交互 |
| 共享模型 | `models.py` | 请求、问题描述、结果与诊断，不依赖 SymPy |

文件布局：

```text
MathLens/
├── pyproject.toml
├── requirements-dev.lock
├── docs/
│   ├── architecture.md
│   └── implementation-s1.md
├── src/mathlens/
│   ├── __init__.py
│   ├── models.py
│   ├── application.py
│   ├── execution.py
│   ├── cli.py
│   ├── parsing/
│   │   ├── __init__.py
│   │   ├── normalize.py
│   │   └── latex.py
│   ├── solving/
│   │   ├── __init__.py
│   │   ├── symbolic.py
│   │   └── serialization.py
│   ├── rendering/
│   │   ├── __init__.py
│   │   └── formats.py
│   └── ocr/
│       └── __init__.py
└── test/
    ├── test_parsing.py
    ├── test_solving.py
    └── test_pipeline.py
```

上述 Python 文件目前均为空文件。`ocr/` 只保留包入口；`test/` 沿用现有名称，由 pytest 配置指定。项目使用 setuptools 的 src 包发现，不依赖 IDE 添加导入路径。CLI 入口等 `cli.main` 实现后再注册，当前安装不会提供计算命令。

### 环境与安装

Python 要求为 3.11–3.12。运行依赖固定为 SymPy 1.14.0、latex2sympy2 1.9.1、antlr4-python3-runtime 4.7.2；开发依赖为 pytest 8.4.2，构建后端为 setuptools 82.0.1。来源为对应 PyPI 发行包；完整开发依赖组合记录在 `requirements-dev.lock`。当前 ANTLR 依赖在 Python 3.13 导入失败（`typing.io` 已不可用），因此配置排除 3.13 及以上。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock -e "."
```

仅安装项目使用 `pip install -e .`；按开发声明安装使用 `pip install -e ".[dev]"`，需要复现完整组合时使用上面的锁文件命令。空测试文件尚无用例，pytest 报告“未收集到测试”是当前骨架状态，不代表 S1 已通过验收。

本次骨架验证环境为 Windows x86_64 / CPython 3.12.12。editable 安装、全部占位模块导入、`pip check`、wheel 构建及包内容检查已通过；`pytest --collect-only -q` 返回无用例，符合当前空文件状态。3.11 尚未实测。

验证命令为 `.\.venv\Scripts\python.exe -m pip check`、`.\.venv\Scripts\python.exe -m pytest --collect-only -q`、`.\.venv\Scripts\python.exe -m pip wheel --no-deps --wheel-dir dist .`。wheel 包含全部 14 个源码文件，不包含测试文件。

依赖探测中，分数求值、导数与定积分样例可运行；`\log(10)` 被解析成 `log(10, 10)`，因此按本文约定先拒绝该写法，不能直接当作自然对数。`x^2-2=0` 解析直接返回已求解的等式列表，方程适配必须保留原式并受控处理，不能把 parser 当成只构建表达式的纯转换。上述为第三方依赖行为记录，项目计算接口尚未实现。

调用关系为 `CLI → application → execution → worker 内的 parsing / solving → 公开结果 → rendering`。CLI 不绕过应用层直接调用求解器；计算侧不依赖展示层。执行位置由 worker 机制决定，不改变模块职责。

## 接口与结果

`prepare(request) -> PreparedProblem` 在父进程检查字段，缺参数抛 `NeedsInputError`；成功只返回文本与请求元数据，不解析数学内容。`compute(prepared_problem) -> ComputationResult` 在 worker 完成清理、解析、结构校验、计算和序列化。

| 模型 | 字段约定 |
|---|---|
| `ComputeRequest` | `input_kind="latex"`, `latex`, `operation`, `variables`, `domain`, `assumptions`, `bounds`, `budget`；不定义图片或数值求解参数 |
| `PreparedProblem` | 已校验的 LaTeX、运算、变量、定义域、上下限与预算；不含 SymPy 对象 |
| `ComputationResult` | `schema_version`, `status`, `result_kind`, `completeness`, `verification`, `value`, `latex`, `conditions`, `diagnostics`, `attempts`，并报告实际定义域 |

`operation` 为 `simplify / differentiate / integrate / solve_equation`。`domain` 枚举为 `real / complex / integer / positive_real`，S1 默认且仅支持 real；其他已知域返回 `unsupported + domain_not_enabled`，未知值返回 `error + invalid_domain`。`assumptions` 仅接受缺省或空映射，非空返回 `unsupported + assumptions_not_enabled`，不构造自定义变量假设。

实数求解域映射到 `solveset(..., domain=S.Reals)`，不注入 `Symbol(real=True)`。显式指定 domain 的 simplify 请求附 info 诊断 `domain_not_applied_to_simplify`：“当前化简未应用变量实数假设，部分表达式可能保留原式”；记录 domain 是否显式提供，省略时不重复提示。积分上下限使用 `bounds`。

### 状态与数学内容

S1 的 status 取值为 `success / needs_input / unsupported / error / timeout`。

| 场景 | status / 诊断 |
|---|---|
| 完成计算、空解集、全集或已确认发散 | `success`；发散附 `divergent_integral` |
| prepare 缺字段 | `needs_input + missing_field`，`stage=prepare` |
| worker 发现原式与参数冲突 | `needs_input + conflicting_arguments`，`stage=compute` |
| 未开放的语法、定义域、假设或能力 | `unsupported`，附具体能力诊断 |
| 运算尚未完成 | `unsupported + symbolic_not_completed`，保留可用数学内容 |
| 无效输入 / worker 异常 / 超时 | 分别为 `error + invalid_latex/invalid_request`、`error + worker_failed`、`timeout + deadline_exceeded` |

诊断含 `code / message / severity / stage`，可附 `fields` 定位输入。调用方根据诊断来源决定补字段或确认冲突，不把 needs_input 限定在 prepare。

| 数学内容 | result_kind | value.kind | completeness |
|---|---|---|---|
| 已完成表达式，含特殊函数与精确定义的代数根 | `exact` | `expression` | `not_applicable` |
| 完整有限解集 | `exact` | `finite_set` | `complete` |
| 空解集 | `exact` | `empty_set` | `complete` |
| 全集或完整无限解集 | `exact` | `symbolic_set` | `complete` |
| 已确认积分发散 | `exact` | `divergent` | `not_applicable` |
| 整体未求值运算 | `unevaluated` | `unevaluated` | `not_applicable` |
| 纯待求解条件集，如 ConditionSet | `unevaluated` | `symbolic_set` | `unknown` |
| 已求值与未求值表达式组合 | `mixed` | `expression` | `not_applicable` |
| 部分已知解与剩余条件组合 | `mixed` | `symbolic_set` | `partial` |
| 无可返回数学内容 | `none` | 无，`value=null` | `not_applicable` |

S1 的 result_kind 取值为 `exact / mixed / unevaluated / none`，mixed 仅指已求值与未求值组合。条件不等于未完成：已求出的带条件精确答案仍可为 exact。有限小数按原始十进制文本构造精确有理数，不先转机器浮点数。

`value` 为带 kind 的 JSON 对象：表达式含 `latex/text`，有限集含元素表示数组，符号集保留整体表示和条件。`divergent` 另含 `direction=positive_infinity/negative_infinity/does_not_exist`；exact 在此表示收敛性判定确定，不表示存在有限值。无数学结果时顶层 `latex=null`。`conditions` 是 `latex/text` 对象数组，积分常数由 solving 层加入。数学数值使用字符串或带标签表示，避免精度丢失及非标准 NaN/Infinity；异常对象不得进入结果，所有嵌套字段须通过严格 JSON 往返。

**S1 所有结果的 `verification` 固定为 `not_performed`**，包含成功和父进程生成的错误/超时。必要的参数、定义域、收敛性和序列化检查仍执行；此字段仅报告独立数学复核，S1 不实现独立复核流程。

### 版本

- 公开结果顶层必含整数 `schema_version=1`，API、CLI 和 IPC 内层结果一致，包括提前失败。增加可选字段可保持版本；必填字段、类型、语义等不兼容变更须升版，新增枚举须更新兼容规则。
- IPC envelope 使用独立的整数 `protocol_version=1`。S1 不接受缺失、字符串或未知版本，分别返回本地 v1 的 `schema_version_mismatch / protocol_version_mismatch` 错误。

## 解析与计算

最小语法：整数、有限小数、单个拉丁字母变量、`\pi`；`+ - * / =`、`\cdot`、`\times`、`^`、`\frac`；圆括号/花括号及匹配的 `\left(`/`\right)`；外围 `$...$`/`\[...\]`；带括号参数的 `\sin/\cos/\exp/\log`；单重 `\int` 与配对上下限、`dx`/`\mathrm{d}x`；一阶 `\frac{d}{dx}` 及对应直立 d 写法。也可只输入表达式，由请求指定运算与参数。

`_` 仅用于积分下限，不开放一般下标、limit、矩阵、多重积分、求和、自定义宏或一般函数定义。未知 token 在 normalize 拒绝，返回 `syntax_not_supported` 和支持清单；合法 token 的结构仍须由现有 parser 及语义检查验证，不自写数学 parser。允许范围内残缺语法报 invalid_latex。原式的变量、上下限与显式参数须一致，运算符仅应用一次。

`\log` 约定为自然对数：固定组合须测试 `\log(10)`、`\log(\exp(1))` 及内部表达式；若语义不同，先以 `log_semantics_not_supported` 拒绝，经过测试且可追溯的规则才可用于改写。只移除定界符等必要包装，不擅自补等号或括号。

符号策略为 `simplify / diff / integrate / solveset`。保留原始 LaTeX、清理记录和约束；重打印只表示解析结果。解析器可能提前计算，关键约束无法可靠保留时拒绝输入。参考 [latex2sympy2 上游说明](https://github.com/IuvenisSapiens/latex2sympy2)。

普通反常积分与柯西主值分开：`1/x` 在 `[-1,1]` 的主值 0 不能充当普通积分值，需检查奇点两侧。仅确认不收敛才返回 divergent，NaN、zoo、残留积分或未知条件不构成证明；无法判定则保留未完成结果。求解器失败不等于无解。

## worker 与 CLI

`execution.py` 提供可导入的模块顶层入口，数学模块在 worker 内加载：

```python
from multiprocessing.connection import Connection

def worker_main(request_json: bytes, result_conn: Connection) -> None:
    ...
```

- 使用 `multiprocessing.get_context("spawn")`，以 `Process(target=worker_main, args=(request_json, send_conn))` 启动。请求为 UTF-8 JSON bytes，包含 `protocol_version/action/problem/budget`，S1 action 仅为 compute；数学对象不作为启动参数。
- worker 完整执行 `normalize → parse → 校验 → compute → serialize`；正常或可捕获错误均只发送一次 `{"protocol_version": 1, "result": ...}`，通过独立单向 Pipe 的 `send_bytes/recv_bytes` 传 JSON。finally 关闭写端，返回值不传结果；父进程启动后关闭自己的写端副本。
- 父进程按单调时钟监督启动、解析、计算、校验、序列化与接收的总时限。边收结果边监督，不先无限 join；就绪不等于消息收齐，接收同样受限时与大小限制。可用接收线程，但 Timer/线程不能负责中断求解器。
- 超时后终止，限时 join，必要时强制结束；回收后返回 timeout，无法确认清理则报告错误，不能无限等待。损坏消息、EOF、崩溃按协议报错；丢弃强制结束后的通道。S1 一请求一进程，不用共享队列/进程池，不设计 request_id 并发匹配。
- 限制输入、表达式、阶数与输出大小。子进程用于执行控制，不等同安全沙箱；S1 正常计算只解析一次。

CLI 默认两行 `status: ...`、`latex: ...`（无答案为 `(none)`），有诊断时打印 `code: message`，包括成功提示。`--json` 的 stdout 只输出完整 ComputationResult 单对象，包含输入错误；日志写 stderr，不混入 traceback 或 worker 输出。success 退出码为 0，其他为 1；发散属于成功判定。API 与 CLI 共用序列化逻辑。

## 验收

| 检查 | S1 最低要求 |
|---|---|
| 兼容性与单元测试 | 固定版本后验证白名单、log 底数、积分上下限、导数不重复计算、恒等式原始约束；测试解析、求解与分类 |
| 数学回归 | `1/3+1/6`、导数、不定/定积分、`x^2-2=0`、实数域 `x^2+1=0` 空集、`x=x` 全集；含分母约束的输入不可丢排除点 |
| 发散与未完成 | `1/x` 在 `[0,1]` 向正无穷发散、在 `[-1,1]` 普通积分不存在；未定结果不直接标为发散 |
| 结果与协议 | fixtures 保存 request、status、诊断代码、latex 及必要数学期望；检查映射表、JSON 往返、无 SymPy 泄漏、版本异常、固定 verification |
| 执行与 CLI | 注入可控卡住 worker，验证预算加清理余量内返回、进程回收且下一请求可用；覆盖崩溃、EOF、坏 JSON、超大消息、needs_input 两个来源、两种输出模式 |

比较数学语义并保留稳定 LaTeX 快照，基线变化先核对原因。上述检查通过并有安装/运行说明，S1 才算完成。
