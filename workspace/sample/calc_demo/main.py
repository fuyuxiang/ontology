from ontology_runtime import Function, call_function


@Function(
    name="calc_demo",
    description="演示函数：输入数字翻倍返回",
    type="logic",
    params=[
        {"name": "x", "type": "number", "required": True, "description": "输入数字"},
    ],
    return_type="number",
)
def calc_demo(params):
    return params["x"] * 2
