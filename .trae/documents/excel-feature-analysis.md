# Excel 下载功能分析报告

## 1. 项目概述

这是一个基于 MCP（Model Context Protocol）的 MySQL 数据库查询和 Excel 导出工具，主要功能包括：
- 连接多个 MySQL 数据库（YIFEI、YUNYAN_OB）
- 执行 SQL 查询
- 数据缓存与分析
- **Excel 账单下载与导出**

---

## 2. Excel 相关功能详细分析

### 2.1 核心 Excel 功能模块

#### **2.1.1 社保账单下载功能** (`download_tools.py`)

**函数**: `account_bill_download(company_name, cost_time)`

**功能描述**:
- 从数据库查询社保账单明细数据
- 将数据填充到 Excel 模板中
- 生成完整的社保账单 Excel 文件

**涉及的配置和文件**:

1. **Excel 模板文件**:
   - 路径：`output/FA 独立户账单模版 - 客户版本.xlsx`
   - 用途：作为账单生成的基础模板
   - Sheet 名称：`账单明细`
   - 数据从第 3 行开始填充（1-2 行可能是表头）

2. **列定义配置文件**:
   - 路径：`Reference/账单明细_columns.json`
   - 用途：定义 Excel 表格的所有列名及数据类型
   - 包含 80 列，主要字段：
     - 基本信息：序号、姓名、证件号码、户籍性质等
     - 基数信息：养老基数、医疗基数、失业基数等
     - 金额信息：养老公司、医疗公司、养老个人等
     - 比例信息：企业养老比例、个人养老比例等
     - 其他费用：服务费、工会费、增值税等

3. **字段映射关系** (`FIELD_MAPPING`):
   ```python
   FIELD_MAPPING = {
       '姓名': '姓名',
       '户籍性质': '户籍性质',
       '证件号码': '证件号码',
       '社保缴纳单位': '社保缴纳单位',
       '公积金缴纳单位': '公积金缴纳单位',
       '入职日期': '入职日期',
       '离职日期': '离职日期',
       '账单年月': '账单年月',
       '服务年月': '服务年月',
       '养老基数': '养老基数',
       # ... 共 43 个字段映射
   }
   ```

4. **默认值配置** (`DEFAULT_VALUES`):
   ```python
   DEFAULT_VALUES = {
       '序号': 'sequence',  # 自动序号
       '补差养老个人': 0,
       '补差医疗个人': 0,
       # ... 共 33 个默认值字段
       '养老收费模式': '托收',
       '养老支付方向': 1,
       # ... 各种收费模式和支付方向
   }
   ```

**程序逻辑流程**:

```
1. 参数验证
   - 检查 company_name 和 cost_time 是否为空
   
2. 加载配置文件
   - 读取 Reference/账单明细_columns.json
   - 获取模板列定义
   
3. 执行 SQL 查询
   - 使用复杂的 CTE 查询（WITH 子句）
   - 涉及多个表：soi_account, hro_customer, soi_acc_bill, soi_insured_info 等
   - 查询条件：公司名称匹配、账单月份、发送状态等
   
4. 数据验证
   - 检查是否查询到数据
   - 检查数据行数（限制 199 行以内）
   
5. 加载 Excel 模板
   - 使用 openpyxl 加载模板文件
   - 定位到"账单明细"Sheet
   
6. 清空旧数据
   - 清空第 3-202 行、第 1-80 列的所有单元格
   
7. 填充新数据
   - 遍历查询结果
   - 根据 FIELD_MAPPING 填充对应列
   - 根据 DEFAULT_VALUES 填充默认值
   - 设置数字格式（#,##0.00）
   
8. 保存文件
   - 保存修改后的 Excel 文件
   
9. 计算汇总
   - 对 numeric_cols 进行求和统计
   
10. 返回结果
    - 返回 JSON 格式的执行结果
```

**依赖的 Python 库**:
- `openpyxl`: Excel 文件操作
- `pandas`: 数据处理
- `datetime`: 日期处理

**关键代码段**:

```python
# 加载模板
wb = load_workbook(output_path)
ws = wb['账单明细']

# 清空旧数据
for row in range(3, 202):
    for col in range(1, 81):
        ws.cell(row=row, column=col).value = None

# 填充数据
for row_idx, row_data in enumerate(df.values, 3):
    for sql_col, excel_col in FIELD_MAPPING.items():
        col_idx = template_columns.index(excel_col) + 1
        cell = ws.cell(row=row_idx, column=col_idx)
        cell.value = value
        
# 保存
wb.save(output_path)
```

---

