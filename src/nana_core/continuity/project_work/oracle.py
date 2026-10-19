"""Trusted evaluator: Python compiler symbol tables, never candidate AST output.

Independent implementation and inputs/answers are not sent to learning proposer.
This checks declarations/positions, not a full Python type/API compatibility claim.
"""
import symtable
from ...contracts import CoreError


def expected_inventory(data):
    try:
        table = symtable.symtable(data['source'], data['filename'], 'exec')
    except (SyntaxError, ValueError):
        raise CoreError('PROJECT_ORACLE_PARSE_FAILED') from None
    rows = []
    def walk(parent, names=()):
        for child in parent.get_children():
            name = child.get_name()
            if name in {'lambda', 'listcomp', 'setcomp', 'dictcomp', 'genexpr'}:
                continue
            kind = str(child.get_type()).split('.')[-1].lower()
            if kind not in {'function', 'class'}:
                raise CoreError('PROJECT_ORACLE_UNSUPPORTED_SYMBOL')
            full = (*names, name)
            rows.append({'name': '.'.join(full), 'kind': kind, 'line': child.get_lineno()})
            walk(child, full)
    walk(table)
    return sorted(rows, key=lambda row: (row['line'], row['name']))
