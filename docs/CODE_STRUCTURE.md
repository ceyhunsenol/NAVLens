# NAVLens Code Structure Rules

This document complements the mandatory architecture contract. Architecture
controls which layer owns a responsibility; these rules prevent a correctly
placed layer from becoming a monolith.

The words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## General cohesion rules

- A file, module, class, function, or crate MUST have one reason to change.
- Code is grouped by cohesive capability, not because it uses the same language
  or framework.
- A module MUST expose a small intentional public API and keep implementation
  details private.
- Unrelated behavior MUST NOT be added to an existing type merely because that
  type is already available at the call site.
- Boolean switches that select unrelated behavior usually indicate that the
  function or type must be split.
- Names such as `Manager`, `Processor`, `Handler`, `Helper`, `Utils`, `Common`,
  and `Base` require a specific architectural meaning. They MUST NOT be used to
  hide mixed responsibilities.
- Regions, comment headings, and long comments MUST NOT be used as substitutes
  for extracting cohesive modules.

## Size guardrails

Size is a warning signal, not the only design criterion. Generated code,
declarative lookup tables, fixtures, and test vectors MAY exceed these limits.
All other exceptions require a written justification in the pull request.

| Construct | Review trigger | Expected response |
| --- | ---: | --- |
| Rust production file | 300 lines | Extract cohesive submodules |
| Rust function | 40 lines | Extract named domain/application operations |
| Rust public type implementation | 200 lines | Split responsibilities or collaborators |
| Python production module | 300 lines | Split by capability |
| Python class | 150 lines | Prefer composition and smaller collaborators |
| Python function/method | 40 lines | Extract pure, named operations |
| TypeScript production module | 300 lines | Split UI, state, data access, and mapping |
| Function parameters | 5 parameters | Introduce a meaningful input/command type |
| Nesting depth | 3 levels | Use early returns or extracted operations |
| Cyclomatic complexity | 10 | Split branches into explicit policies/strategies |

Tests SHOULD also remain focused. A large test module should be split by
behavior, but readability is more important than mechanically meeting a line
count.

## Rust module rules

### Crate roots

`lib.rs` and `main.rs` are composition and export surfaces.

- `lib.rs` SHOULD contain module declarations, selected re-exports, and crate
  documentation only.
- `main.rs` SHOULD parse process-level input, build dependencies, invoke one
  application entry point, and map the final result to an exit code.
- Neither file may accumulate domain calculations or use-case implementations.

Preferred structure:

```text
src/
├── lib.rs
├── return_value.rs
├── portfolio/
│   ├── mod.rs
│   ├── component.rs
│   ├── estimate.rs
│   └── error.rs
└── prediction/
    ├── mod.rs
    ├── interval.rs
    └── confidence.rs
```

### Modules and types

- A public domain concept SHOULD have its own file.
- Small inseparable value types MAY share a file when they change together.
- `mod.rs` SHOULD declare/re-export modules and MUST NOT become a second giant
  implementation file.
- Fields are private by default. Construction occurs through validated
  constructors when invariants exist.
- Trait definitions live with the consumer that needs the abstraction, not
  automatically with the implementation.
- Implementations are split by responsibility; a single `impl` block MUST NOT
  become a catalogue of unrelated convenience methods.
- Extension traits MUST represent a coherent capability and MUST NOT serve as a
  dumping ground.

### Dependencies

- `pub` and `pub(crate)` are used deliberately; internal details remain private.
- Domain crates MUST NOT expose framework or dependency-specific types in their
  public APIs without an approved architectural decision.
- Cross-crate access MUST use public contracts, never duplicated internal
  structures.
- Features MUST NOT silently change financial semantics.

## Python structure rules

Preferred feature structure:

```text
navlens/
├── sources/
│   └── tefas/
│       ├── client.py
│       ├── parser.py
│       ├── records.py
│       └── errors.py
├── datasets/
├── features/
├── estimators/
├── training/
├── evaluation/
└── visualization/
```

- Python packages are named after capabilities, not technical leftovers.
- A class MUST represent one stable concept with one responsibility.
- Prefer pure functions for transformations and calculations without identity
  or lifecycle.
- Prefer composition over inheritance. Inheritance requires a real substitutable
  relationship, not merely code reuse.
