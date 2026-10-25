"""AST/token metrics, not a completion score or exact McCabe analysis."""

import argparse
import ast
import io
import json
from pathlib import Path
import tokenize


def measure(root):
    rows = []
    functions = []
    for path in sorted((Path(root) / "src/nana_core").rglob("*.py")):
        text = path.read_text()
        tree = ast.parse(text)
        lines = text.splitlines()
        nodes = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for node in nodes:
            decisions = sum(
                isinstance(n, (ast.If, ast.IfExp, ast.For, ast.While, ast.ExceptHandler, ast.comprehension))
                for n in ast.walk(node)
            )
            decisions += sum(len(n.values) - 1 for n in ast.walk(node) if isinstance(n, ast.BoolOp))
            functions.append(
                {
                    "path": str(path.relative_to(root)),
                    "name": node.name,
                    "line": node.lineno,
                    "span": node.end_lineno - node.lineno + 1,
                    "decision_estimate": 1 + decisions,
                }
            )
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
        meaningful = {
            t.start[0]
            for t in tokens
            if t.type
            not in {
                tokenize.COMMENT,
                tokenize.NL,
                tokenize.NEWLINE,
                tokenize.INDENT,
                tokenize.DEDENT,
                tokenize.ENDMARKER,
            }
        }
        rows.append(
            {
                "path": str(path.relative_to(root)),
                "physical_lines": len(lines),
                "token_lines_including_docstrings": len(meaningful),
                "over120": sum(len(s) > 120 for s in lines),
                "over200": sum(len(s) > 200 for s in lines),
                "semicolons": sum(t.string == ";" for t in tokens),
                "functions": len(nodes),
                "documented_functions": sum(ast.get_docstring(n) is not None for n in nodes),
                "return_annotated_functions": sum(n.returns is not None for n in nodes),
            }
        )
    return {
        "method": "AST_DECISION_ESTIMATE_NOT_EXACT_MCCABE; token lines include docstrings; function counts include nested/private",
        "files": len(rows),
        "totals": {key: sum(row[key] for row in rows) for key in rows[0] if key != "path"},
        "rows": rows,
        "largest_functions": sorted(functions, key=lambda r: r["span"], reverse=True)[:25],
        "highest_decisions": sorted(functions, key=lambda r: r["decision_estimate"], reverse=True)[:25],
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    value = measure(a.source.resolve())
    a.output.write_text(json.dumps(value, indent=2) + "\n")
    print(json.dumps({"files": value["files"], **value["totals"]}))
