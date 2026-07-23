# Decision 0145: bounded candidate portfolios precede portion optimization

## Status

Accepted in NSO06.

## Decision

Candidate selection builds deterministic top-K pools for each required meal-grammar role group and
then ranks complete combinations. It does not assign a food to a single exclusive category and it
does not hand the first greedy match directly to the portion solver.

The portfolio is deliberately bounded by candidates per group and total combinations. Hard
exclusions and incompatible food forms are applied before ranking; meal affinity, confidence and
explicit preferences affect ordering without becoming invented nutritional facts.

## Consequences

- Multiple coherent compositions can reach the numerical optimizer.
- A multi-role food is eligible for multiple pools but cannot fill two required components alone.
- Insufficient capability coverage is explicit in diagnostics.
- Candidate growth remains predictable before the CP-SAT model introduced in NSO07.
