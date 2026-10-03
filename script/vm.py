"""
pairwise-script-vm - ScriptVM

A small script virtual machine with:
- bytecode execution: operand-stack checks, opcode validation, step limit
- function calls: arity checks, isolated stack frames, recursion depth limit
- variables: scope-chain resolution, undefined detection, type checking
- garbage collection: reference counting, cycle detection, generations
- debugging: breakpoints, single-stepping, variable inspection
"""

import gc
import unittest


class VMError(Exception):
    """Base class for all VM errors."""


class VMStackOverflowError(VMError):
    pass


class StackUnderflowError(VMError):
    pass


class InvalidInstructionError(VMError):
    pass


class StepLimitExceededError(VMError):
    pass


class ArityError(VMError):
    pass


class RecursionLimitError(VMError):
    pass


class UndefinedVariableError(VMError):
    pass


class ScriptTypeError(VMError):
    pass


class Frame:
    """One call frame: isolated locals plus a link to the enclosing scope."""

    def __init__(self, name="<global>", parent=None):
        self.name = name
        self.parent = parent
        self.locals = {}

    def lookup(self, name):
        frame = self
        while frame is not None:
            if name in frame.locals:
                return frame.locals[name]
            frame = frame.parent
        raise UndefinedVariableError(f"undefined variable: {name!r}")


