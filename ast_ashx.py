#!/usr/bin/env python3
"""Generate ActionScript and Haxe skeletons from Clang's filtered AST JSON.

Usage: python3 ast_ashx.py [AST.json] [-o ./orig/a/BoxShape.as]
       [--haxe-output ./hx/a/BoxShape.hx]
"""
import argparse
import json
import os
import re
import sys


def read_json_stream(path):
    text = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
    decoder = json.JSONDecoder()
    pos = 0
    while pos < len(text):
        while pos < len(text) and text[pos].isspace():
            pos += 1
        if pos == len(text):
            break
        try:
            value, pos = decoder.raw_decode(text, pos)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON at line {text.count(chr(10), 0, exc.pos) + 1}: {exc.msg}") from exc
        if not isinstance(value, dict):
            raise ValueError("expected each AST record to be a JSON object")
        yield value


def as_name(name):
    name = re.sub(r"[^A-Za-z0-9_$]", "_", name)
    if not name or name[0].isdigit():
        name = "_" + name
    return name


def type_default(qual_type):
    t = qual_type.replace("const ", "").strip()
    if "*" in t or "&" in t:
        return "null"
    if t == "void":
        return ""
    if t == "bool":
        return "false"
    if t in {"char", "signed char", "unsigned char", "short", "unsigned short",
             "int", "unsigned int", "long", "unsigned long", "long long",
             "unsigned long long", "float", "double", "btScalar", "size_t"}:
        return "0"
    return "null"


def haxe_type(cpp_type, return_type=False):
    t = cpp_type.strip().replace("const ", "").strip()
    if return_type and t == "void":
        return "Void"
    if "&" in t:
        base = haxe_type(t.replace("&", "").strip())
        return f"#if cpp Reference<{base}> #else {base} #end"
    if "*" in t:
        base = haxe_type(t.replace("*", "").strip())
        return f"cpp.Star<{base}>"
    if "btVector3" in t:
        return "bullet.Bt.Vector3"
    if "btTransform" in t:
        return "bullet.Bt.Transform"
    if "btQuaternion" in t:
        return "bullet.Bt.Quaternion"
    if t in {"float", "double", "btScalar"}:
        return "Float"
    if t == "bool":
        return "Bool"
    if t in {"void"}:
        return "Void"
    if t in {"char", "signed char", "unsigned char", "short", "unsigned short",
             "int", "unsigned int", "long", "unsigned long", "long long",
             "unsigned long long", "size_t"}:
        return "Int"
    return "Dynamic"


def haxe_class_name(cpp_name):
    name = as_name(cpp_name)
    if name.startswith("bt"):
        name = name[2:]
    return name[:1].upper() + name[1:]


def params(node):
    result = []
    for child in node.get("inner", []):
        if child.get("kind") == "ParmVarDecl":
            result.append((as_name(child.get("name") or f"arg{len(result)}"),
                           child.get("type", {}).get("qualType", "")))
    return result


def unwrap(node):
    transparent = {"ImplicitCastExpr", "ExprWithCleanups", "MaterializeTemporaryExpr",
                   "CXXBindTemporaryExpr", "ParenExpr", "ConstantExpr"}
    while node and node.get("kind") in transparent and node.get("inner"):
        node = node["inner"][0]
    return node


