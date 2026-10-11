"""Fixed isolated test template: examine literal assignments; NEVER import patch."""
import ast,json,pathlib,sys

def literal_values(text):
    tree=ast.parse(text);out={}
    for node in tree.body:
        if not isinstance(node,ast.Assign) or len(node.targets)!=1 or not isinstance(node.targets[0],ast.Name):raise ValueError('Only literal assignments allowed')
        out[node.targets[0].id]=ast.literal_eval(node.value)
    return out

def main():
    root=pathlib.Path(sys.argv[1]);target=sys.argv[2];expected=json.loads(sys.argv[3])
    try:
        values=literal_values((root/target).read_text());ok=all(values.get(k)==v for k,v in expected.items())
    except Exception:ok=False
    print(json.dumps({'test_template':'literal_contract','passed':ok}));return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
