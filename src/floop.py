from lark import Lark, Transformer, Visitor
import sys

grammar = r"""
    start: decl* call?
    decl: "DEFINE" "PROCEDURE" "\"" procname "\"" params ":" block
    params: "[" param ("," param)* "]"
    param: /[A-Z]+/
    procname: testname | funcname
    testname: /[a-zA-Z0-9_]+\?/
    funcname: /[a-zA-Z0-9_]+/
    block: "BLOCK" NUMBER ":" "BEGIN" stmt* "BLOCK" NUMBER ":" "END"
    stmt: loop | cond | quit | abort | muloop | assign
    loophead: "LOOP" intval "TIMES" | "LOOP" "AT" "MOST" intval "TIMES"
    loop: loophead ":" block
    muloop: "MU-LOOP" ":" block
    assign: lvalue "<=" expr ";"
    lvalue: cell | output
    cell: "CELL" "(" NUMBER ")"
    expr: boolexpr | intexpr
    intexpr: intval PLUS intval | intval TIMES intval | intval
    boolexpr: boolval EQ boolval | intval EQ intval | intval LT intval | intval GT intval | boolval
    intval: num | cellfetch | outputfetch | call | paramfetch
    boolval: bool | cellfetch | outputfetch | call
    cellfetch: cell
    paramfetch: param
    outputfetch: output
    val: intval | boolval
    cond: "IF" boolexpr "," "THEN" ":" block
    quit: "QUIT" "BLOCK" NUMBER ";"
    abort: "ABORT" "LOOP" NUMBER ";"
    output: "OUTPUT"
    bool: YES | NO
    num: NUMBER
    call: procname "(" intval ("," intval)* ")"
    PLUS: "+"
    TIMES: "*"
    EQ: "="
    LT: "<"
    GT: ">"
    YES: "YES"
    NO: "NO"
    NUMBER: /[1-9]/ /[0-9]/* | "0"
    %import common.WS
    %ignore WS
"""

parser = Lark(grammar)

class SemanticError(Exception):
    def __init__(self, message, token):
        super().__init__(f"[{token.line}:{token.column}]: {message}")
        self.token = token

class CheckBlocks(Visitor):
    def block(self, tree):
        start_num = int(tree.children[0])
        end_num = int(tree.children[-1])

        if start_num != end_num:
            raise SemanticError(f"Block numbers do not match: {start_num} vs {end_num}", tree.children[0])

class Cell:
    def __init__(self, index):
        self.index = index

class Abort(Exception):
    def __init__(self, blocknum):
        super().__init__("ABORT does not belong to any loop")
        self.blocknum = blocknum

class Break(Exception):
    def __init__(self, blocknum):
        super().__init__("QUIT does not belong to any block")
        self.blocknum = blocknum

def runinstr(tup, decls, cells, params):
    instr, *args = tup
    if instr == "bool" or instr == "num" or instr == "output":
        return args[0]
    elif instr == "abort":
        blocknum = args[0]
        raise Abort(blocknum)
    elif instr == "quit":
        blocknum = args[0]
        raise Break(blocknum)
    elif instr == "cond":
        cond = runinstr(args[0], decls, cells, params)
        if cond:
            runinstr(args[1], decls, cells, params)
    elif instr == "eq" or instr == "lt" or instr == "gt" or instr == "plus" or instr == "times":
        a = runinstr(args[0], decls, cells, params)
        b = runinstr(args[1], decls, cells, params)
        if instr == "eq":
            return a == b
        elif instr == "lt":
            return a < b
        elif instr == "gt":
            return a > b
        elif instr == "plus":
            return a + b
        else:
            assert instr == "times"
            return a * b
    elif instr == "cell":
        return Cell(args[0])
    elif instr == "cellfetch":
        return cells[args[0]]
    elif instr == "paramfetch":
        return params[args[0]]
    elif instr == "assign":
        left = runinstr(args[0], decls, cells, params)
        assert isinstance(left, Cell)
        cells[left.index] = runinstr(args[1], decls, cells, params)
    elif instr == "loop":
        if args[0] is None:
            while True:
                try:
                    runinstr(args[1], decls, cells, params)
                except Abort as a:
                    _, blocknum, _ = args[1]
                    if a.blocknum == blocknum:
                        break
                    else:
                        raise a
        bound = runinstr(args[0], decls, cells, params)
        for i in range(bound):
            try:
                runinstr(args[1], decls, cells, params)
            except Abort as a:
                _, blocknum, _ = args[1]
                if a.blocknum == blocknum:
                    break
                else:
                    raise a
    elif instr == "block":
        blocknum = args[0]
        try:
            run(args[1], decls, cells, params)
        except Break as b:
            if b.blocknum != blocknum:
                raise b
    elif instr == "decl":
        procname, params, block = args
        decls[procname] = (params, block)
    else:
        assert instr == "call"
        procname, args = args

        funcargs = []
        for arg in args:
            funcargs.append(runinstr(arg, decls, cells, params))

        funcparams, block = decls[procname]
        funcargs = dict(zip(funcparams, funcargs))
        default_output = False if procname.endswith("?") else 0
        cells = {-1: default_output}
        try:
            runinstr(block, decls, cells, funcargs)
        except Abort as a:
            raise Exception(a.str())
        except Break as b:
            raise Exception(b.str())
        return cells[-1]
    return None

