---
argument-hint: [spec-file-under-spec/] [phase-name]
description: "Architecture-first planning for a specific spec phase. Define files, symbols, and code-level interfaces first, then derive swim lanes for parallel agents."
---

# Plan Implementation For a Spec Phase (Architecture-First, Code-Boundary Swim Lanes)


Inputs:
- `$1` = spec file path relative to `spec/` (e.g., `MASTER_ROADMAP.md`, `api/ocr-pipeline.md`)
- `$2` = phase name or identifier within that spec (e.g., `Phase 2 – Ingestion Service`)

The goal is to design the **best architecture first**, then define swim lanes that fit that architecture. Do **not** alter the design to accommodate swim lanes.

---

## 0. Load & Scope

1. Read the spec file:
   - `@spec/$1`
2. Find the phase whose heading/label best matches `"$2"`.
   - Treat this phase as the primary scope.
   - Consider other phases only when explicitly referenced as dependencies.

---

## A. Architectural Baseline & Component Catalog (For Phase `$2`)

From the requirements of phase `$2`, define the **post-implementation component catalog**:

1. **Files**
   - Paths to be **added**, **modified**, or **removed**.
   - Reuse existing files when it makes architectural sense.

2. **Classes / Types**
   - Names, paths, visibility.
   - Mark each as **new** or **modified**.

3. **Functions / Methods**
   - Names, paths, signatures:
     - Parameters (names, types, optionality).
     - Return type.
     - Error behavior.

4. **Data Structures**
   - DTOs, event payloads, schemas, enums, config.
   - Fields + types, required vs optional, invariants, versioning.

At this stage, do not assign swim lanes. Focus entirely on optimal phase-level architecture.

---

## B. Code-Level Interface Contracts (Freeze Before Lane Work)

Define interfaces that span module or service boundaries for phase `$2`:

- **Types of interfaces**:
  - HTTP/GraphQL/RPC endpoints (routes + handler symbols).
  - Public library APIs (exported functions/methods).
  - Events/queues/topics with payload schemas.
  - DB queries/contracts and schema changes.

For each interface:

- Specify:
  - Defining file(s) and symbol names.
  - Input/output shapes (types, fields).
  - Error behavior, including failure modes and retry semantics.
  - Invariants and idempotency guarantees where relevant.

- Mark:
  - **Owning component** (later: owning swim lane).
  - Expected **consumers**.

Define an **interface freeze gate** for phase `$2` (`IF-0-$2`):

- Consumers must not start implementation work that depends on an interface until it is defined and stable enough for them to work against.

---

## C. Exhaustive Change List (Scoped to Phase `$2`)

Based on A and B:

- Enumerate every file/class/function/data structure that changes in phase `$2` as:
  - **A**