#### **2.1.2 通用 Excel 写入功能** (`file_tools.py`)

**函数 1**: `write_excel(filename, data, sheet_name, append)`

**功能描述**:
- 将数据写入 Excel 文件
- 支持新增或追加模式
- 支持两种数据格式：
  - 列格式：`{column: [values]}`
  - 记录格式：`[{field: value}, ...]`

**程序逻辑**:
```
1. 获取输出路径（使用 path_manager）
2. 创建目录（如果不存在）
3. 判断是否追加模式
   - 追加：加载现有文件，删除同名 Sheet
   - 新增：创建新 Workbook
4. 数据格式转换
   - 将数据统一转换为记录格式
5. 写入表头（加粗、居中）
6. 写入数据行
7. 保存文件
8. 返回 JSON 结果
```

**函数 2**: `write_excel_multi(filename, sheets_data)`

**功能描述**:
- 将多个数据集写入同一 Excel 文件的不同 Sheet
- 适用于需要多工作表的报表

**程序逻辑**:
```
1. 创建新 Workbook
2. 删除默认的"Sheet"
3. 遍历 sheets_data 字典
   - 为每个 key 创建一个 Sheet
   - 写入对应的数据
4. 保存文件
5. 返回 JSON 结果（包含所有 Sheet 名称）
```

**依赖的 Python 库**:
- `openpyxl`: Excel 文件操作
- `pathlib`: 路径管理

---

### 2.2 Excel 功能在 MCP Server 中的暴露

**文件**: `src/server.py`

#### **暴露的 Tool**:

1. **`account_bill_download`** (第 399-418 行)
   ```python
   @mcp.tool()
   async def account_bill_download(
       company_name: str,
       cost_time: str
   ) -> str:
       """下载指定公司在指定月份的社保账单明细 Excel 文件"""
       return download_account_bill(company_name, cost_time)
   ```

2. **`write_excel`** (第 365-381 行) - **已注释**
   ```python
   # @mcp.tool()
   # async def write_excel(...)
   ```

3. **`write_excel_multi`** (第 384-396 行) - **已注释**
   ```python
   # @mcp.tool()
   # async def write_excel_multi(...)
   ```

**重要发现**:
- `write_excel` 和 `write_excel_multi` 已经被注释掉，不再作为 MCP Tool 暴露
- `account_bill_download` 仍然处于激活状态

---

### 2.3 模块导出关系

**文件**: `src/tools/__init__.py`

```python
from .file_tools import write_excel, write_excel_multi
from .download_tools import account_bill_download

__all__ = [
    "write_excel",
    "write_excel_multi",
    "account_bill_download",
    # ... 其他工具
]
```

**影响**:
- 这些函数被导出到模块顶层
- 在 `server.py` 中被导入和使用

---

### 2.4 路径管理

**文件**: `src/core/path_manager.py`

**涉及的路径**:
```python
@property
def output_dir(self) -> Path:
    """获取输出目录"""
    return self._project_root / "output"

@property
def reference_dir(self) -> Path:
    """获取 Reference 目录"""
    parent_root = self._project_root.parent
    ref_dir = parent_root / "Reference"
    return ref_dir
```

**实际路径**:
- 输出目录：`/Users/alex.tu/Documents/10 MCP/at-mysql/output/`
- Reference 目录：`/Users/alex.tu/Documents/10 MCP/Reference/`

---

### 2.5 依赖配置

**文件**: `requirements.txt`

```txt
mcp>=1.0.0
mysql-connector-python>=8.0.0
openpyxl>=3.1.0        # ← Excel 操作核心依赖
python-dotenv>=1.0.0
```

**注意**: `pandas` 没有显式声明，但在代码中被使用（可能是 mcp 的依赖）

---

### 2.6 MCP 配置

**文件**: `MCPconfig.json`

```json
{
  "mcpServers": {
    "at-mysql": {
      "command": "/usr/bin/env",
      "args": ["python", "-m", "src.server"],
      "env": {
        "PYTHONPATH": "/Users/alex.tu/Documents/10 MCP/at-mysql",
        "PROJECT_ROOT": "/Users/alex.tu/Documents/10 MCP/at-mysql"
      }
    }
  }
}
```

---

## 3. 删除 Excel 功能需要修改的文件清单

### 3.1 核心代码文件

