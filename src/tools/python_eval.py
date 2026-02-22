
from src.tools.base import Tool


class PythonEvalTool(Tool):
    """Runs basic Python expressions in a sandboxed eval."""
    
    SAFE_BUILTINS = {
        "abs": abs, "all": all, "any": any, "bool": bool,
        "dict": dict, "enumerate": enumerate, "filter": filter,
        "float": float, "int": int, "len": len, "list": list,
        "map": map, "max": max, "min": min, "pow": pow,
        "range": range, "round": round, "set": set, "sorted": sorted,
        "str": str, "sum": sum, "tuple": tuple, "type": type,
        "zip": zip, "True": True, "False": False, "None": None,
    }

    def __init__(self):
        super().__init__(
            "python_eval",
            "Evaluate a Python expression. Only basic math, string, and collection operations are allowed. No file I/O or imports.",
            args_schema={
                "expression": "The Python expression to evaluate (e.g., '2 + 2', '[x**2 for x in range(10)]')"
            }
        )

    async def run(self, expression: str) -> str:
        try:
            import math
            import json as json_mod

            safe_globals = {"__builtins__": self.SAFE_BUILTINS, "math": math, "json": json_mod}
            result = eval(expression, safe_globals, {})
            return str(result)
        except Exception as e:
            return f"Error evaluating expression: {e}"
