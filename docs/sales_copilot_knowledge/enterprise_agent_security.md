# Enterprise Agent: deployment and security

Our Enterprise Agent combines RAG retrieval, tool calling and governed actions. Standard deployments are suitable for teams that use managed infrastructure. Enterprise deployments can run in a customer VPC or private infrastructure so that application traffic, document indexes and model integrations follow the customer network boundary.

For regulated buyers, discuss SSO/RBAC, source-level permissions, audit records, encryption in transit and at rest, data retention, network egress controls and an approved model-provider policy. A private deployment does not remove the need for access control or retrieval-quality evaluation.

RAG retrieves relevant approved knowledge before answering. An Agent can then use restricted tools, such as CRM lookup or ticket creation, with typed arguments. It must not receive unrestricted database access.
