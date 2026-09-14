# 云桥金融安全与合规要求（Security Review）

## 强制要求
1. 禁止 SaaS，必须部署在客户 VPC。
2. 所有审计日志保留至少 180 天。
3. 必须支持 SAML SSO。
4. 业务数据不得跨境。
5. 正式上线必须接入客户 HSM（Hardware Security Module）。
6. 安全团队对上线具有否决权。

## 时间要求
若 HSM 集成能力在 2026 Q4 无法达到 GA，则项目将推迟到 2027。
