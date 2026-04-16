"""
EML Tree Similarity
===================

Implements Zhang-Shasha Tree Edit Distance (TED) for comparing EML formulas.
Used for ranking by structural simplicity and deduplication.
"""

from __future__ import annotations

from dataclasses import dataclass

from eml_mcp.trees import EMLNode, NodeType


@dataclass
class TEDNode:
    """Internal node representation for Zhang-Shasha algorithm."""

    label: str
    children: list[TEDNode]


def _to_ted_node(node: EMLNode) -> TEDNode:
    """Convert EMLNode to TEDNode."""
    if node.node_type == NodeType.CONST:
        label = f"const:{node.value}"
        children = []
    elif node.node_type == NodeType.VAR:
        label = f"var:{node.var_name}"
        children = []
    else:
        label = "eml"
        children = [_to_ted_node(node.left), _to_ted_node(node.right)]
    return TEDNode(label=label, children=children)


def _get_post_order(node: TEDNode) -> list[TEDNode]:
    """Get nodes in post-order traversal."""
    nodes = []
    for child in node.children:
        nodes.extend(_get_post_order(child))
    nodes.append(node)
    return nodes


def tree_edit_distance(t1: EMLNode, t2: EMLNode) -> int:
    """Compute the Zhang-Shasha tree edit distance between two EML trees."""
    # 1. Convert to internal representation
    root1 = _to_ted_node(t1)
    root2 = _to_ted_node(t2)

    # 2. Get post-order nodes
    nodes1 = _get_post_order(root1)
    nodes2 = _get_post_order(root2)

    n1 = len(nodes1)
    n2 = len(nodes2)

    # 3. Compute leftmost leaf indices (l())
    def get_leftmost(nodes):
        l_idx = [0] * len(nodes)
        for i, node in enumerate(nodes):
            if not node.children:
                l_idx[i] = i
            else:
                # Leftmost of first child
                # Post-order: children of nodes[i] are before it.
                # The leftmost leaf of node i is the leftmost leaf of its first child.
                # But we need the index in 'nodes' array.
                curr = node
                while curr.children:
                    curr = curr.children[0]
                # Find index of curr in nodes
                for j in range(i + 1):
                    if nodes[j] is curr:
                        l_idx[i] = j
                        break
        return l_idx

    l1 = get_leftmost(nodes1)
    l2 = get_leftmost(nodes2)

    # 4. Key roots (nodes that have a left sibling or are the root)
    def get_keyroots(l_idx):
        kr = []
        for i, l_val in enumerate(l_idx):
            is_keyroot = True
            for j in range(i + 1, len(l_idx)):
                if l_idx[j] == l_val:
                    is_keyroot = False
                    break
            if is_keyroot:
                kr.append(i)
        return kr

    kr1 = get_keyroots(l1)
    kr2 = get_keyroots(l2)

    td = [[0] * (n2) for _ in range(n1)]

    def cost(n1_obj, n2_obj):
        return 0 if n1_obj.label == n2_obj.label else 1

    # 5. Main Zhang-Shasha loop
    for i in kr1:
        for j in kr2:
            # Forest Distance DP
            # fd[x, y] = dist between forest nodes1[l1[i]...x] and nodes2[l2[j]...y]
            # Offset indices to handle empty forest
            offset1 = l1[i]
            offset2 = l2[j]
            size1 = i - offset1 + 1
            size2 = j - offset2 + 1
            fd = [[0] * (size2 + 1) for _ in range(size1 + 1)]

            for x in range(1, size1 + 1):
                fd[x][0] = fd[x - 1][0] + 1
            for y in range(1, size2 + 1):
                fd[0][y] = fd[0][y - 1] + 1

            for x in range(1, size1 + 1):
                node_x_idx = x + offset1 - 1
                for y in range(1, size2 + 1):
                    node_y_idx = y + offset2 - 1
                    if l1[node_x_idx] == l1[i] and l2[node_y_idx] == l2[j]:
                        fd[x][y] = min(
                            fd[x - 1][y] + 1,
                            fd[x][y - 1] + 1,
                            fd[x - 1][y - 1] + cost(nodes1[node_x_idx], nodes2[node_y_idx]),
                        )
                        td[node_x_idx][node_y_idx] = fd[x][y]
                    else:
                        x_prime = l1[node_x_idx] - offset1
                        y_prime = l2[node_y_idx] - offset2
                        fd[x][y] = min(
                            fd[x - 1][y] + 1,
                            fd[x][y - 1] + 1,
                            fd[x_prime][y_prime] + td[node_x_idx][node_y_idx],
                        )

    return td[n1 - 1][n2 - 1]
