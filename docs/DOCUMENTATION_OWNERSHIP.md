# Documentation ownership

`nexstream-deploy/docs/` is the single canonical source for cross-service architecture,
requirements, C4 views, reliability, operations, security boundaries, scaling, and roadmap.
Service repositories contain only service-local build/process/status documents and relevant sprint
guidance. Wire schemas and compatibility details are canonical in `nexstream-contracts`.

The original `nexstream-starter` remains an immutable input blueprint and is not a second active
architecture source. Distributed Sprint 01 material now lives in `nexstream-contracts/docs`, and
its executed test catalog/results live in `nexstream-contracts/tests`.

| Starter content | Active owner |
|---|---|
| Architecture, ADRs, runbook, security, benchmark, roadmap | `nexstream-deploy/docs/` |
| Sprint 01 contract guidance and vectors | `nexstream-contracts/` |
| Service behavior/build/test evidence | corresponding service repository |
| Portfolio overview/status/reporting | `nexstream-deploy/` |

No cross-repository symlinks are used.