def expression(node):
    if not node:
        return "/* missing expression */"
    kind = node.get("kind")
    if kind in {"ImplicitCastExpr", "ExprWithCleanups", "MaterializeTemporaryExpr",
                "CXXBindTemporaryExpr", "ParenExpr", "ConstantExpr", "CXXFunctionalCastExpr",
                "CStyleCastExpr"}:
        inner = node.get("inner", [])
        return expression(inner[0]) if inner else "null"
    if kind == "CXXThisExpr":
        return "this"
    if kind == "MemberExpr":
        receiver = expression((node.get("inner") or [{}])[0])
        return receiver + "." + as_name(node.get("name", "member"))
    if kind == "DeclRefExpr":
        return as_name(node.get("referencedDecl", {}).get("name", "unknown"))
    if kind in {"IntegerLiteral", "FloatingLiteral", "CharacterLiteral", "CXXBoolLiteralExpr"}:
        return str(node.get("value", "0")).lower()
    if kind == "CXXDefaultArgExpr":
        return expression((node.get("inner") or [{}])[0])
    if kind == "CXXConstructExpr":
        t = node.get("type", {}).get("qualType", "Object").replace("const ", "").strip()
        args = node.get("inner", [])
        if len(args) == 1:
            arg_type = args[0].get("type", {}).get("qualType", "")
            if arg_type.replace("const ", "").replace("&", "").strip() == t:
                return expression(args[0])
        return "new " + haxe_type(t) + "(" + ", ".join(expression(x) for x in args) + ")"
    if kind == "CXXMemberCallExpr":
        children = node.get("inner", [])
        callee = unwrap(children[0]) if children else {}
        name = expression(callee) if callee.get("kind") == "MemberExpr" else as_name(callee.get("name", "call"))
        return name + "(" + ", ".join(expression(x) for x in children[1:]) + ")"
    if kind == "CXXOperatorCallExpr":
        children = node.get("inner", [])
        callee = children[0] if children else {}
        while callee.get("inner"):
            callee = callee["inner"][0]
        op_name = callee.get("referencedDecl", {}).get("name", "")
        args = [expression(x) for x in children[1:]]
        if op_name == "operator=" and len(args) >= 2:
            return args[0] + " = " + args[1]
        helpers = {"operator*": "btVector3_mul", "operator-": "btVector3_sub"}
        if op_name in helpers and len(args) >= 2:
            return helpers[op_name] + "(" + args[0] + ", " + args[1] + ")"
        return "/* unsupported " + op_name + " */ " + ", ".join(args)
    if kind == "BinaryOperator":
        children = node.get("inner", [])
        if len(children) >= 2:
            return "(" + expression(children[0]) + " " + node.get("opcode", "=") + " " + expression(children[1]) + ")"
    return "/* unsupported " + kind + " */"


def statement(node, indent="\t", haxe=False):
    kind = node.get("kind")
    if kind == "CompoundStmt":
        return [line for child in node.get("inner", []) for line in statement(child, indent, haxe)]
    if kind in {"BinaryOperator", "CXXOperatorCallExpr"}:
        return [indent + expression(node) + ";"]
    if kind == "DeclStmt":
        lines = []
        for decl in node.get("inner", []):
            if decl.get("kind") == "VarDecl":
                init = decl.get("inner", [])
                rhs = expression(init[0]) if init else "null"
                var_type = haxe_type(decl.get("type", {}).get("qualType", ""))
                annotation = ":" + var_type if haxe else ""
                lines.append(indent + "var " + as_name(decl.get("name", "value")) + annotation + " = " + rhs + ";")
        return lines
    if kind == "CXXMemberCallExpr":
        return [indent + expression(node) + ";"]
    if kind in {"ExprWithCleanups", "CXXBindTemporaryExpr", "MaterializeTemporaryExpr"} and node.get("inner"):
        return statement(node["inner"][0], indent, haxe)
    return [indent + "// TODO translate " + kind]


def walk_nodes(node):
    if isinstance(node, dict):
        yield node
        for child in node.get("inner", []):
            yield from walk_nodes(child)


def project_classes(roots, requested_class=None):
    found = []

    def walk(node, current_file=""):
        if not isinstance(node, dict):
            return current_file
        loc = node.get("loc", {})
        file_name = loc.get("file") or node.get("range", {}).get("begin", {}).get("file") or current_file
        if (node.get("kind") == "CXXRecordDecl" and node.get("completeDefinition") and node.get("name")
                and file_name.startswith(("bullet/", "src/", "bullet3/src/"))
                and (requested_class is None or node.get("name") == requested_class)):
            found.append(node)
        for child in node.get("inner", []):
            file_name = walk(child, file_name)
        return file_name

    current_file = ""
    for root in roots:
        current_file = walk(root, current_file)
    unique = {}
    for record in found:
        unique.setdefault(record["name"], record)
    return list(unique.values())


def owner_from_mangled_name(mangled):
    if not mangled or not mangled.startswith("_ZN"):
        return None
    pos, components = 3, []
    while pos < len(mangled) and mangled[pos] in "KVRrO":
        pos += 1
    while pos < len(mangled) and mangled[pos] != "E":
        start = pos
        while pos < len(mangled) and mangled[pos].isdigit():
            pos += 1
        if start == pos:
            return None
        size = int(mangled[start:pos])
        component = mangled[pos:pos + size]
        if len(component) != size:
            return None
        components.append(component)
        pos += size
    return components[-2] if len(components) >= 2 else None


