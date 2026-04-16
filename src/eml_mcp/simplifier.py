"""
EML Tree Simplifier (E-Graph / Equality Saturation)
===================================================

Reduces redundant EML compositions and performs constant folding to minimize
tree complexity (node count K). This uses an Equality Graph to find the globally
simplest equivalent tree.
"""

import collections
import math
import cmath
from typing import Any
from eml_mcp.primitives import _safe_exp, _safe_log
from eml_mcp.trees import EMLNode, NodeType, const, eml_node, var

# Pattern shorthand
C1 = ("const_1",)


RULES = [
    # exp(ln(z)) -> z
    # exp(x) = eml(x, 1)
    # ln(z) = eml(1, eml(eml(1, z), 1))
    (("eml", ("eml", C1, ("eml", ("eml", C1, "?z"), C1)), C1), "?z"),
    # ln(exp(z)) -> z
    (("eml", C1, ("eml", ("eml", C1, ("eml", "?z", C1)), C1)), "?z"),
]


class EGraph:
    def __init__(self):
        self.union_find = {}
        self.classes = collections.defaultdict(set)
        self.hashcons = {}
        self.next_id = 0

    def find(self, i: int) -> int:
        if i not in self.union_find:
            return i
        if self.union_find[i] == i:
            return i
        self.union_find[i] = self.find(self.union_find[i])
        return self.union_find[i]

    def add(self, enode: tuple) -> int:
        if enode[0] == "eml":
            enode = ("eml", self.find(enode[1]), self.find(enode[2]))
        elif enode[0] == "call":
            enode = ("call", enode[1], tuple((k, self.find(v)) for k, v in enode[2]))
        elif enode[0] == "const":
            for existing_enode in self.hashcons:
                if existing_enode[0] == "const":
                    try:
                        diff = existing_enode[1] - enode[1]
                        if not cmath.isnan(diff):
                            if abs(diff) < 1e-15:
                                return self.find(self.hashcons[existing_enode])
                        else:
                            if str(existing_enode[1]) == str(enode[1]):
                                return self.find(self.hashcons[existing_enode])
                    except Exception:
                        pass

        if enode in self.hashcons:
            return self.find(self.hashcons[enode])

        i = self.next_id
        self.next_id += 1
        self.union_find[i] = i
        self.classes[i].add(enode)
        self.hashcons[enode] = i
        return i

    def merge(self, i: int, j: int) -> int:
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i == root_j:
            return root_i

        self.union_find[root_j] = root_i
        self.classes[root_i].update(self.classes[root_j])
        del self.classes[root_j]

        # Basic congruence closure
        changed = True
        while changed:
            changed = False
            new_hashcons = {}
            for enode, eclass in list(self.hashcons.items()):
                new_eclass = self.find(eclass)
                new_enode = enode
                if enode[0] == "eml":
                    new_enode = ("eml", self.find(enode[1]), self.find(enode[2]))
                elif enode[0] == "call":
                    new_enode = ("call", enode[1], tuple((k, self.find(v)) for k, v in enode[2]))

                if new_enode in new_hashcons:
                    other_eclass = new_hashcons[new_enode]
                    if new_eclass != other_eclass:
                        root_other = self.find(other_eclass)
                        if new_eclass != root_other:
                            self.union_find[new_eclass] = root_other
                            self.classes[root_other].update(self.classes[new_eclass])
                            del self.classes[new_eclass]
                            new_eclass = root_other
                            changed = True
                new_hashcons[new_enode] = new_eclass
            self.hashcons = new_hashcons

        return root_i

    def insert_tree(self, node: EMLNode) -> int:
        if node.node_type == NodeType.CONST:
            return self.add(("const", node.value))
        elif node.node_type == NodeType.VAR:
            return self.add(("var", node.var_name))
        elif node.node_type == NodeType.EML:
            left_id = self.insert_tree(node.left)
            right_id = self.insert_tree(node.right)
            return self.add(("eml", left_id, right_id))
        elif node.node_type == NodeType.CALL:
            args_ids = (
                tuple(sorted((k, self.insert_tree(v)) for k, v in node.args.items()))
                if node.args
                else ()
            )
            return self.add(("call", node.func_name, args_ids))
        else:
            raise ValueError(f"Unsupported node type for e-graph: {node.node_type}")


def egraph_matches(egraph: EGraph, eclass_id: int, pattern: Any) -> list[dict[str, int]]:
    if isinstance(pattern, str) and pattern.startswith("?"):
        return [{pattern: egraph.find(eclass_id)}]

    eclass_id = egraph.find(eclass_id)
    matches = []

    for enode in egraph.classes[eclass_id]:
        if pattern == ("const_1",):
            if enode[0] == "const":
                try:
                    if not cmath.isnan(enode[1]) and abs(enode[1] - 1.0) < 1e-15:
                        matches.append({})
                except Exception:
                    pass
        elif pattern[0] == "eml" and enode[0] == "eml":
            left_matches = egraph_matches(egraph, enode[1], pattern[1])
            if not left_matches:
                continue
            right_matches = egraph_matches(egraph, enode[2], pattern[2])
            if not right_matches:
                continue

            for lm in left_matches:
                for rm in right_matches:
                    conflict = False
                    env = lm.copy()
                    for k, v in rm.items():
                        if k in env and env[k] != v:
                            conflict = True
                            break
                        env[k] = v
                    if not conflict:
                        matches.append(env)
    return matches


