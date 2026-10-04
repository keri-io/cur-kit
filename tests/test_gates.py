from scripts.gates import check_source


def _function(name: str, body_lines: int) -> str:
    body = "".join(f"    x{i} = {i}\n" for i in range(body_lines))
    return f"def {name}():\n{body}"


def test_ac23_compliant_module_passes():
    assert check_source("def f(a, b):\n    return a + b\n", "ok.py") == []


def test_ac23_long_function_is_flagged():
    problems = check_source(_function("long", 20), "long.py")
    assert any("long" in p and "21 lines" in p for p in problems)


def test_ac23_too_many_params_is_flagged_but_self_is_free():
    source = "class C:\n    def m(self, a, b, c):\n        return a\n\ndef f(a, b, c, d):\n    return a\n"
    problems = check_source(source, "p.py")
    assert any("f" in p and "4 params" in p for p in problems)
    assert not any("m " in p or "'m'" in p for p in problems)


def test_ac23_nesting_three_is_flagged_but_elif_chains_are_not():
    deep = "def f(a):\n    for x in a:\n        if x:\n            if x > 1:\n                return x\n"
    chain = "def g(a):\n    if a == 1:\n        return 1\n    elif a == 2:\n        return 2\n    elif a == 3:\n        return 3\n"
    assert any("nesting 3" in p for p in check_source(deep, "d.py"))
    assert check_source(chain, "c.py") == []


def test_ac23_too_many_functions_is_flagged():
    source = "\n".join(f"def f{i}():\n    return {i}\n" for i in range(11))
    assert any("11 functions" in p for p in check_source(source, "many.py"))


def test_ac23_long_file_is_flagged():
    source = "\n".join(f"x{i} = {i}" for i in range(201)) + "\n"
    assert any("201 lines" in p for p in check_source(source, "big.py"))