| 文件 | 需要删除的内容 | 优先级 |
|------|--------------|--------|
| `src/tools/download_tools.py` | 整个文件 | **高** |
| `src/tools/file_tools.py` | 整个文件 | **高** |
| `src/server.py` | - `account_bill_download` tool (L399-418)<br>- 导入语句中的 `write_excel`, `write_excel_multi` (L20-22)<br>- 已注释的 `write_excel` 代码块 (L365-381)<br>- 已注释的 `write_excel_multi` 代码块 (L384-396) | **高** |
| `src/tools/__init__.py` | - 导入语句 (L10-11)<br>- `__all__` 中的 `write_excel`, `write_excel_multi`, `account_bill_download` | **中** |

### 3.2 配置文件和静态资源

| 文件/目录 | 操作 | 备注 |
|-----------|------|------|
| `output/FA 独立户账单模版 - 客户版本.xlsx` | 删除 | Excel 模板文件 |
| `Reference/账单明细_columns.json` | 删除 | 列定义配置 |
| `Reference/客户明细_1775723638505.xlsx` | 删除 | 示例 Excel 文件 |
| `requirements.txt` | 可选：移除 `openpyxl` | 如果不再需要 Excel 功能 |

### 3.3 依赖项

**需要移除的 Python 包**:
- `openpyxl` (如果确认不再使用)

---

## 4. 删除步骤建议

### 阶段 1: 代码修改

1. **删除 `src/tools/download_tools.py` 文件**
2. **删除 `src/tools/file_tools.py` 文件**
3. **修改 `src/tools/__init__.py`**
   - 移除相关导入
   - 从 `__all__` 中移除
4. **修改 `src/server.py`**
   - 移除导入语句
   - 删除 `account_bill_download` tool 定义
   - 删除已注释的 Excel 相关代码块

### 阶段 2: 资源文件清理

5. **删除 Excel 模板文件**
6. **删除列定义配置文件**
7. **删除 Reference 目录下的 Excel 示例文件**

### 阶段 3: 依赖清理

8. **更新 `requirements.txt`**
   - 移除 `openpyxl` 依赖（可选，如果其他代码不再使用）

### 阶段 4: 验证

9. **测试验证**
   - 运行程序确保没有导入错误
   - 确认 MCP Server 正常启动
   - 验证其他功能不受影响

---

## 5. 影响范围评估

### 5.1 受影响的模块

- ✅ `src/tools/download_tools.py` - 完全删除
- ✅ `src/tools/file_tools.py` - 完全删除
- ✅ `src/tools/__init__.py` - 修改导入和导出
- ✅ `src/server.py` - 移除 Tool 定义
- ✅ 资源文件 - 删除

### 5.2 不受影响的模块

- ✅ `src/tools/sql_tools.py` - SQL 执行功能
- ✅ `src/tools/data_tools.py` - 数据缓存和分析功能
- ✅ `src/core/` - 核心配置、路径、数据库连接
- ✅ `MySQL_OB` 和 `MySQL_Yifei` Tool - 数据库查询功能
- ✅ `analyze_cached_data` Tool - 数据分析功能

### 5.3 风险评估

**低风险**:
- Excel 相关功能相对独立
- 与其他模块耦合度低
- `write_excel` 相关功能已被注释

**需要注意**:
- 确认 `openpyxl` 是否在其他地方被使用
- 确认是否有外部系统依赖这些 Excel 导出功能

---

## 6. 补充说明

### 6.1 当前 Excel 功能状态

- `account_bill_download`: **活跃状态**，可被 MCP 客户端调用
- `write_excel`: **已禁用**，代码被注释
- `write_excel_multi`: **已禁用**，代码被注释

### 6.2 数据流

```
MCP Client 调用
    ↓
account_bill_download Tool
    ↓
download_tools.account_bill_download()
    ↓
1. 查询数据库 (db_manager.execute_query)
2. 加载配置文件 (账单明细_columns.json)
3. 读取 Excel 模板 (FA 独立户账单模版 - 客户版本.xlsx)
4. 填充数据 (openpyxl)
5. 保存文件
    ↓
返回 JSON 结果
```

### 6.3 关键参数

- **company_name**: 客户公司核心名称（去掉"公司"等后缀）
- **cost_time**: 账单月份，格式 YYYY-MM
- **数据行数限制**: 199 行

---

## 7. 总结

本项目包含三套 Excel 相关功能：

1. **社保账单下载** (`account_bill_download`) - 核心业务功能，复杂度最高
2. **通用 Excel 写入** (`write_excel`) - 已禁用
3. **多 Sheet Excel 写入** (`write_excel_multi`) - 已禁用

删除这些功能需要修改 4 个代码文件，删除 3 个资源文件，并可选择性移除 `openpyxl` 依赖。

整体删除风险较低，因为 Excel 功能模块相对独立。