def stub_classes_from_methods(roots, requested_class=None):
    stubs = {}
    for root in roots:
        for node in walk_nodes(root):
            if node.get("kind") != "CXXMethodDecl":
                continue
            owner = owner_from_mangled_name(node.get("mangledName", ""))
            if not owner or (requested_class and owner != requested_class):
                continue
            record = stubs.setdefault(owner, {"kind": "CXXRecordDecl", "name": owner, "tagUsed": "class",
                "completeDefinition": True, "inner": [{"kind": "AccessSpecDecl", "access": "public"}]})
            record["inner"].append(node)
    return list(stubs.values())


def generate_as_record(record, definitions, include_constructor):
    # Keep ActionScript generation behavior in step with ast_to_as.py.
    class_name = record["name"]
    access, ctor, methods, seen = ("private" if record.get("tagUsed") == "class" else "public"), None, [], set()
    for child in record.get("inner", []):
        kind = child.get("kind")
        if kind == "AccessSpecDecl":
            access = child.get("access", access)
            continue
        if access != "public" or child.get("isImplicit"):
            continue
        name = child.get("name", "")
        if kind == "CXXConstructorDecl" and name == class_name and ctor is None:
            ctor = params(child)
        elif kind == "CXXMethodDecl" and name and not name.startswith("operator"):
            signature = child.get("type", {}).get("qualType", "")
            if (name, signature) not in seen:
                seen.add((name, signature))
                definition = next((d for d in definitions if d.get("kind") == "CXXMethodDecl"
                    and d.get("mangledName") == child.get("mangledName")
                    and any(c.get("kind") == "CompoundStmt" for c in d.get("inner", []))), None)
                methods.append((name, params(child), signature, definition))
    ctor_def = next((d for d in definitions if d.get("kind") == "CXXConstructorDecl"
                     and d.get("name") == class_name
                     and d.get("parentDeclContextId") == record.get("id")), None)
    base_calls, ctor_body = [], []
    if ctor_def:
        for item in ctor_def.get("inner", []):
            if item.get("kind") == "CXXCtorInitializer" and item.get("baseInit"):
                base_calls.append(as_name(item["baseInit"].get("qualType", "")) + ".call(this);")
            elif item.get("kind") == "CompoundStmt":
                ctor_body = statement(item)
    out = ["// Generated from Clang AST. Translated method bodies are emitted where supported; remaining methods use stubs."]
    if include_constructor:
        out.append(f"function {class_name}({', '.join(p[0] for p in (ctor or []))}) {{")
        out.extend("\t" + call for call in base_calls)
        out.extend(ctor_body)
        out.extend(["}", ""])
    used = {}
    for name, args, signature, definition in methods:
        safe = as_name(name)
        used[safe] = used.get(safe, 0) + 1
        if used[safe] > 1:
            safe += "_" + str(used[safe])
        out.append(f"{class_name}.prototype.{safe} = function({', '.join(p[0] for p in args)}) {{")
        body = next((c for c in definition.get("inner", []) if c.get("kind") == "CompoundStmt"), None) if definition else None
        if body is not None:
            out.extend(statement(body))
        else:
            default = type_default(signature.split("(", 1)[0].strip())
            if default:
                out.append("\treturn " + default + ";")
        out.extend(["};", ""])
    return "\n".join(out).rstrip() + "\n"


