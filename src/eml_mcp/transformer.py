"""
EML-Transformer Prototype.

Maps discrete EML formula trees into structural PyTorch layers (FFNs).
This module implements the "L-1 Compiler" pattern, translating symbolic
EML identities into analytical neural network weights.

This version uses vectorized layer-wise unrolling for efficiency and
supports hybrid learnable weights.
"""

from __future__ import annotations

from typing import Any
import json
import torch
import torch.nn as nn
from torch import Tensor
from eml_mcp.trees import EMLNode, NodeType
from eml_mcp.simplifier import simplify_tree
from eml_mcp.database import EMLFormulaDB


class EMLCompiledFFN(nn.Module):
    """A PyTorch module compiled from a discrete EML tree.

    This module unrolls an EMLNode tree into a vectorized tape.
    Each unique subtree is assigned a slot in the tape.
    Computational stages are executed depth-by-depth.
    """

    def __init__(
        self,
        trees: EMLNode | list[EMLNode],
        variable_names: list[str],
        eps: float = 1e-12,
        complex_mode: bool = False,
        learnable: bool = False,
        db: EMLFormulaDB | None = None,
        compile_model: bool = True,
    ):
        """Initialize the compiled FFN.

        Args:
            trees: One or more symbolic EMLNode trees to compile.
            variable_names: Names of input variables (defines input vector order).
            eps: Stability epsilon for log.
            complex_mode: If True, uses complex128 tensors and safe complex logs.
            learnable: If True, weights can be fine-tuned via delta parameters.
            db: Optional database to resolve CALL nodes.
            compile_model: Whether to use torch.compile() for optimization.
        """
        super().__init__()
        self.variable_names = variable_names
        self.eps = eps
        self.complex_mode = complex_mode
        self.learnable = learnable
        self.db = db
        self.compile_model = compile_model
        # Use complex128 for complex mode to maintain exact precision
        self.dtype = torch.complex128 if complex_mode else torch.float64

        if isinstance(trees, EMLNode):
            self.single_head_mode = True
            trees = [trees]
        else:
            self.single_head_mode = False
        self.tree_list = trees

        # 1. Expand CALL nodes and linearize trees into unique sub-expressions (DAG conversion)
        self.unique_nodes = {}  # expr -> {index, depth, node}
        self.leaves = []  # list of (index, type, value/name)
        self.internal_nodes = []  # list of (index, depth, left_idx, right_idx)

        # Expand and simplify
        expanded_trees = [self._expand_calls(t) for t in self.tree_list]
        simplified_trees = [simplify_tree(t) for t in expanded_trees]

        self.root_indices_list = [self._linearize(t) for t in simplified_trees]
        self.register_buffer("root_indices", torch.tensor(self.root_indices_list, dtype=torch.long))

        self.num_nodes = len(self.unique_nodes)
        self.node_to_idx = {expr: data["index"] for expr, data in self.unique_nodes.items()}

        # 2. Build constants buffer
        self._setup_constants()

        # 3. Create computational stages
        # Group internal nodes by depth
        depth_groups = {}
        for node_data in self.unique_nodes.values():
            if node_data["node"].node_type == NodeType.EML:
                d = node_data["depth"]
                if d not in depth_groups:
                    depth_groups[d] = []
                depth_groups[d].append(node_data)

        self.stages = nn.ModuleList()
        for d in sorted(depth_groups.keys()):
            nodes = depth_groups[d]
            stage = EMLStage(
                nodes=nodes,
                node_to_idx=self.node_to_idx,
                eps=self.eps,
                complex_mode=self.complex_mode,
                learnable=self.learnable,
                dtype=self.dtype,
                num_nodes=self.num_nodes,
            )
            self.stages.append(stage)

    def _linearize(self, node: EMLNode) -> int:
        """Linearize the tree into unique sub-expressions."""
        expr = node.to_expression()
        if expr in self.unique_nodes:
            return self.unique_nodes[expr]["index"]

        if node.node_type == NodeType.EML:
            left_idx = self._linearize(node.left)
            right_idx = self._linearize(node.right)
            idx = len(self.unique_nodes)
            depth = 1 + max(
                self.unique_nodes[node.left.to_expression()]["depth"],
                self.unique_nodes[node.right.to_expression()]["depth"],
            )
            self.unique_nodes[expr] = {
                "index": idx,
                "depth": depth,
                "node": node,
                "left_idx": left_idx,
                "right_idx": right_idx,
            }
        else:
            # Leaf node
            idx = len(self.unique_nodes)
            self.unique_nodes[expr] = {"index": idx, "depth": 0, "node": node}
            if node.node_type == NodeType.VAR:
                self.leaves.append({"index": idx, "type": "var", "name": node.var_name})
            else:
                self.leaves.append({"index": idx, "type": "const", "value": node.value})

        return idx

    def _expand_calls(self, node: EMLNode) -> EMLNode:
        """Recursively expand CALL nodes by stitching in trees from the database."""
        if node.node_type != NodeType.CALL:
            if node.node_type == NodeType.EML:
                return EMLNode(
                    node_type=NodeType.EML,
                    left=self._expand_calls(node.left),
                    right=self._expand_calls(node.right),
                )
            return node.copy()

        # Resolve CALL
        if not self.db:
            raise ValueError(
                f"Cannot expand CALL node '{node.func_name}' because no DB was provided."
            )

        formula_data = self.db.get_formula(node.func_name)
        if not formula_data:
            raise ValueError(f"Formula '{node.func_name}' not found in database.")

        # 1. Restore the template tree from JSON
        template_tree = EMLNode.from_dict(json.loads(formula_data["tree_json"]))

        # 2. Recursively expand the arguments provided to this CALL
        expanded_args = {k: self._expand_calls(v) for k, v in node.args.items()}

        # 3. Substitute expanded arguments into the template
        expanded_sub_tree = template_tree.substitute(expanded_args)

        # 4. Recursively expand any CALL nodes that might exist in the substituted template
        # (Allows templates themselves to contain CALL nodes)
        return self._expand_calls(expanded_sub_tree)

    def _setup_constants(self):
        """Setup constants buffer and variable mapping."""
        # Map variables to their indices in the input tensor
        self.var_to_input_idx = {name: i for i, name in enumerate(self.variable_names)}

        # Constant values to be pre-filled into the tape
        const_indices = []
        const_values = []
        for leaf in self.leaves:
            if leaf["type"] == "const":
                val = leaf["value"]
                if not self.complex_mode and isinstance(val, complex):
                    val = val.real
                const_indices.append(leaf["index"])
                const_values.append(val)

        self.register_buffer("const_indices", torch.tensor(const_indices, dtype=torch.long))
        self.register_buffer("const_values", torch.tensor(const_values, dtype=self.dtype))

        # Variable mapping: which tape index corresponds to which input variable
        var_indices = []
        var_input_indices = []
        for leaf in self.leaves:
            if leaf["type"] == "var":
                var_indices.append(leaf["index"])
                var_input_indices.append(self.var_to_input_idx[leaf["name"]])

        self.register_buffer("var_indices", torch.tensor(var_indices, dtype=torch.long))
        self.register_buffer("var_input_indices", torch.tensor(var_input_indices, dtype=torch.long))

        # Initial forward pass to warm up or compile
        if hasattr(torch, "compile") and getattr(self, "compile_model", False):
            try:
                # We compile the main forward logic
                # 'reduce-overhead' is good for small models like ours
                self._compiled_run = torch.compile(self._run_forward, mode="reduce-overhead")
            except Exception:
                self._compiled_run = self._run_forward
        else:
            self._compiled_run = self._run_forward

    def forward(self, x: Tensor) -> Tensor:
        """Forward pass dispatch."""
        return self._compiled_run(x)

    def _run_forward(self, x: Tensor) -> Tensor:
        """Actual forward pass logic.

        Args:
            x: Input tensor of shape (..., len(variable_names)).
        """
        # 1. Initialize tape
        if x.dtype != self.dtype:
            x = x.to(self.dtype)

        batch_shape = x.shape[:-1]
        tape_shape = batch_shape + (self.num_nodes,)
        tape = torch.zeros(tape_shape, dtype=self.dtype, device=x.device)

        # 2. Fill leaves
        # Fill constants: use broadcasting
        tape[..., self.const_indices] = self.const_values
        # Fill variables
        tape[..., self.var_indices] = x[..., self.var_input_indices]

        # 3. Execute computational stages
        for stage in self.stages:
            tape = stage(tape)

        # 4. Return head outputs
        out = tape[..., self.root_indices]
        # If single head, we still keep it consistent as (..., 1) or squeeze?
        # Let's stay consistent with (..., num_heads) if it's a list,
        # but if it was originally a single tree, we can squeeze for backward comp.
        if self.single_head_mode:
            return out.squeeze(-1)
        return out

    def network_to_etree(self) -> list[EMLNode]:
        """Convert the current active PyTorch matrix mapping back into symbolic EMLNodes."""
        def build_node(idx: int) -> EMLNode:
            if idx in self.const_indices:
                idx_pos = (self.const_indices == idx).nonzero(as_tuple=True)[0].item()
                val = self.const_values[idx_pos].item()
                if isinstance(val, complex):
                    if val.imag == 0: val = val.real
                node = EMLNode(NodeType.CONST, value=val)
                node._tape_idx = idx
                return node
            elif idx in self.var_indices:
                idx_pos = (self.var_indices == idx).nonzero(as_tuple=True)[0].item()
                input_idx = self.var_input_indices[idx_pos].item()
                node = EMLNode(NodeType.VAR, var_name=self.variable_names[input_idx])
                node._tape_idx = idx
                return node
            else:
                for stage in self.stages:
                    if idx in stage.out_indices:
                        idx_pos = (stage.out_indices == idx).nonzero(as_tuple=True)[0].item()
                        if self.learnable:
                            We = stage.fixed_W_e[idx_pos] + stage.delta_W_e[idx_pos]
                            Wl = stage.fixed_W_l[idx_pos] + stage.delta_W_l[idx_pos]
                            left_idx = We.abs().argmax().item()
                            right_idx = Wl.abs().argmax().item()
                        else:
                            left_idx = stage.left_indices[idx_pos].item()
                            right_idx = stage.right_indices[idx_pos].item()
                        node = EMLNode(NodeType.EML, left=build_node(left_idx), right=build_node(right_idx))
                        node._tape_idx = idx
                        return node
                raise ValueError(f"Index {idx} not found in nodes.")

        return [build_node(r.item()) for r in self.root_indices]

    def prune_redundant_features(self, etrees: list[EMLNode]) -> list[int]:
        """Runs the E-Graph simplifier and returns the optimal tape indices to drop."""
        simplified = [simplify_tree(t) for t in etrees]
        kept_indices = set()
        
        def trace_required(node: EMLNode):
            expr = node.to_expression()
            if expr in self.node_to_idx:
                kept_indices.add(self.node_to_idx[expr])
            if node.node_type == NodeType.EML:
                trace_required(node.left)
                trace_required(node.right)
                
        for t in simplified:
            trace_required(t)
            
        all_indices = set(range(self.num_nodes))
        return list(all_indices - kept_indices)

    def apply_symbolic_pruning(self):
        """Zero-out weights connected to heads strictly classified outside the optimal topological selection."""
        if not self.learnable:
            return
            
        etrees = self.network_to_etree()
        simplified = [simplify_tree(t) for t in etrees]
        kept_indices = set()
        
        def rewire(node: EMLNode, orig_tape_idx: int):
            expr = node.to_expression()
            if expr in self.node_to_idx:
                target_idx = self.node_to_idx[expr]
                kept_indices.add(target_idx)
                if node.node_type == NodeType.EML:
                    rewire(node.left, -1)
                    rewire(node.right, -1)
                return target_idx
            else:
                if node.node_type == NodeType.EML:
                    left_idx = rewire(node.left, -1)
                    right_idx = rewire(node.right, -1)
                    if orig_tape_idx != -1 and left_idx != -1 and right_idx != -1:
                        for stage in self.stages:
                            if orig_tape_idx in stage.out_indices:
                                idx_pos = (stage.out_indices == orig_tape_idx).nonzero(as_tuple=True)[0].item()
                                with torch.no_grad():
                                    stage.delta_W_e[idx_pos].zero_()
                                    stage.delta_W_l[idx_pos].zero_()
                                    # Snap to optimal
                                    stage.delta_W_e[idx_pos][left_idx] = 1.0 - stage.fixed_W_e[idx_pos][left_idx]
                                    stage.delta_W_l[idx_pos][right_idx] = 1.0 - stage.fixed_W_l[idx_pos][right_idx]
                                    stage.bias_e[idx_pos].zero_()
                                    stage.bias_l[idx_pos].zero_()
                        kept_indices.add(orig_tape_idx)
                        return orig_tape_idx
            return -1

        with torch.no_grad():
            for i, (orig_tree, simp_tree) in enumerate(zip(etrees, simplified)):
                r_idx = self.root_indices[i].item()
                rewire(simp_tree, r_idx)
                kept_indices.add(r_idx)
                
            for stage in self.stages:
                for i, out_idx in enumerate(stage.out_indices):
                    if out_idx.item() not in kept_indices:
                        stage.delta_W_e[i].zero_()
                        stage.delta_W_l[i].zero_()
                        stage.bias_e[i].zero_()
                        stage.bias_l[i].zero_()
                        # Counteract any fixed_W selection
                        stage.delta_W_e[i] = -stage.fixed_W_e[i]
                        stage.delta_W_l[i] = -stage.fixed_W_l[i]


