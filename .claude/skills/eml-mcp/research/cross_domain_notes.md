# Cross-domain notes

This skill's content focuses on the EML server operationally. The
conceptual / theoretical connections to other domains live in the main
project docs, which this file points at.

## See `docs/cross_domain_exploration.md`

The "Minimal Generative Architecture" (MGA) pattern:

| Domain               | Primitive      | Generates                          |
| -------------------- | -------------- | ---------------------------------- |
| Boolean logic        | NAND gate      | All logic circuits                 |
| Continuous math      | EML operator   | All elementary functions           |
| Evolutionary biology | 4 gene actions | Emergent morphology (OpenPraparat) |

The shared structural pattern: **minimal primitives + recursion +
boundary constraints → unbounded complexity**. The EML server
demonstrates this for continuous math; the doc proposes it's a broader
principle.

## Related MCP servers on the same machine

- **hybrid-ai-mcp** — Boolean-domain companion. McCulloch-Pitts neurons
  + standard logic gates. Genuinely pairs with EML: EML computes
  continuous features, MCP neurons make auditable binary decisions on
  thresholded flags. Combining them gives a two-layer
  "Sheffer-operator" pipeline (continuous Sheffer → discrete Sheffer).
- **mcp-logic** — Prover9-backed automated reasoning. Used in
  `docs/cross_domain_exploration.md` to formally prove properties of
  EML-derived arithmetic (e.g. anti-commutativity of `subtract`).

Neither is a dependency of this server, but reaching for them when a
question spans domains is often cheaper than extending this one.

## Transformer-architecture speculation

`docs/eml_transformer_architecture.md` contains older notes about
using the master tree as a transformer-like substrate (attention over
EML subtree positions). Status: speculative, not implemented, not a
current priority. Read only if the user asks about it.

## What's NOT in this repo but is relevant

- Odrzywołek's reference package (`VA00/SymbolicRegressionPackage`) —
  the original EML toolkit. Compare when unsure whether our engine
  differs from the paper's algorithms.
- Schanuel's conjecture — the backing theoretical justification for
  using transcendental test points as a verification oracle. Not
  proved, but widely accepted; if broken, our `eml_verify` is a
  probabilistic rather than certain check.
- The E-graph / equality saturation literature — We have successfully
  replaced our ad-hoc simplifier with a proper e-graph-based
  rewriter. The current simplifier uses equality saturation with topological
  matching and Bellman-Ford extraction, proving more identities while
  retaining robust performance.