def generate_haxe_record(record, definitions, include_constructor):
    name = haxe_class_name(record["name"])
    access, ctor_params, methods, seen = ("private" if record.get("tagUsed") == "class" else "public"), [], [], set()
    for child in record.get("inner", []):
        if child.get("kind") == "AccessSpecDecl":
            access = child.get("access", access)
        elif access == "public" and not child.get("isImplicit"):
            kind, method_name = child.get("kind"), child.get("name", "")
            if kind == "CXXConstructorDecl" and method_name == record["name"] and not ctor_params:
                ctor_params = params(child)
            elif kind == "CXXMethodDecl" and method_name and not method_name.startswith("operator"):
                sig = child.get("type", {}).get("qualType", "")
                if (method_name, sig) not in seen:
                    seen.add((method_name, sig))
                    definition = next((d for d in definitions if d.get("kind") == "CXXMethodDecl"
                        and d.get("mangledName") == child.get("mangledName")
                        and any(c.get("kind") == "CompoundStmt" for c in d.get("inner", []))), None)
                    methods.append((method_name, params(child), sig, definition))
    # nativeGen avoids generating Dynamic-based constructors for native C++ types.
    # structAccess emits direct value access instead of pointer-style access.
    out = ["package;", "", "#if cpp", "import cpp.Reference;", "#end", "",
           "// Generated from Clang AST. Review translated bodies before using in production.",
           "#if cpp", "@:nativeGen", "@:structAccess", "#end", f"class {name}", "{"]
    if include_constructor:
        args = ", ".join(f"{p}:{haxe_type(t)}" for p, t in ctor_params)
        out.extend([f"\tpublic function new({args})", "\t{", "\t}", ""])
    for method_name, args, signature, definition in methods:
        return_type = haxe_type(signature.split("(", 1)[0].strip(), True)
        args_hx = ", ".join(f"{p}:{haxe_type(t)}" for p, t in args)
        out.extend([f"\tpublic function {as_name(method_name)}({args_hx}):{return_type}", "\t{"])
        body = next((c for c in definition.get("inner", []) if c.get("kind") == "CompoundStmt"), None) if definition else None
        if body:
            out.extend(statement(body, "\t\t", haxe=True))
        elif return_type != "Void":
            out.append("\t\treturn cast null;")
        out.extend(["\t}", ""])
    out.extend(["}", ""])
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", default="../a.json", help="AST JSON (default: ../a.json; use - for stdin)")
    parser.add_argument("-o", "--output", help="ActionScript output (default: ./orig/a/<Class>.as; use - for stdout)")
    parser.add_argument("--haxe-output", help="Haxe output (default: ./hx/a/<Class>.hx; use - to skip)")
    parser.add_argument("--class", dest="class_name", help="emit only this class")
    parser.add_argument("--stub-class", type=int, choices=(0, 1, 2), default=1,
                        help="no complete class: 0=error, 1=write nothing (default), 2=synthesize a stub class")
    args = parser.parse_args()
    try:
        records = list(read_json_stream(args.input))
        classes = project_classes(records, args.class_name)
        include_constructor = True
        if not classes:
            if args.stub_class in (1, 2):
                classes = stub_classes_from_methods(records, args.class_name)
                if not classes and args.stub_class == 2:
                    raise ValueError("no complete class or method suitable for a stub class found in the AST")
                if args.stub_class == 1:
                    include_constructor = False
            else:
                raise ValueError("no matching complete project class definitions found in the AST")
        definitions = [r for root in records for r in walk_nodes(root)
                       if r.get("kind") in {"CXXConstructorDecl", "CXXMethodDecl"}]
        as_result = "\n".join(generate_as_record(c, definitions, include_constructor) for c in classes)
        if any(token in as_result for token in ("btVector3_mul(", "btVector3_sub(")):
            as_result += "\nfunction btVector3_mul(a, b) {\n\treturn new btVector3(a.x() * b.x(), a.y() * b.y(), a.z() * b.z());\n}\n"
            as_result += "function btVector3_sub(a, b) {\n\treturn new btVector3(a.x() - b.x(), a.y() - b.y(), a.z() - b.z());\n}\n"
        hx_result = "\n".join(generate_haxe_record(c, definitions, include_constructor) for c in classes)
        output = args.output or ("./orig/a/" + haxe_class_name(classes[0]["name"]) + ".as" if classes
                                 else "./orig/a/Generated.as")
        haxe_output = args.haxe_output or ("./hx/a/" + haxe_class_name(classes[0]["name"]) + ".hx" if classes
                                           else "./hx/a/Generated.hx")
        if output == "-":
            sys.stdout.write(as_result)
        else:
            os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
            with open(output, "w", encoding="utf-8") as f:
                f.write(as_result)
        if haxe_output != "-":
            os.makedirs(os.path.dirname(haxe_output) or ".", exist_ok=True)
            with open(haxe_output, "w", encoding="utf-8") as f:
                f.write(hx_result)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