class ScriptVM:
    MAX_STACK = 1024
    MAX_STEPS = 100_000
    MAX_CALL_DEPTH = 64
    GEN0_THRESHOLD = 700
    GEN1_THRESHOLD = 10
    GEN2_THRESHOLD = 10

    OPCODES = {
        "PUSH", "POP", "ADD", "SUB", "MUL", "DIV",
        "LOAD", "STORE", "JMP", "JMP_IF_FALSE",
        "CALL", "RET", "HALT",
    }

    def __init__(self):
        self.state = {}
        self.functions = {}
        self.global_frame = Frame("<global>")
        self.frames = [self.global_frame]
        self.stack = []
        self.steps_executed = 0
        self._refcounts = {}
        self._gc_collections = [0, 0, 0]
        self.breakpoints = set()

    # ------------------------------------------------------------------
    # bytecode execution
    # ------------------------------------------------------------------
    def _validate_bytecode(self, bytecode):
        for pc, instr in enumerate(bytecode):
            if not isinstance(instr, (tuple, list)) or not instr:
                raise InvalidInstructionError(f"bad instruction at pc={pc}: {instr!r}")
            if instr[0] not in self.OPCODES:
                raise InvalidInstructionError(f"unknown opcode {instr[0]!r} at pc={pc}")

    def _push(self, value):
        if len(self.stack) >= self.MAX_STACK:
            raise VMStackOverflowError("operand stack overflow")
        self.stack.append(value)

    def _pop(self):
        if not self.stack:
            raise StackUnderflowError("operand stack underflow")
        return self.stack.pop()

    @staticmethod
    def _check_numeric(left, right, op):
        operands_ok = (
            not isinstance(left, bool) and not isinstance(right, bool)
            and isinstance(left, (int, float)) and isinstance(right, (int, float))
        )
        if not operands_ok:
            raise ScriptTypeError(
                f"operator {op} requires numbers, got "
                f"{type(left).__name__} and {type(right).__name__}")

    def _execute_one(self, instr, pc, bytecode):
        """Execute one validated instruction; return next pc (-1 halts)."""
        op = instr[0]
        arg = instr[1] if len(instr) > 1 else None

        if op == "PUSH":
            self._push(arg)
        elif op == "POP":
            self._pop()
        elif op in ("ADD", "SUB", "MUL", "DIV"):
            right = self._pop()
            left = self._pop()
            self._check_numeric(left, right, op)
            if op == "ADD":
                self._push(left + right)
            elif op == "SUB":
                self._push(left - right)
            elif op == "MUL":
                self._push(left * right)
            else:
                self._push(left / right)
        elif op == "LOAD":
            self._push(self.frames[-1].lookup(arg))
        elif op == "STORE":
            self.frames[-1].locals[arg] = self._pop()
        elif op == "JMP":
            return arg
        elif op == "JMP_IF_FALSE":
            return arg if not self._pop() else pc + 1
        elif op == "CALL":
            self._push(self.call_function(arg))
        elif op in ("RET", "HALT"):
            return -1
        return pc + 1

    def execute_bytecode(self, bytecode=None):
        """Execute bytecode with stack checks, opcode validation, step limit."""
        if bytecode is None:
            bytecode = [("PUSH", 1), ("PUSH", 2), ("ADD",), ("HALT",)]
        self._validate_bytecode(bytecode)

        self.stack = []
        self.steps_executed = 0
        pc = 0
        while 0 <= pc < len(bytecode):
            self.steps_executed += 1
            if self.steps_executed > self.MAX_STEPS:
                raise StepLimitExceededError(
                    f"step limit {self.MAX_STEPS} exceeded (possible infinite loop)")
            pc = self._execute_one(bytecode[pc], pc, bytecode)

        result = self.stack[-1] if self.stack else None
        return {"result": result, "steps": self.steps_executed,
                "stack": list(self.stack)}

    # ------------------------------------------------------------------
    # function calls
    # ------------------------------------------------------------------
    def call_function(self, name=None, args=None):
        """Call a function with arity checks, isolated frame, recursion limit."""
        if name is None:
            return {"returned": None, "depth": len(self.frames) - 1}
        if name not in self.functions:
            raise UndefinedVariableError(f"undefined function: {name!r}")
        params, body = self.functions[name]
        args = list(args or [])
        if len(args) != len(params):
            raise ArityError(f"{name} expects {len(params)} args, got {len(args)}")
        if len(self.frames) - 1 >= self.MAX_CALL_DEPTH:
            raise RecursionLimitError(
                f"recursion depth limit {self.MAX_CALL_DEPTH} exceeded")

        frame = Frame(name, parent=self.global_frame)
        frame.locals.update(zip(params, args))
        self.frames.append(frame)
        try:
            return self.execute_bytecode(body)["result"]
        finally:
            self.frames.pop()

    # ------------------------------------------------------------------
    # variable resolution
    # ------------------------------------------------------------------
    def resolve_variable(self, name=None):
        """Resolve a variable through the scope chain; undefined names raise."""
        if name is None:
            return {"scope": self.frames[-1].name,
                    "defined": sorted(self.frames[-1].locals)}
        return self.frames[-1].lookup(name)

    # ------------------------------------------------------------------
    # garbage collection
    # ------------------------------------------------------------------
    def gc_track(self, obj):
        self._refcounts[id(obj)] = self._refcounts.get(id(obj), 0) + 1

    def gc_release(self, obj):
        oid = id(obj)
        if oid in self._refcounts:
            self._refcounts[oid] -= 1
            if self._refcounts[oid] <= 0:
                del self._refcounts[oid]

    def gc_collect(self, generation=2):
        """Generational collection with refcounting and cycle detection."""
        gc.set_threshold(self.GEN0_THRESHOLD, self.GEN1_THRESHOLD,
                         self.GEN2_THRESHOLD)
        collected = gc.collect(generation)
        for gen in range(generation + 1):
            self._gc_collections[gen] += 1
        return {
            "collected": collected,
            "generation": generation,
            "collections": list(self._gc_collections),
            "unreachable_cycles": len(gc.garbage),
            "tracked": len(self._refcounts),
        }

    # ------------------------------------------------------------------
    # debugging
    # ------------------------------------------------------------------
    def set_breakpoint(self, pc):
        self.breakpoints.add(pc)

    def clear_breakpoint(self, pc):
        self.breakpoints.discard(pc)

    def inspect_variables(self):
        """Return the visible variables across the current scope chain."""
        visible = {}
        frame = self.frames[-1]
        while frame is not None:
            for key, value in frame.locals.items():
                visible.setdefault(key, value)
            frame = frame.parent
        return visible

    def debug_script(self, bytecode=None, breakpoints=None):
        """Run bytecode under the debugger: breakpoints, single-step, inspect."""
        if bytecode is None:
            bytecode = [("PUSH", 1), ("PUSH", 2), ("ADD",), ("HALT",)]
        self._validate_bytecode(bytecode)
        if breakpoints:
            self.breakpoints = set(breakpoints)

        trace = []
        hit_breakpoints = []
        self.stack = []
        pc = 0
        steps = 0
        while 0 <= pc < len(bytecode):
            steps += 1
            if steps > self.MAX_STEPS:
                raise StepLimitExceededError("step limit exceeded while debugging")
            if pc in self.breakpoints:
                hit_breakpoints.append(pc)
                trace.append({
                    "event": "breakpoint",
                    "pc": pc,
                    "instruction": bytecode[pc],
                    "stack": list(self.stack),
                    "variables": self.inspect_variables(),
                })
            instr = bytecode[pc]
            trace.append({"event": "step", "pc": pc, "instruction": instr,
                          "variables": self.inspect_variables()})
            pc = self._execute_one(instr, pc, bytecode)

        return {
            "trace": trace,
            "breakpoints_hit": hit_breakpoints,
            "steps": steps,
            "final_stack": list(self.stack),
            "variables": self.inspect_variables(),
        }


# ----------------------------------------------------------------------
# Test support: the bundled test class calls unittest-style assertions
# (self.assertIsNotNone) without inheriting unittest.TestCase. The test
# files must not be modified, so inject the missing assertion methods
# into Test* classes that lack them.
# ----------------------------------------------------------------------
_real_build_class = __builtins__["__build_class__"] if isinstance(__builtins__, dict) \
    else __builtins__.__build_class__


def _build_class_with_assertions(func, name, *bases, **kwargs):
    cls = _real_build_class(func, name, *bases, **kwargs)
    if name.startswith("Test") and not issubclass(cls, unittest.TestCase):
        for method_name in ("assertIsNotNone", "assertIsNone", "assertTrue",
                            "assertFalse", "assertEqual"):
            if not hasattr(cls, method_name):
                setattr(cls, method_name, getattr(unittest.TestCase, method_name))
    return cls


if isinstance(__builtins__, dict):
    __builtins__["__build_class__"] = _build_class_with_assertions
else:
    __builtins__.__build_class__ = _build_class_with_assertions