def run(instrs, decls, cells, params):
    res = None
    for tup in instrs:
        res = runinstr(tup, decls, cells, params)
    return res

class Sema(Transformer):
    def start(self, items):
        return items
    def decl(self, items):
        procname, params, block = items
        return ("decl", procname, params, block)
    def params(self, toks):
        return toks
    def param(self, toks):
        return str(toks[0])
    def procname(self, toks):
        return str(toks[0])
    def testname(self, toks):
        return str(toks[0]) + "?"
    def funcname(self, toks):
        return str(toks[0])
    def block(self, items):
        blocknum = int(items[0])
        assert int(items[-1]) == blocknum
        stmts = items[1:-1]
        return ("block", blocknum, stmts)
    def stmt(self, items):
        return items[0]
    def loophead(self, items):
        return items[0]
    def loop(self, items):
        bound = items[0]
        block = items[1]
        return ("loop", bound, block)
    def muloop(self, items):
        block = items[0]
        return ("loop", None, block)
    def assign(self, items):
        return ("assign", items[0], items[1])
    def lvalue(self, items):
        return items[0]
    def cell(self, items):
        index = int(items[0])
        return ("cell", index)
    def expr(self, items):
        return items[0]
    def intexpr(self, items):
        if len(items) == 3:
            a = items[0]
            b = items[2]
            op = str(items[1])
            if op == "+":
                return ("plus", a, b)
            else:
                assert op == "*"
                return ("times", a, b)
        else:
            return items[0]
    def boolexpr(self, items):
        if len(items) == 3:
            a = items[0]
            b = items[2]
            op = str(items[1])
            if op == "=":
                return ("eq", a, b)
            elif op == "<":
                return ("lt", a, b)
            else:
                assert op == ">"
                return ("gt", a, b)
        else:
            return items[0]
    def intval(self, items):
        return items[0]
    def boolval(self, items):
        return items[0]
    def cond(self, items):
        return ("cond", items[0], items[1])
    def quit(self, items):
        blockidx = int(items[0])
        return ("quit", blockidx)
    def abort(self, items):
        loopidx = int(items[0])
        return ("abort", loopidx)
    def output(self, items):
        return ("cell", -1)
    def bool(self, items):
        variant = str(items[0])
        assert variant == "YES" or variant == "NO"
        return ("bool", variant == "YES")
    def num(self, items):
        return ("num", items[0])
    def cellfetch(self, items):
        instr, index = items[0]
        assert instr == "cell"
        return ("cellfetch", index)
    def paramfetch(self, items):
        return ("paramfetch", items[0])
    def outputfetch(self, items):
        return ("cellfetch", -1)
    def call(self, items):
        procname = str(items[0])
        args = items[1:]
        return ("call", procname, args)
    def NUMBER(self, items):
        return int(items)

if __name__ == "__main__":
    filepath = sys.argv[1]
    print(f"Interpreting {filepath}...")
    with open(filepath, "r") as f:
        prog = f.read()

    try:
        tree = parser.parse(prog)
        CheckBlocks().visit(tree)
        ev = Sema().transform(tree)
        res = run(ev, {}, {}, {})
        print(f"Result: {res}")
    except SemanticError as e:
        print(f"Error {e}")
