"""No-exec bounded source transformations. Candidate methods see no oracle."""
import ast
import re
from ...contracts import CoreError


def inventory(method, data):
    if type(data) is not dict or set(data) != {'filename', 'source', 'sha256'}:
        raise CoreError('PROJECT_SOURCE_CONTRACT')
    source = data['source']
    if type(source) is not str or len(source.encode()) > 6144:
        raise CoreError('PROJECT_SOURCE_BOUND')
    if method == 'PYTHON_TOP_DEFS':
        return [{'name': m.group(1), 'kind': 'function', 'line': n}
                for n, line in enumerate(source.splitlines(), 1)
                if (m := re.match(r'^def ([A-Za-z_]\w*)\(', line))]
    if method != 'PYTHON_AST_API':
        raise CoreError('PROJECT_METHOD_UNSUPPORTED')
    try:
        tree = ast.parse(source, filename=data['filename'])
    except (SyntaxError, ValueError, RecursionError):
        raise CoreError('PROJECT_PARSE_FAILED') from None
    rows = []
    def visit(node, parents=()):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            name = (*parents, node.name)
            rows.append({'name': '.'.join(name), 'kind': 'class' if isinstance(node, ast.ClassDef) else 'function', 'line': node.lineno})
            parents = name
        for child in ast.iter_child_nodes(node):
            visit(child, parents)
    visit(tree)
    return sorted(rows, key=lambda row: (row['line'], row['name']))
