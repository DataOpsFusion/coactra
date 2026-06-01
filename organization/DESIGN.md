# fleetlib.organization — v0.2 domain redesign (AD-inspired)

> Redesign from a flat SQLModel directory into an OOP **domain model**: a composable,
> multi-tenant org **tree** with real behavior — modeled on Active Directory's OU tree +
> inheritance (the *model*, not LDAP/Kerberos/the wire). Keeps the verdict boundary:
> organization owns **structure + authority + lifecycle + permissions**, NOT collaboration
> execution (that stays in `agent`/`workflow`, which *query* org for who/can).

## Locked decisions
- **Persistence:** in-memory domain tree + **explicit `save()`/`load()`** (repository
  pattern; no active-record). Mutations happen in memory; `store.save(org)` flushes.
- **Permissions:** **inherited down the tree** (AD GPO/ACL style) + per-member overrides
  + per-node `block_inheritance`.
- **DI everywhere:** the store is **injected**, never instantiated inline. A **factory**
  selects the backend. A composition root wires it.

## AD → fleetlib mapping
| AD | fleetlib.organization |
|----|----------------------|
| Domain/Forest | `tenant` (isolation boundary) |
| OU | `Organization` node (parent + children — a composite) |
| User/Computer/service | `Member` (kind: human/service/agent) — a principal |
| Security group / role | `Seat` / `Role` (grouping that perms attach to) |
| GPO/ACL inheritance | inherited tree permissions |
| Block Inheritance / Enforced | per-node `block_inheritance` + per-member override |
| Distinguished Name | org `path` (`acme/engineering/R&D/ada`) |
| Disable vs Delete | `suspend()` vs `remove()` |
| Move between OUs | `move()` (reparent) |

## Layers (the "not-junior" structure)
```
domain/      # rich OOP, the behavior — Organization, Member, Seat, Permission
  organization.py   # the composite aggregate (tree node + lifecycle + permission resolution)
  member.py, seat.py, permission.py
repository/   # persistence SPI (the swappable seam) — DI'd into load/save
  store.py          # OrgStore Protocol (WRITE + the new READ/directory APIs)
  sqlite_store.py   # default backend (sqlmodel); reads return rich rows
  neo4j_store.py    # raise-on-use stub (optional extra)
factory.py    # make_org_store(config) -> OrgStore ; composition root helpers
service.py    # load_org(tenant, *, store) -> Organization ; save_org(org, *, store)
```

## Domain API (illustrative — the real shape)
```python
from fleetlib.organization import Organization, make_org_store, load_org, save_org

store = make_org_store("sqlite://")                 # factory + DI
acme  = Organization.root(tenant="acme", name="Acme")
eng   = acme.add_child("Engineering")
rnd   = eng.add_child("R&D")                          # OU tree

ada = rnd.hire(name="ada", kind="human", role="lead",
               permissions={"deploy", "approve"})     # add principal to this OU
rnd.grant("deploy")                                   # node-level perm (inherits down)
rnd.block_inheritance = False                         # AD "block inheritance"

rnd.can(ada, "deploy")        # True  (own set ∪ inherited from ancestors)
acme.can(ada, "deploy")       # resolves through the tree
rnd.suspend(ada)              # disable (status), reversible
rnd.move(ada, to=eng)         # reparent the principal's seat
rnd.members(recursive=True)   # this OU + descendants
ada.dn                        # "acme/Engineering/R&D/ada"  (DN-style path)
rnd.manager                   # escalation target (parent-chain authority)

save_org(acme, store=store)                           # explicit persist
again = load_org("acme", store=store)                 # rebuild the tree
```

## Permission resolution (inheritance algorithm)
`can(member, action)` is True iff, walking from the member's node up to the root
(stopping where a node sets `block_inheritance=True`):
1. a **member-level override** (allow/deny) wins outright (deny beats allow), else
2. the action is in the union of the member's **role/seat** perms and any **node** perms
   granted on the path.
Multi-tenant: resolution never crosses the tenant boundary; cross-tenant access raises.

## Store: the new READ/directory APIs (the pilot's missing piece)
`OrgStore` gains (alongside existing writes): `children_of(tenant, node_id)`,
`memberships(tenant, node_id, recursive)`, `seat_of(tenant, member_id)`,
`node(tenant, id)`, `roots(tenant)`, and a bulk `directory(tenant)` join — so a consumer
(e.g. homelab-mcp's OrgCache) reads everything through the **public** API, no reaching
into `_engine`. This is what makes the homelab-mcp adapter collapse to thin.

## Boundary (unchanged, enforced)
organization answers *who exists / who reports to whom / who may do what / hire-suspend-
remove*. It does **not** message agents, run workflows, or provision infra. `hire()`
records a principal; homelab-mcp's runtime calls it, then provisions separately.

## Compatibility / tests
- Keep the existing write methods working (additive) so current behavior is preserved.
- Existing tests remain the regression oracle; add domain-model + inheritance + read-API
  tests. Then the homelab-mcp pilot adapter is rewritten to use `directory()` and shrinks.
