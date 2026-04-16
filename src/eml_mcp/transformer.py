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
import torch
import torch.nn as nn
from torch import Tensor
from eml_mcp.trees import EMLNode, NodeType
from eml_mcp.simplifier import simplify_tree


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
        learnable: bool = False
    ):
        """Initialize the compiled FFN.
        
        Args:
            trees: One or more symbolic EMLNode trees to compile.
            variable_names: Names of input variables (defines input vector order).
            eps: Stability epsilon for log.
            complex_mode: If True, uses complex128 tensors and safe complex logs.
            learnable: If True, weights can be fine-tuned via delta parameters.
        """
        super().__init__()
        self.variable_names = variable_names
        self.eps = eps
        self.complex_mode = complex_mode
        self.learnable = learnable
        self.dtype = torch.complex128 if complex_mode else torch.float64
        
        if isinstance(trees, EMLNode):
            self.single_head_mode = True
            trees = [trees]
        else:
            self.single_head_mode = False
        self.tree_list = trees
        
        # 1. Linearize trees into unique sub-expressions (DAG conversion)
        self.unique_nodes = {} # expr -> {index, depth, node}
        self.leaves = []       # list of (index, type, value/name)
        self.internal_nodes = [] # list of (index, depth, left_idx, right_idx)
        
        # Apply symbolic simplification before linearization to unify redudant forms
        trees = [simplify_tree(t) for t in trees]
        
        self.root_indices_list = [self._linearize(t) for t in trees]
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
                num_nodes=self.num_nodes
            )
            self.stages.append(stage)

    def _linearize(self, node: EMLNode) -> int:
        """Linearize the tree into unique sub-expressions."""
        expr = node.to_expression()
        if expr in self.unique_nodes:
            return self.unique_nodes[expr]["index"]
        
        idx = len(self.unique_nodes)
        
        if node.node_type == NodeType.EML:
            left_idx = self._linearize(node.left)
            right_idx = self._linearize(node.right)
            depth = 1 + max(self.unique_nodes[node.left.to_expression()]["depth"],
                           self.unique_nodes[node.right.to_expression()]["depth"])
            self.unique_nodes[expr] = {
                "index": idx, 
                "depth": depth, 
                "node": node,
                "left_idx": left_idx,
                "right_idx": right_idx
            }
        else:
            # Leaf node
            self.unique_nodes[expr] = {"index": idx, "depth": 0, "node": node}
            if node.node_type == NodeType.VAR:
                self.leaves.append({"index": idx, "type": "var", "name": node.var_name})
            else:
                self.leaves.append({"index": idx, "type": "const", "value": node.value})
                
        return idx

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

    def forward(self, x: Tensor) -> Tensor:
        """Forward pass.
        
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
        num_nodes: int = 0
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
        if self.complex_mode:
            exp_l = torch.exp(L)
            r_mag = R.abs().clamp(min=self.eps)
            ln_r = torch.complex(torch.log(r_mag), torch.atan2(R.imag, R.real))
            V = exp_l - ln_r
        else:
            exp_l = torch.exp(L)
            ln_r = torch.log(torch.relu(R) + self.eps)
            V = exp_l - ln_r
            
        # 3. Update tape
        # We need a new tape to stay differentiable and not do in-place modification
        # if using autograd (though tape update is usually fine in some contexts).
        # We use scatter_ to update the slots for this stage.
        new_tape = tape.clone()
        new_tape[..., self.out_indices] = V
        return new_tape
