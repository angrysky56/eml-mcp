# EML-Transformer Architecture: Formal Specification

**Status:** Architecture Draft v0.1
**Authors:** Ty (2026-04-14), with analysis contributions from Claude (Anthropic) and Gemini (Google)
**Repository:** `/home/ty/Repositories/ai_workspace/eml-mcp/`

---

## 1. Problem Statement

### 1.1 The External Tool Bottleneck

Current LLMs treat exact computation as an external dependency. Each tool call
introduces latency, breaks the execution loop, and creates a trust boundary.
The transformer-vm approach (Moran 2026, Percepta 2026) demonstrates that
deterministic computation can be compiled directly into transformer weights.

### 1.2 The EML Reduction

The EML operator $\operatorname{eml}(x,y) = \exp(x) - \ln(y)$ generates all elementary
functions from the constant 1 (Odrzywołek 2026). Combined with the transformer-vm
compilation approach, this yields a *minimal* compiled transformer: one operation
type, uniform layers, trivial compiler backend.

### 1.3 This Document

Formal specification of a transformer architecture that executes EML programs
via analytically constructed weights. Includes the critical analysis of three
routes for FFN weight construction, complexity bounds, and a falsification protocol.

---

## 2. Formal Problem Formulation

### 2.1 State Space

$$\mathcal{X} = \mathbb{C}^d$$

where $d$ is the residual stream width. Designated slots hold:
- **Input slots** $s_{\text{in}} \subseteq [1..d]$: Input variables ($x$, $y$, constant 1)
- **Working slots** $s_{\text{work}} \subseteq [1..d]$: EML intermediate values
- **Output slot** $s_{\text{out}} \in [1..d]$: Final result

The state at layer $\ell$ is $\mathbf{h}^{(\ell)} \in \mathbb{C}^d$, evolving as a register
file updated by each layer.

### 2.2 Action Space (Compiler Decisions)

$$\mathcal{A} = \mathcal{A}_{\text{schedule}} \times \mathcal{A}_{\text{alloc}} \times \mathcal{A}_{\text{route}}$$

- $\mathcal{A}_{\text{schedule}}$: Assignment of EML nodes to half-layers (bottom-up traversal)
- $\mathcal{A}_{\text{alloc}}$: Slot assignment for each live variable (register allocation)
- $\mathcal{A}_{\text{route}}$: Q/K/V weight construction for argument routing

### 2.3 Objective

$$\min_{L, d} \quad L \cdot d \quad \text{(total parameter volume)}$$

subject to:

$$\forall x_i \in \mathcal{T}: \quad |f_{\text{compiled}}(x_i) - f_{\text{ref}}(x_i)| < \epsilon$$

where $\mathcal{T}$ is the set of algebraically independent transcendental test
points (Euler-Mascheroni, Glaisher-Kinkelin, $\sqrt{2}$, $\phi$) and $\epsilon$
is the target precision.

### 2.4 Constraint Set

**Equality constraints:**
- Each EML node computes exactly $\exp(a) - \ln(b)$ for its routed inputs
- Data dependencies respected: each node executes after both children

**Inequality constraints:**
- $d \geq d_{\min}$: Width must accommodate all simultaneously live variables
- $L \geq \lceil D/2 \rceil$: Layers bounded below by tree depth $D$ (2 half-steps per layer)
- Slot reuse only for dead variables (liveness constraint)

---

## 3. Complexity Profiling and Lower Bounds

### 3.1 Tight Layer Lower Bound

**Theorem.** An EML tree of depth $D$ requires at least $\lceil D/2 \rceil$
transformer layers.

*Proof.* Each transformer layer provides exactly 2 half-steps: one attention
half-layer (routing) and one FFN half-layer (computation). Each EML node
requires at minimum one half-step for argument routing and one for evaluation.
However, the attention half-step can route arguments for the next FFN step
simultaneously, so each full layer can retire one EML node from the critical
path. The critical path length equals the tree depth $D$. But since the root
node needs both its children complete before it can execute, and each layer
retires at most 2 levels of the tree (one per half-step), the minimum is
$\lceil D/2 \rceil$. $\square$