class EMLStage(nn.Module):
    """A computational stage in the EML Transformer.

    Computes multiple EML nodes in parallel at the same tree depth.
    """

    def __init__(
        self,
        nodes: list[dict],
        node_to_idx: dict[str, int],
        eps: float = 1e-12,
        complex_mode: bool = False,
        learnable: bool = False,
        dtype: torch.dtype = torch.float64,
        num_nodes: int = 0,
    ):
        super().__init__()
        self.eps = eps
        self.complex_mode = complex_mode
        self.learnable = learnable
        self.num_nodes = num_nodes

        # Indices for selection and assignment
        out_indices = [n["index"] for n in nodes]
        left_indices = [n["left_idx"] for n in nodes]
        right_indices = [n["right_idx"] for n in nodes]

        self.register_buffer("out_indices", torch.tensor(out_indices, dtype=torch.long))
        self.register_buffer("left_indices", torch.tensor(left_indices, dtype=torch.long))
        self.register_buffer("right_indices", torch.tensor(right_indices, dtype=torch.long))

        # Weights for selection
        # We use a custom parameter approach for hybrid learning
        # Initially, W is a selection matrix (1 at child index, 0 elsewhere)
        if learnable:
            # W = W_fixed + Delta
            # We construct W_fixed as a sparse representation (just indices)
            # and Delta as a dense matrix that grows the search space.
            # For simplicity in Phase 8 Task 5, we'll keep it as 1-to-1 mapping
            # but allow scalar scaling/biasing.
            # (Task 3 requested W = W_fixed + Delta, we'll implement that here)

            # For each output node in this stage, we have a dense weight vector
            # of size num_nodes.
            self.delta_W_e = nn.Parameter(torch.zeros(len(nodes), num_nodes, dtype=dtype))
            self.delta_W_l = nn.Parameter(torch.zeros(len(nodes), num_nodes, dtype=dtype))
            self.bias_e = nn.Parameter(torch.zeros(len(nodes), dtype=dtype))
            self.bias_l = nn.Parameter(torch.zeros(len(nodes), dtype=dtype))

            # Sparse fixed selection (mapped to dense during forward for simplicity)
            # In a production version, we'd use sparse matrices.
            fixed_W_e = torch.zeros(len(nodes), num_nodes, dtype=dtype)
            fixed_W_l = torch.zeros(len(nodes), num_nodes, dtype=dtype)
            for i in range(len(nodes)):
                fixed_W_e[i, left_indices[i]] = 1.0
                fixed_W_l[i, right_indices[i]] = 1.0
            self.register_buffer("fixed_W_e", fixed_W_e)
            self.register_buffer("fixed_W_l", fixed_W_l)

    def forward(self, tape: Tensor) -> Tensor:
        # 1. Select inputs for this stage
        if self.learnable:
            # W = fixed + delta
            We = self.fixed_W_e + self.delta_W_e
            Wl = self.fixed_W_l + self.delta_W_l

            # Vectorized projection: (B, N) @ (N, M)^T -> (B, M)
            # PyTorch's @ (matmul) handles batching: (..., N) @ (N, K) -> (..., K)
            # We need (tape, We.T)
            L = tape @ We.T + self.bias_e
            R = tape @ Wl.T + self.bias_l
        else:
            # Efficient indexing for fixed mode
            L = tape[..., self.left_indices]
            R = tape[..., self.right_indices]

        # 2. Compute EML operation
        # Apply numerical guardrails to prevent INF/NAN
        # For float32, exp(88) is ~1e38 (overflow)
        # For float64, exp(709) is ~1e308
        if tape.dtype == torch.float32:
            max_exp = 88.0
        else:
            max_exp = 709.0

        L_safe = torch.clamp(L.real, max=max_exp)
        if L.is_complex():
            L_safe = torch.complex(L_safe, L.imag)

        # native exp
        exp_l = torch.exp(L_safe)

        if self.complex_mode:
            # Principal branch of log(z) = log(|z|) + i*arg(z)
            # torch.log already handles this correctly for complex128.
            # We just need to ensure R != 0.
            R_safe = R
            # Tiny epsilon shift for stability at singularity
            mask = R == 0
            if mask.any():
                R_safe = torch.where(mask, torch.full_like(R, self.eps), R)
            ln_r = torch.log(R_safe)
        else:
            # Real mode: log(|R| + eps)
            ln_r = torch.log(torch.abs(R) + self.eps)

        V = exp_l - ln_r

        # 3. Update tape
        # To maintain differentiability, we must use clone() if grad is enabled.
        # However, if not training, we can update in-place for performance.
        if not torch.is_grad_enabled():
            tape[..., self.out_indices] = V
            return tape

        new_tape = tape.clone()
        new_tape[..., self.out_indices] = V
        return new_tape
