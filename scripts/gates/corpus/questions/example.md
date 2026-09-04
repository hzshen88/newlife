# Question — 示例：漂移的步长是不是恒定的

上游 goal：`goals/example.md`

验证脚本：`verification/example_check.py`——**内容哈希只写在锚里，散文不复述**
（同一事实写两遍，第二遍迟早漂移）。<!--@script: sha256=436acb80d89e398fc03e2733d1977b7bf68b402a3f5b3e903ecb95c52d195934-->

---

## 判据与实测

轨迹长度为 13。<!--@check-1: path_len=13-->
本条覆盖 <!--@check-1: covers=drift--> 这一个生产函数。<!--@goal: C1-->

末态为 24。<!--@check-2: endpoint=24-->
本条同时走到 <!--@check-2: covers=endpoint-->。<!--@goal: C2-->

相邻步长只有一个取值。<!--@check-3: distinct_gaps=1--><!--@goal: C3-->


## 结局

<!--@outcome: C1=constant-->