def run_rewrites(egraph: EGraph) -> bool:
    changed = False

    # 1. Constant folding
    for eclass_id, enodes in list(egraph.classes.items()):
        for enode in list(enodes):
            if enode[0] == "eml":
                l_consts = [n for n in egraph.classes[egraph.find(enode[1])] if n[0] == "const"]
                r_consts = [n for n in egraph.classes[egraph.find(enode[2])] if n[0] == "const"]
                if l_consts and r_consts:
                    v1 = l_consts[0][1]
                    v2 = r_consts[0][1]
                    try:
                        res = _safe_exp(v1) - _safe_log(v2)
                        new_id = egraph.add(("const", res))
                        if egraph.find(eclass_id) != egraph.find(new_id):
                            egraph.merge(eclass_id, new_id)
                            changed = True
                    except Exception:
                        pass

    # 2. Pattern rules
    for lhs, rhs in RULES:
        for eclass_id in list(egraph.classes.keys()):
            for env in egraph_matches(egraph, eclass_id, lhs):
                if isinstance(rhs, str) and rhs.startswith("?"):
                    target_id = env[rhs]
                    if egraph.find(eclass_id) != egraph.find(target_id):
                        egraph.merge(eclass_id, target_id)
                        changed = True

    return changed


def extract_best(egraph: EGraph, root_id: int) -> EMLNode:
    costs = {}

    changed = True
    while changed:
        changed = False
        for eclass_id, enodes in egraph.classes.items():
            for enode in enodes:
                cost = float("inf")
                if enode[0] in ("const", "var"):
                    cost = 1
                elif enode[0] == "eml":
                    c_left = egraph.find(enode[1])
                    c_right = egraph.find(enode[2])
                    if c_left in costs and c_right in costs:
                        cost = 1 + costs[c_left][0] + costs[c_right][0]
                elif enode[0] == "call":
                    args_costs = [
                        costs[egraph.find(v)][0] for _, v in enode[2] if egraph.find(v) in costs
                    ]
                    if len(args_costs) == len(enode[2]):
                        cost = 1 + sum(args_costs)

                if cost < float("inf"):
                    if eclass_id not in costs or cost < costs[eclass_id][0]:
                        costs[eclass_id] = (cost, enode)
                        changed = True

    def build_tree(eclass_id: int) -> EMLNode:
        eclass_id = egraph.find(eclass_id)
        enode = costs[eclass_id][1]
        if enode[0] == "const":
            return const(enode[1])
        elif enode[0] == "var":
            return var(enode[1])
        elif enode[0] == "eml":
            return eml_node(build_tree(enode[1]), build_tree(enode[2]))
        elif enode[0] == "call":
            args = {k: build_tree(v_id) for k, v_id in enode[2]}
            return EMLNode(node_type=NodeType.CALL, func_name=enode[1], args=args)

    return build_tree(egraph.find(root_id))


def simplify_tree(node: EMLNode) -> EMLNode:
    """Simplify an EML tree using Equality Saturation."""
    if node.node_type not in (NodeType.EML, NodeType.CONST, NodeType.VAR, NodeType.CALL):
        return node.copy()

    egraph = EGraph()
    root_id = egraph.insert_tree(node)

    # Saturation loop (limit iterations to prevent infinite loops)
    for _ in range(10):
        if not run_rewrites(egraph):
            break

    return extract_best(egraph, root_id)


def get_exp_input(node: EMLNode) -> EMLNode | None:
    """Check if node is exp(z) = eml(z, 1) and return z."""
    if node.node_type == NodeType.EML:
        if node.right.node_type == NodeType.CONST and abs(node.right.value - 1.0) < 1e-15:
            return node.left
    return None


def get_ln_input(node: EMLNode) -> EMLNode | None:
    """Check if node is ln(z) = eml(1, eml(eml(1, z), 1)) and return z."""
    if node.node_type != NodeType.EML:
        return None
    if not (node.left.node_type == NodeType.CONST and abs(node.left.value - 1.0) < 1e-15):
        return None

    middle = node.right
    if middle.node_type != NodeType.EML:
        return None
    if not (middle.right.node_type == NodeType.CONST and abs(middle.right.value - 1.0) < 1e-15):
        return None

    inner = middle.left
    if inner.node_type != NodeType.EML:
        return None
    if not (inner.left.node_type == NodeType.CONST and abs(inner.left.value - 1.0) < 1e-15):
        return None

    return inner.right
