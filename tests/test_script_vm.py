import pytest
from script.vm import ScriptVM


class TestScriptVM:

    def test_execute_bytecode(self):
        """字节码执行不做栈检查，栈溢出直接崩溃"""
        obj = ScriptVM()
        result = obj.execute_bytecode()
        self.assertIsNotNone(result)

    def test_call_function(self):
        """函数调用不做参数检查，参数多了少了都不报错"""
        obj = ScriptVM()
        result = obj.call_function()
        self.assertIsNotNone(result)

    def test_resolve_variable(self):
        """变量解析不做作用域链，全局变量和局部变量混在一起"""
        obj = ScriptVM()
        result = obj.resolve_variable()
        self.assertIsNotNone(result)

    def test_gc_collect(self):
        """垃圾回收不做引用计数，对象永远不释放"""
        obj = ScriptVM()
        result = obj.gc_collect()
        self.assertIsNotNone(result)

    def test_debug_script(self):
        """调试不做断点，不能暂停执行"""
        obj = ScriptVM()
        result = obj.debug_script()
        self.assertIsNotNone(result)

