"""
Agent 工具定义
LangChain Agent 可调用的工具集

工具列表：
1. calculator - 数学计算（安全表达式解析）
2. get_current_datetime - 获取当前时间
3. list_uploaded_files - 列出已上传文件
4. read_uploaded_file - 读取文本文件内容
5. tavily_search - 联网搜索（需配置 TAVILY_API_KEY）

安全设计：
- calculator 使用 AST 解析，仅允许白名单内的运算
- read_uploaded_file 限制文件类型，防止路径遍历攻击
"""
import ast
import math
import operator
from datetime import datetime
from pathlib import Path

from langchain_core.tools import tool  # LangChain 工具装饰器

from config import config  # 全局配置

# 上传文件存储目录
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"

# 安全数学运算操作符白名单
# 只允许基础算术运算，防止代码注入攻击
_SAFE_OPS = {
    ast.Add: operator.add,      # 加法
    ast.Sub: operator.sub,      # 减法
    ast.Mult: operator.mul,     # 乘法
    ast.Div: operator.truediv,  # 除法
    ast.Pow: operator.pow,      # 幂运算
    ast.USub: operator.neg,     # 负号
    ast.Mod: operator.mod,      # 取模
}


def _eval_math(node: ast.AST) -> float:
    """
    安全的数学表达式求值器
    
    使用 AST（抽象语法树）解析表达式，只执行白名单内的运算，
    防止任意代码执行攻击。
    
    Args:
        node: AST 节点
    
    Returns:
        计算结果（浮点数）
    
    Raises:
        ValueError: 遇到不支持的表达式
    """
    # 常量节点（数字）
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    
    # 一元运算（如负号）
    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_eval_math(node.operand))
    
    # 二元运算（加减乘除等）
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_eval_math(node.left), _eval_math(node.right))
    
    # 函数调用（仅允许白名单内的数学函数）
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        func_name = node.func.id
        if func_name in {"sqrt", "sin", "cos", "tan", "log", "log10"}:
            args = [_eval_math(arg) for arg in node.args]
            if func_name == "sqrt":
                return math.sqrt(args[0])
            if func_name == "sin":
                return math.sin(args[0])
            if func_name == "cos":
                return math.cos(args[0])
            if func_name == "tan":
                return math.tan(args[0])
            if func_name == "log":
                return math.log(args[0])
            if func_name == "log10":
                return math.log10(args[0])
    
    # 常量引用（pi, e）
    if isinstance(node, ast.Name):
        if node.id == "pi":
            return math.pi
        if node.id == "e":
            return math.e
    
    raise ValueError(f"不支持的表达式: {ast.dump(node)}")


@tool
def calculator(expression: str) -> str:
    """
    数学计算器工具
    
    支持的运算：
    - 基础算术：+、-、*、/、**（幂运算）、%（取模）
    - 数学函数：sqrt、sin、cos、tan、log、log10
    - 常量：pi（圆周率）、e（自然对数底数）
    
    安全特性：
    - 使用 AST 解析，防止代码注入
    - 仅执行白名单内的运算
    
    Args:
        expression: 数学表达式字符串
    
    Returns:
        计算结果字符串，或错误信息
    """
    try:
        # 使用 AST 解析表达式
        tree = ast.parse(expression.strip(), mode="eval")
        result = _eval_math(tree.body)
        # 整数结果转换为整数格式
        if result == int(result):
            return str(int(result))
        return str(round(result, 10))
    except Exception as exc:
        return f"计算失败: {exc}"


@tool
def get_current_datetime() -> str:
    """
    获取当前日期和时间
    
    返回本地时区的当前时间，格式为：YYYY-MM-DD HH:MM:SS
    
    Returns:
        当前时间字符串
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@tool
def list_uploaded_files() -> str:
    """
    列出用户已上传的文件
    
    扫描 uploads 目录，返回最近上传的20个文件列表，
    包含文件名和文件大小信息。
    
    Returns:
        文件列表字符串，或"暂无上传文件"
    """
    if not UPLOAD_DIR.exists():
        return "暂无上传文件"

    # 递归获取所有文件，按修改时间降序排序
    files = sorted(
        (f for f in UPLOAD_DIR.rglob("*") if f.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not files:
        return "暂无上传文件"

    lines = []
    # 最多返回20个文件
    for path in files[:20]:
        rel = path.relative_to(UPLOAD_DIR)
        size_kb = path.stat().st_size / 1024
        lines.append(f"- {rel} ({size_kb:.1f} KB)")
    return "已上传文件:\n" + "\n".join(lines)


@tool
def read_uploaded_file(filename: str) -> str:
    """
    读取已上传的文本文件内容
    
    安全特性：
    - 防止路径遍历攻击（过滤 .. 和绝对路径）
    - 限制文件类型（仅允许文本类文件）
    - 限制内容大小（最多8000字符）
    
    支持的文件类型：
    .txt, .md, .json, .csv, .py, .js, .html, .xml, .yaml, .yml
    
    Args:
        filename: 文件名或 uploads 下的相对路径
    
    Returns:
        文件内容，或错误信息
    """
    # 安全处理：防止路径遍历攻击
    safe_name = filename.lstrip("/").replace("..", "")
    path = UPLOAD_DIR / safe_name

    # 检查文件是否存在
    if not path.is_file():
        return f"文件不存在: {filename}"

    # 检查文件类型白名单
    text_extensions = {".txt", ".md", ".json", ".csv", ".py", ".js", ".html", ".xml", ".yaml", ".yml"}
    if path.suffix.lower() not in text_extensions:
        return f"不支持读取该类型文件: {path.suffix}，仅支持文本类文件"

    try:
        # 读取文件内容
        content = path.read_text(encoding="utf-8")
        # 内容长度限制
        if len(content) > 8000:
            return content[:8000] + "\n\n...(内容过长，已截断)"
        return content
    except UnicodeDecodeError:
        return "无法以文本方式读取该文件（可能是二进制文件）"


def _create_tavily_search_tool():
    """
    创建 Tavily 联网搜索工具
    
    Tavily 是一个专为 AI Agent 设计的搜索服务，
    提供高质量、最新的搜索结果。
    
    注意：需要配置 TAVILY_API_KEY 环境变量才能启用。
    
    Returns:
        TavilySearch 工具实例，或 None（未配置时）
    """
    if not config.tavily or not config.tavily.api_key:
        return None

    from langchain_tavily import TavilySearch

    return TavilySearch(
        max_results=config.tavily.max_results,
        include_answer=True,  # 直接包含总结答案
        search_depth="basic",  # 搜索深度
        tavily_api_key=config.tavily.api_key,
    )


def get_agent_tools() -> list:
    """
    返回 Agent 可用的全部工具列表
    
    工具加载逻辑：
    1. 基础工具始终加载：calculator、get_current_datetime、list_uploaded_files、read_uploaded_file
    2. 可选工具条件加载：Tavily 搜索（需配置 API Key）
    
    Returns:
        LangChain 工具列表
    """
    tools = [calculator, get_current_datetime, list_uploaded_files, read_uploaded_file]

    # 条件加载 Tavily 搜索工具
    tavily_tool = _create_tavily_search_tool()
    if tavily_tool:
        tools.append(tavily_tool)

    return tools