- Abstract base classes and protocols are introduced at a real boundary, not in
  anticipation of hypothetical implementations.
- Dataclasses/Pydantic records, clients, parsers, trainers, and estimators MUST
  remain separate.
- A provider client performs transport; a parser converts provider payloads; a
  normalizer maps parsed records to the shared contract. One class MUST NOT own
  all three responsibilities.
- Training code MUST NOT fetch live data implicitly. Datasets are explicit,
  versioned inputs.
- Import-time work, global mutable state, and hidden singleton clients are
  forbidden.
- Notebook modules MUST NOT be imported by production code.

## TypeScript structure rules

- Components render and handle interaction; they do not call databases,
  implement financial rules, or parse provider payloads.
- API clients, DTO mapping, state, and presentation components remain separate.
- Hooks encapsulate one cohesive behavior and MUST NOT become alternate service
  containers.
- Shared components contain reusable presentation, not fund-specific business
  rules.
- Server/client boundaries are explicit. Secrets and provider credentials MUST
  never enter client bundles.

## Separation inside a feature

Even within one feature, transport, orchestration, rules, and storage stay
separate:

```text
HTTP DTO
   │ mapping
   ▼
Application command/use case
   │ calls
   ▼
Domain operation ◄── Repository port
                         ▲
                         │ implements
                   Database adapter
```

Sharing a feature name does not permit one part to absorb another part's work.

## When to split code

Split immediately when at least one condition is true:

- different parts change for different reasons;
- tests require unrelated setup;
- a type depends on both domain and infrastructure concerns;
- private fields form independent groups used by different methods;
- a method name needs `and` to describe its behavior;
- adding a provider, estimator, or output format requires editing unrelated
  implementations;
- a file exceeds a guardrail without being declarative or generated.

Do not split merely to create one-line forwarding files. A useful module owns a
cohesive concept and improves dependency visibility.

## Duplication and extraction

- A domain rule, formula, validation, metric, or mapping contract has one
  canonical implementation.
- Cross-language callers use bindings or serialized outputs; they MUST NOT copy
  financial algorithms into another language.
- Before implementing behavior, search the knowledge graph for an existing
  owner and related call paths.
- Copy-paste followed by small edits is forbidden for production behavior.
- Similar-looking code is not automatically the same abstraction. Do not create
  generic `utils`, `common`, or base classes merely to remove a few repeated
  lines.
- Extract code when the repeated behavior has the same meaning, invariants, and
  reason to change. Put it in the innermost layer that legitimately owns it.
- Two independent concepts MAY remain structurally similar when combining them
  would couple unrelated responsibilities.
- Tests MAY repeat small setup when extraction would hide intent. Shared test
  builders and fixtures must remain test-only.
- A new dependency or helper must not provide an alternate path around the
  canonical domain operation.

When duplication is discovered, first identify ownership, then migrate callers,
then remove the duplicate. Do not leave both implementations active.

## Documentation alongside code

- Public types and functions require Rustdoc, Python docstrings, or TypeScript
  API documentation that explains units, invariants, and errors.
- A behavior change updates its focused document in the same pull request.
- A boundary or dependency-direction change requires an ADR.
- README remains a concise entry point; detailed behavior belongs under `docs/`.
- Documentation MUST distinguish implemented guarantees from planned behavior.
- Planned behavior MUST NOT be presented as an available capability.
- Open decisions and non-goals SHOULD be identified when their omission could
  otherwise be mistaken for an implementation promise.
- Status headings are used only where they improve clarity; documents MUST NOT
  add empty or irrelevant sections to satisfy a template.
- Examples and commands in documentation are treated as testable interfaces and
  must be kept current.
- Comments explain why a decision exists; they do not narrate obvious code.

## Enforcement

- Reviewers treat guardrail violations as design feedback, not cosmetic issues.
- Rust formatting, tests, and Clippy run with warnings denied.
- Python will use Ruff, type checking, tests, and configured complexity limits.
- TypeScript will use ESLint, TypeScript strict mode, formatting, and tests.
- CI MUST run the checks for every affected workspace.
- Architecture-specific checks SHOULD be automated when practical; an automated
  check does not replace responsibility review.