**Concrete bounds (verified formulas from eml-mcp):**

| Function    | K  | Depth $D$ | Min Layers | Min Width $d_{\min}$ |
|-------------|---:|----------:|-----------:|---------------------:|
| exp(x)      |  3 |         1 |          1 |                    3 |
| ln(x)       |  7 |         3 |          2 |                    4 |
| 0           |  7 |         3 |          2 |                    4 |
| x − y       | 11 |         4 |          2 |                    5 |
| −x          | 17 |         7 |          4 |                    5 |
| x + y       | 27 |         9 |          5 |                    6 |
| x × y       | 41 |        10 |          5 |                    7 |

### 3.2 Width Lower Bound

$$d_{\min} = \max_{\ell} |\text{live}(\ell)| + |\text{fixed}|$$

where $\text{live}(\ell)$ is the set of EML intermediates alive at half-step
$\ell$ and $\text{fixed}$ includes input variables and the constant 1.
This is a standard register allocation problem (Chaitin 1981) — equivalent
to graph coloring on the interference graph of live ranges.

For the EML grammar $S \to 1 \mid \operatorname{eml}(S,S)$, the interference
graph has a specific structure: a binary tree where sibling nodes always
interfere (both must be live for the parent's computation). The chromatic
number of this graph gives $d_{\min}$.

---

## 4. The FFN Activation Hurdle (Critical Bottleneck)

This is the central technical question. The standard PyTorch FFN computes:

$$\text{FFN}(\mathbf{h}) = \sigma(\mathbf{h} W_1 + b_1) W_2 + b_2$$

where $\sigma$ is ReLU, GELU, or SiLU. But we need:

$$\text{EML-step}(\mathbf{h}) = \exp(\mathbf{h}[s_a]) - \ln(\mathbf{h}[s_b])$$

where $s_a$, $s_b$ are the source slots for this step's arguments.

Three routes exist. The choice determines the precision, generality,
and "vanilla-ness" of the resulting transformer.

### Route 1: Custom EML Activation (Recommended)

**Construction:** Replace the FFN block with a purpose-built EML compute unit:

```
EML_FFN(h) = h + W_out · [exp(W_exp · h) - ln(W_ln · h)]
```

where:
- $W_{\exp} \in \mathbb{R}^{1 \times d}$: sparse selector, extracts slot $s_a$
- $W_{\ln} \in \mathbb{R}^{1 \times d}$: sparse selector, extracts slot $s_b$
- $W_{\text{out}} \in \mathbb{R}^{d \times 1}$: sparse writer, targets slot $s_{\text{out}}$
- Residual connection commits the update

**Precision:** Machine epsilon ($\sim 10^{-16}$). Uses hardware exp/ln directly.

**Parameters per layer:** $3d$ (three sparse vectors). Total for depth-$D$
tree: $3d \cdot \lceil D/2 \rceil$.

**Tradeoff analysis:**
- ✓ Exact computation, machine epsilon guaranteed
- ✓ Minimal parameters — three sparse vectors per layer
- ✓ Analytically constructible — zero training, zero gradient
- ✗ Not a "vanilla" `nn.TransformerEncoderLayer`
- ✗ Requires custom module implementation

**Justification for Route 1:** The transformer is acting as a compiled machine.
The activation function choice IS the instruction set choice. Choosing
$\sigma = \text{ReLU}$ for a machine that needs to compute $\exp$ and $\ln$ is
like building a RISC processor and insisting every gate must be a NOR gate
when you already have the NAND gate designed. The EML operator IS the transistor.
Swapping it in is not a hack — it is the design decision.

### Route 2: Polynomial Approximation (Vanilla Transformer)

**Construction:** Approximate $\exp$ and $\ln$ as piecewise-linear functions
(for ReLU) or polynomial approximations (for GELU/SiLU) using the hidden
dimension $d_{ff}$ to provide sufficient basis functions.

For ReLU, any continuous function on $[a,b]$ can be approximated to within
$\epsilon$ using $O(1/\epsilon)$ ReLU units (universal approximation theorem
for ReLU networks, Cybenko 1989 / Leshno et al. 1993).

**Precision analysis:**

For $\exp(x)$ on $[-10, 10]$ with $\epsilon = 10^{-6}$:
- Taylor series degree needed: $\sim 25$ terms
- ReLU piecewise-linear segments needed: $\sim 10^6$ (exp grows exponentially)
- Hidden dimension required: $d_{ff} \geq 10^6$

For machine epsilon ($\epsilon = 10^{-16}$): $d_{ff} \geq 10^{16}$. **Infeasible.**

**Tradeoff analysis:**
- ✓ 100% vanilla `nn.TransformerEncoderLayer`
- ✓ Compatible with existing framework tooling
- ✗ Cannot achieve machine epsilon — precision bounded by $d_{ff}$
- ✗ Massive hidden dimension for reasonable precision
- ✗ Different approximation needed for each input range
- ✗ Violates the falsifiable prediction (machine epsilon)

**Verdict:** Route 2 fails the precision requirement. A vanilla ReLU FFN
cannot compute exp or ln to machine epsilon in finite width. This is not
a practical limitation — it is a fundamental expressivity bound.

### Route 3: Exploit Existing Activations (GELU/SiLU Contain exp)

**Observation:** GELU and SiLU/Swish both contain $\exp$ internally:

$$\text{SiLU}(x) = \frac{x}{1 + e^{-x}} = x \cdot \sigma(x)$$

$$\text{GELU}(x) \approx 0.5 x \left(1 + \tanh\left[\sqrt{2/\pi}(x + 0.044715 x^3)\right]\right)$$

If we can algebraically extract $\exp(x)$ from $\text{SiLU}(x)$:

$$\exp(x) = \frac{\text{SiLU}(x)}{x - \text{SiLU}(x)} \quad (x \neq 0)$$

This would allow using a "vanilla" SiLU transformer and recovering exp from the
activation's output via $W_2$. However:

**Problem 1 — Division:** Recovering $\exp$ from SiLU requires division by
$(x - \text{SiLU}(x))$, which is not a linear operation and cannot be
implemented by $W_2$ alone. A second FFN layer or attention-based routing
trick would be needed.

**Problem 2 — ln has no standard activation containing it:** Even if exp is
extractable, $\ln$ is not present in any standard activation function. We'd
need $\exp$ from FFN + some other mechanism for $\ln$.

**Problem 3 — Numerical stability:** Near $x = 0$, the division becomes $0/0$.

**Verdict:** Route 3 is theoretically interesting but practically broken.
Extracting $\exp$ from SiLU requires non-linear post-processing that a single
FFN layer cannot provide, and $\ln$ has no pathway at all.

### Route Selection: Route 1 (Custom EML Activation)

Route 1 is the only path to machine-epsilon precision. Route 2 fails on
expressivity (ReLU cannot compute transcendentals in finite width). Route 3
fails on algebraic extraction ($\ln$ has no pathway).

**This is not a limitation — it is the design insight.** The EML operator
$\exp(x) - \ln(y)$ IS the activation function. The paper's core result is
that this single function suffices for all elementary mathematics. Using it
as the activation is the natural architectural choice, just as choosing NAND
gates is the natural choice for digital logic.

---

## 5. Layer Architecture (Detailed)

Each transformer layer executes up to 2 EML nodes (one per half-step).

### 5.1 Half-Step A: Attention Routing

**Purpose:** Route source slot values to working registers for the upcoming
FFN computation. This is pure data movement — no arithmetic.

**Weight construction:**

For EML node $n$ with left child result in slot $s_a$ and right child
result in slot $s_b$, construct:

$$Q = e_{s_{\text{work}_1}}^\top \quad \text{(query: "I need the value for exp input")}$$
$$K = e_{s_a}^\top \quad \text{(key: "I hold the exp input")}$$
$$V = e_{s_a}^\top \quad \text{(value: copy the actual value)}$$

where $e_i$ is the $i$-th standard basis vector in $\mathbb{R}^d$.

For multi-head attention with $H$ heads, assign one head to route $s_a$
(the exp argument) and another to route $s_b$ (the ln argument). Remaining
heads are identity (pass-through).

**Key insight:** Attention scores must be hard (argmax), not soft (softmax).
In the compiled regime, we set the attention temperature to near-zero so
that $\text{softmax}(QK^\top / \tau)$ approaches a one-hot selector. With
analytically constructed Q/K matrices, the correct key always has the
highest score by a margin we control.

**Residual write-back:** The attention output is added to the residual stream,
placing the routed values in designated working slots.

### 5.2 Half-Step B: FFN EML Computation

**Purpose:** Compute $\operatorname{eml}(a, b) = \exp(a) - \ln(b)$ and write the
result to the target slot.

**Weight construction (Route 1):**

$$\mathbf{h}^{(\ell+1)} = \mathbf{h}^{(\ell)} + W_{\text{out}} \cdot \left[\exp(W_{\exp} \cdot \mathbf{h}^{(\ell)}) - \ln(W_{\ln} \cdot \mathbf{h}^{(\ell)})\right]$$

where:
- $W_{\exp} = e_{s_a}^\top \in \mathbb{R}^{1 \times d}$: selects slot $s_a$
- $W_{\ln} = e_{s_b}^\top \in \mathbb{R}^{1 \times d}$: selects slot $s_b$
- $W_{\text{out}} = e_{s_{\text{target}}} \in \mathbb{R}^{d \times 1}$: writes to target slot

These are all sparse one-hot vectors. The entire computation is:

1. Extract $a = \mathbf{h}[s_a]$ (one dot product)
2. Extract $b = \mathbf{h}[s_b]$ (one dot product)
3. Compute $\exp(a) - \ln(b)$ (hardware float ops)
4. Write result to $\mathbf{h}[s_{\text{target}}]$ (one outer product)

**Correctness guarantee:** Since $W_{\exp}$ and $W_{\ln}$ are exact one-hot
selectors, and $\exp$/$\ln$ use hardware float64, the per-step error is bounded
by one ULP (unit in the last place). Over $D$ steps, total error accumulates
as $O(D \cdot \text{ULP}) \approx D \times 10^{-16}$.

For multiplication ($D = 10$): max accumulated error $\leq 10 \times 10^{-16}
= 10^{-15}$, consistent with eml-mcp verification results (max error $4.44 \times 10^{-16}$).

### 5.3 Slot Lifecycle (Register Allocation)

Each variable $v$ in the EML tree has a live range $[b_v, d_v]$:
- $b_v$: the half-step at which $v$ is computed (birth)
- $d_v$: the last half-step at which $v$ is read as an argument (death)

Two variables $v_i, v_j$ **interfere** iff their live ranges overlap:
$[b_{v_i}, d_{v_i}] \cap [b_{v_j}, d_{v_j}] \neq \emptyset$.

The interference graph is constructed, and its chromatic number $\chi$ gives
the minimum required working slots. For a full binary tree of depth $D$:

$$\chi = D + 1$$

since at any level, both sibling nodes and the path from root must be
simultaneously live. Adding input slots (constant 1, variables $x$, $y$):

$$d_{\min} = D + 1 + |\text{inputs}|$$

---

## 6. Compilation Pipeline

### 6.1 Input

An `EMLNode` tree from `eml_core.py` (already verified by `eml_verify`).

### 6.2 Pass 1: Bottom-Up Scheduling

Traverse the tree bottom-up (post-order). At each internal node:

```
schedule = []
for node in postorder(tree):
    if node.type == EML:
        schedule.append({
            "node_id": id(node),
            "left_source": slot_of(node.left),
            "right_source": slot_of(node.right),
            "target": allocate_slot(node),
            "half_step": len(schedule),
        })
```

Each scheduled entry becomes one FFN half-step. Pair consecutive entries
into full layers. If the count is odd, the last layer uses only its FFN
half-step (attention half-step is identity pass-through).

### 6.3 Pass 2: Slot Allocation (Register Allocation)

**Algorithm:** Linear scan register allocation (Poletto & Sarkar 1999) over
live ranges computed from the schedule.

```
Input:  schedule S, available slots [1..d_max]
Output: slot_map: node_id → slot_index

free_slots = stack([d_max, d_max-1, ..., 1])
active = []  # sorted by death time

for entry in S:
    # Free dead variables
    expire_old(active, entry.half_step, free_slots)

    # Allocate target slot
    if free_slots is empty:
        spill()  # never needed for trees — always enough slots
    entry.target_slot = free_slots.pop()
    active.insert_sorted(entry, key=death_time)

    slot_map[entry.node_id] = entry.target_slot
```

For binary trees, spilling never occurs because the maximum simultaneous
liveness is $D + 1$, and we provision $d \geq D + 1 + |\text{inputs}|$.

### 6.4 Pass 3: Weight Construction

For each layer $\ell$ executing EML node $n$:

**Attention weights (argument routing):**
$$W_Q^{(\ell)} = \beta \cdot e_{s_{\text{work}_1}} \otimes e_{s_a} \quad \text{(head 1: route exp argument)}$$
$$W_K^{(\ell)} = e_{s_a} \otimes e_{s_a}$$
$$W_V^{(\ell)} = e_{s_a} \otimes e_{s_a}$$

with temperature scaling $\beta \gg 1$ to ensure hard attention.

Head 2 mirrors this for $s_b$ (the ln argument).

**FFN weights (EML computation):**
$$W_{\exp}^{(\ell)} = e_{s_{\text{work}_1}}^\top, \quad W_{\ln}^{(\ell)} = e_{s_{\text{work}_2}}^\top, \quad W_{\text{out}}^{(\ell)} = e_{s_{\text{target}}}$$

**Embedding:** Maps input token to slot vector:
$$E[\text{token}] = \sum_{i \in \text{inputs}} v_i \cdot e_{s_i}$$

where $v_i$ is the value to place in slot $s_i$ (e.g., constant 1, input $x$).

**Output head:** Reads the final result slot:
$$W_{\text{out}} = e_{s_{\text{result}}}^\top$$

---

## 7. Falsification Protocol

### 7.1 Primary Prediction (Machine Epsilon)

**Claim:** An EML-compiled transformer of depth $\lceil K/2 \rceil$ layers and
width $d_{\min}$ computes any elementary function of complexity $K$ to within
$D \times \text{ULP} \approx D \times 2.22 \times 10^{-16}$ of the reference
implementation, with zero training.

**Falsification test:** For each verified formula in the eml-mcp registry:

1. Build the EML tree via `eml_tree_info(formula_name)`
2. Compile to transformer weights via the pipeline in §6
3. Forward-pass the transformer on the same transcendental test points
   used by `eml_verify`
4. Compare transformer output to reference function

**Pass criterion:** $\max_i |f_{\text{transformer}}(x_i) - f_{\text{ref}}(x_i)|
< D \times 2.22 \times 10^{-16}$

**Kill criterion:** If ANY formula exceeds this bound, the weight construction
is incorrect. Debug by comparing per-layer state to the EML tree's per-node
evaluation trace (both available from eml_core).

### 7.2 Ablation: EML Uniformity Advantage

**Claim:** The EML-compiled transformer has fewer parameters and simpler
compilation than a heterogeneous-operator compiled transformer implementing
the same function.

**Test:** Compile $x \times y$ two ways:
- **EML route:** Compile via EML tree (K=41, depth 10, 5 layers)
- **Heterogeneous route:** Compile via direct multiplication using the
  transformer-vm's general framework

Compare: total parameters, compilation time, per-layer weight density (sparsity).

**Expected result:** EML route has sparser weights (all one-hot selectors)
and simpler compilation (uniform schedule), at the cost of more layers.

---

## 8. Depth-1 Proof of Concept: exp(x)

Gemini correctly identifies this as the first implementation target. If a
single-layer transformer can compute $\exp(x) = \operatorname{eml}(x, 1)$
with analytically constructed weights and zero training, the thesis is proven.

### 8.1 Specification

**EML tree:** `eml(x, 1)` — depth 1, K=3
**Layers:** 1
**Width:** $d = 3$ (slot 0: constant 1, slot 1: input $x$, slot 2: result)
**Heads:** 2 (one routes $x$ to exp-input, one routes 1 to ln-input)

### 8.2 Weight Tensors (Explicit Construction)

**Embedding** $E \in \mathbb{R}^{|\text{vocab}| \times 3}$:
$$E[\text{token}] = [1.0, \quad \text{token\_value}, \quad 0.0]$$

**Attention** (2 heads, each $\mathbb{R}^{3 \times 1}$):
- Head 1 Q: $[0, 1, 0]^\top$, K: $[0, 1, 0]^\top$, V: $[0, 1, 0]^\top$
  → Routes slot 1 ($x$) to working register for exp
- Head 2 Q: $[1, 0, 0]^\top$, K: $[1, 0, 0]^\top$, V: $[1, 0, 0]^\top$
  → Routes slot 0 (constant 1) to working register for ln

**EML FFN:**
- $W_{\exp} = [0, 1, 0]$: extracts slot 1 ($x$)
- $W_{\ln} = [1, 0, 0]$: extracts slot 0 (constant 1)
- $W_{\text{out}} = [0, 0, 1]^\top$: writes to slot 2
- Computation: $\exp(x) - \ln(1) = \exp(x) - 0 = \exp(x)$

**Output head** $W_{\text{out}} \in \mathbb{R}^{1 \times 3}$:
$$W_{\text{out}} = [0, 0, 1]$$
Reads slot 2 (the result).

### 8.3 Verification

Forward pass on test points:

| Input $x$ | Slot 0 | Slot 1 | Slot 2 (after FFN) | Expected |
|----------:|-------:|-------:|-------------------:|---------:|
| 0         | 1.0    | 0.0    | 1.0                | 1.0      |
| 1         | 1.0    | 1.0    | 2.71828...         | $e$      |
| 2         | 1.0    | 2.0    | 7.38906...         | $e^2$    |
| -1        | 1.0    | -1.0   | 0.36788...         | $1/e$    |

If all match to $< 2.22 \times 10^{-16}$, the single-layer case is proved.

---

## 9. Open Questions and Future Work

### 9.1 Attention Routing: Self-Attention vs. Cross-Attention

The transformer-vm uses self-attention for routing within a single sequence.
For EML, all values exist in the same residual stream (no cross-sequence
lookup needed). Self-attention with hard temperature suffices. But:

**Q:** Can the routing be done without attention at all? If slots are
statically assigned (they are — the compiler knows them at construction time),
the attention Q/K/V matrices are constant one-hot selectors. This degenerates
to a fixed permutation matrix, implementable as a simple linear layer
$W_{\text{route}} \in \mathbb{R}^{d \times d}$ without softmax.

If so, the attention mechanism is unnecessary for EML compilation. The
architecture reduces to: **permute → eml → permute → eml → ... → read**.
This would be even simpler than a transformer — it's a feed-forward network
with a custom activation function and skip connections.

### 9.2 Complex Arithmetic

EML requires complex intermediates (trigonometric functions, $\pi$, $i$ all
emerge via $\ln(-1)$). The architecture must use $\mathbb{C}^d$ residual
streams, not $\mathbb{R}^d$. This doubles the effective width. PyTorch
supports `torch.complex128` natively, but attention softmax on complex
scores needs care — use $\text{Re}(QK^\top)$ for score computation.

### 9.3 Integration with Learned Transformers

The ultimate goal: a hybrid model where a small block of EML-compiled layers
handles exact math while the rest does standard language processing. Two
integration patterns:

**A. Side-channel:** Language model detects "need exact computation" →
routes values to a parallel EML block → receives result → continues
generation. The EML block is frozen (compiled weights, never trained).

**B. Interleaved:** Dedicated EML layers inserted at known positions in
the language model's layer stack. During normal generation, these layers
pass through (identity). When exact computation is triggered, they activate.

Pattern A is simpler; pattern B is what Moran's article envisions as
"dual-mode" (deterministic compiled + probabilistic learned).

### 9.4 Connection to MGA Framework

This architecture instantiates the Minimal Generative Architecture pattern
at a new level. The MGA table from the synthesis page now has a concrete
implementation path for L-1 (computational substrate):

| MGA Component       | EML-Transformer Implementation          |
|---------------------|------------------------------------------|
| Minimal primitive   | EML FFN block ($\exp(a) - \ln(b)$)       |
| Recursion           | Layer stacking (each layer = one EML step)|
| Boundary constraint | Finite depth, finite width, IEEE754 range |
| Emergent domain     | All elementary functions                  |
| Compiler            | §6 pipeline: schedule → allocate → construct|

### 9.5 Connection to AlphaEvolve

The compilation pipeline in §6 produces correct but *unoptimized* EML programs
(compiler K vs. direct search K — e.g., multiply: 41 vs. 17). AlphaEvolve's
evolutionary loop could optimize the EML trees themselves: seed with the
compiler output, evolve toward shorter equivalent trees, evaluate via
`eml_verify` on the eml-mcp server. This would close the optimality gap
automatically — using LLM-guided evolution to discover optimal EML programs,
which are then compiled into optimal transformer weights.

---

## 10. Implementation Roadmap

### Phase 1: Depth-1 PoC (exp(x))

Manually construct the weight tensors from §8.2 in PyTorch. Verify against
reference on transcendental test points. If this passes, the core mechanism
is proven. **Estimated effort:** ~100 lines of PyTorch.

### Phase 2: Compiler Passes (schedule, allocate, construct)

Implement the three-pass pipeline from §6 as a new tool `eml_compile_transformer`
in the eml-mcp server. Input: any `EMLNode` tree. Output: `torch.nn.Module`
with analytically constructed weights. **Estimated effort:** ~300 lines.

### Phase 3: Full Formula Suite

Compile all 8 verified formulas. Run the falsification protocol from §7.
Produce the comparison table of compiled-transformer output vs. `eml_verify`
reference values. **This is the publishable result.**

### Phase 4: Hybrid Architecture Sketch

Design the side-channel integration (§9.3A) for a language model to delegate
exact math to the compiled EML block. This is architectural design only —
implementation requires access to a trained language model's internals.

---

## References

- Odrzywołek, A. (2026). "All elementary functions from a single operator."
  arXiv:2603.21852v2.
- Moran, S. (2026). "I Built a Tiny Computer Inside a Transformer."
  Towards Data Science. Code: github.com/sjmoran/transformer-vm
- Percepta (2026). "Constructing an LLM Computer."
  percepta.ai/blog/constructing-llm-computer
- Chaitin, G. (1981). "Register allocation and spilling via graph coloring."
  ACM SIGPLAN Notices.
- Poletto, M. & Sarkar, V. (1999). "Linear scan register allocation."
  ACM TOPLAS 21(5).
