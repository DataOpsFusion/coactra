# Coactra Design Refinements

**Status:** current Team-first refinements.

These refinements remain the preferred interpretation of Coactra's boundaries.
They are written against the current Team-first architecture rather than the
older pre-Team-first draft.

1. **Team stays lean.**
   - Team is a registry, policy boundary, and routing surface.
   - richer org simulation remains optional and deeper than the main public API.

2. **Gateway remains primary.**
   - scoped gateway access is the normal MCP path.
   - additive local or extra mounts are secondary.

3. **Skills remain structured and curated.**
   - skill ids, descriptions, tags, and scopes are the advertised capability surface.
   - raw tool lists are never used as the discovery contract.

4. **Workflow keeps a strong internal run model.**
   - definition, run instance, approvals, checkpoints, and ledger are distinct concepts internally.

5. **Planner output stays candidate-only until promoted.**
   - reusable workflows should not self-poison through automatic promotion.

6. **Memory guardrails stay explicit.**
   - scope
   - provenance
   - injection caps
   - export/delete path
   - memory-write policy

7. **Workspace and tool safety are first-class.**
   - command execution remains heavily gated
   - tool poisoning, secret leakage, scope creep, and command injection are explicit design concerns

8. **Auth is cross-cutting, not buried.**
   - Team carries the governing policy
   - token mechanics and gateway behavior remain separate concerns
