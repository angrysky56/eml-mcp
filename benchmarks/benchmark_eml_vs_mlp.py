"""
Performance benchmark: EML-Transformer vs Standard MLP.

Compares forward-pass latency, parameter efficiency, and gradient computation time.
"""

import time
import torch
import torch.nn as nn
from eml_mcp.transformer import EMLCompiledFFN
from eml_mcp.attention import EMLSymbolicAttention
from eml_mcp.database import EMLFormulaDB
from eml_mcp.trees import EMLNode, NodeType

def count_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)

def benchmark_models():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Benchmarking on {device}")
    
    batch_size = 1024
    input_dim = 4
    num_heads = 8
    embed_dim = 16
    hidden_dim = 64
    
    db = EMLFormulaDB(":memory:")
    # Use exp, e, ln, multiply, add, subtract, negate, zero as functional heads
    head_names = ["exp", "e", "ln", "multiply", "add", "subtract", "negate", "zero"]
    # We need to map variables to x, y as used in registry
    # For now, let's just use 8 heads defined by names
    heads = []
    for name in head_names:
        # Note: some formulas expect 'y', so we map them to input variables
        # exp(x_0), ln(x_1), x_2 + x_3, etc.
        if name in ["exp", "ln", "negate"]:
            node = EMLNode(NodeType.CALL, func_name=name, args={"x": EMLNode(NodeType.VAR, var_name="x0")})
        elif name in ["multiply", "add", "subtract"]:
            node = EMLNode(NodeType.CALL, func_name=name, args={
                "x": EMLNode(NodeType.VAR, var_name="x0"),
                "y": EMLNode(NodeType.VAR, var_name="x1")
            })
        else:
            node = EMLNode(NodeType.CALL, func_name=name, args={})
        heads.append(node)

    # 1. EML Model
    eml_ffn = EMLCompiledFFN(heads, variable_names=["x0", "x1", "x2", "x3"], db=db).to(device)
    eml_attn = EMLSymbolicAttention(num_heads=len(heads), input_dim=input_dim, embed_dim=embed_dim, dtype=torch.float64).to(device)
    
    def eml_model_forward(x):
        h = eml_ffn(x)
        out, _ = eml_attn(x, h)
        return out

    # 2. MLP Model
    mlp = nn.Sequential(
        nn.Linear(input_dim, hidden_dim, dtype=torch.float64),
        nn.ReLU(),
        nn.Linear(hidden_dim, hidden_dim, dtype=torch.float64),
        nn.ReLU(),
        nn.Linear(hidden_dim, 1, dtype=torch.float64)
    ).to(device)

    # Print Parameter Counts
    eml_params = count_parameters(eml_attn) + (count_parameters(eml_ffn) if eml_ffn.learnable else 0)
    mlp_params = count_parameters(mlp)
    
    print(f"\n--- Model Complexity ---")
    print(f"EML-Transformer Params: {eml_params}")
    print(f"Standard MLP Params: {mlp_params}")
    
    # Generate Synthetic Data
    x = torch.randn(batch_size, input_dim, dtype=torch.float64, device=device)
    
    # Warmup
    for _ in range(10):
        _ = eml_model_forward(x)
        _ = mlp(x)

    # Benchmark Forward Pass
    print(f"\n--- Forward Pass Latency (Avg over 100 runs) ---")
    
    start = time.perf_counter()
    for _ in range(100):
        _ = eml_model_forward(x)
    eml_fwd_time = (time.perf_counter() - start) / 100
    print(f"EML Forward: {eml_fwd_time:.6f} s")

    start = time.perf_counter()
    for _ in range(100):
        _ = mlp(x)
    mlp_fwd_time = (time.perf_counter() - start) / 100
    print(f"MLP Forward: {mlp_fwd_time:.6f} s")

    # Benchmark Gradient Computation
    print(f"\n--- Backward Pass (Forward + Grad) Latency ---")
    
    start = time.perf_counter()
    for _ in range(100):
        out = eml_model_forward(x)
        loss = out.mean()
        loss.backward()
    eml_bwd_time = (time.perf_counter() - start) / 100
    print(f"EML Backward: {eml_bwd_time:.6f} s")

    start = time.perf_counter()
    for _ in range(100):
        out = mlp(x)
        loss = out.mean()
        loss.backward()
    mlp_bwd_time = (time.perf_counter() - start) / 100
    print(f"MLP Backward: {mlp_bwd_time:.6f} s")

    print("\n--- Summary ---")
    print(f"EML uses {mlp_params / eml_params:.1f}x fewer parameters than MLP.")
    if eml_fwd_time > mlp_fwd_time:
        print(f"EML forward pass is {eml_fwd_time / mlp_fwd_time:.1f}x slower than MLP (analytical overhead).")
    else:
        print(f"EML forward pass is {mlp_fwd_time / eml_fwd_time:.1f}x faster than MLP.")

if __name__ == "__main__":
    benchmark_models()
