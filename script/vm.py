"""
pairwise-script-vm - ScriptVM

This module contains a deliberately broken implementation.
Fix all bugs so that tests pass.
"""


class ScriptVM:
    def __init__(self):
        self.state = {}

    def execute_bytecode(self, *args, **kwargs):
        """BUG: 字节码执行不做栈检查，栈溢出直接崩溃"""
        return None

    def call_function(self, *args, **kwargs):
        """BUG: 函数调用不做参数检查，参数多了少了都不报错"""
        return None

    def resolve_variable(self, *args, **kwargs):
        """BUG: 变量解析不做作用域链，全局变量和局部变量混在一起"""
        return None

    def gc_collect(self, *args, **kwargs):
        """BUG: 垃圾回收不做引用计数，对象永远不释放"""
        return None

    def debug_script(self, *args, **kwargs):
        """BUG: 调试不做断点，不能暂停执行"""
        return None

