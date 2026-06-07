# 后端架构设计文档

> 本文基于微信小程序“考试类 + 课程类刷题系统”的业务范围设计后端架构。系统采用微服务拆分，数据库使用 MySQL，缓存使用 Redis，题库使用 MongoDB，图片和视频使用 MinIO，所有服务和中间件部署在已有 Kubernetes 集群的 `zuoti` namespace 中。

## 1. 架构目标

- 支持微信小程序通过统一 HTTPS 入口访问后端。
- 支持注册用户和管理员授权用户访问题库。
- 支持考试类、课程类题库的维护、练习、考试、错题、收藏、成绩、趋势统计。
- 支持首页教学视频和学习推广内容管理。
- 支持题目离线缓存和缓存版本更新。
- 支持后台管理端维护用户授权、题库、章节、题目、套卷、反馈、系统配置。
- 密码、密钥、数据库连接串、对象存储密钥等敏感信息不得明文保存在仓库。

## 2. 总体架构

```mermaid
flowchart TD
  Miniapp["微信小程序"] --> Gateway["已有 Ingress Controller + 项目 Ingress\nhttps://www.njwjxy.cn:30443"]
  AdminWeb["后台管理端"] --> Gateway

  Gateway --> AuthSvc["auth-service\n认证与会话"]
  Gateway --> UserSvc["user-service\n用户与授权"]
  Gateway --> ContentSvc["content-service\n首页内容"]
  Gateway --> BankSvc["bank-service\n题库元数据"]
  Gateway --> QuestionSvc["question-service\n题目与缓存版本"]
  Gateway --> PracticeSvc["practice-service\n练习与错题收藏"]
  Gateway --> ExamSvc["exam-service\n套卷与考试"]
  Gateway --> RankingSvc["ranking-service\n奖牌与排名"]
  Gateway --> FeedbackSvc["feedback-service\n反馈"]
  Gateway --> AdminSvc["admin-service\n后台管理聚合"]

  AuthSvc --> MySQL[(MySQL)]
  UserSvc --> MySQL
  ContentSvc --> MySQL
  BankSvc --> MySQL
  PracticeSvc --> MySQL
  ExamSvc --> MySQL
  RankingSvc --> MySQL
  FeedbackSvc --> MySQL
  AdminSvc --> MySQL

  AuthSvc --> Redis[(Redis)]
  PracticeSvc --> Redis
  ExamSvc --> Redis
  RankingSvc --> Redis

  QuestionSvc --> MongoDB[(MongoDB)]
  BankSvc --> MongoDB
  PracticeSvc --> MongoDB
  ExamSvc --> MongoDB

  ContentSvc --> MinIO[(MinIO)]
  QuestionSvc --> MinIO
```

## 3. 外部访问设计

### 3.1 统一入口

小程序前端访问后端使用以下域名和端口：

```text
https://www.njwjxy.cn:30443
```

建议 API 统一使用 `/api` 前缀：

| 类型 | 示例 |
| --- | --- |
| 小程序接口 | `https://www.njwjxy.cn:30443/api/miniapp/...` |
| 后台管理接口 | `https://www.njwjxy.cn:30443/api/admin/...` |
| 文件访问代理 | `https://www.njwjxy.cn:30443/api/files/...` |

### 3.2 微信小程序配置

| 配置项 | 值 / 存储方式 |
| --- | --- |
| AppID | `wxb88840bf78c6cd4d` |
| AppSecret | 不允许写入仓库，必须通过 Kubernetes Secret、CI/CD Secret 或外部密钥系统注入 |

### 3.3 Ingress 访问职责

集群中已部署 Ingress Controller，本项目不需要重复部署 Ingress Controller。后端只需要在 `zuoti` namespace 中维护项目自己的 Ingress 资源，将外部入口路由到对应微服务或 API 网关服务。

- HTTPS 终止或转发。
- 路由小程序接口和后台管理接口。
- 统一跨域、安全头、请求体大小限制。
- 基础限流和黑名单拦截。
- 将请求转发到 `zuoti` namespace 内的微服务。

## 4. Kubernetes 部署约束

### 4.1 Namespace

所有中间件和微服务均部署在已有 Kubernetes 集群的 `zuoti` namespace：

```text
namespace: zuoti
```

### 4.2 工作负载类型

| 类型 | 建议资源 |
| --- | --- |
| 微服务 | `Deployment` + `Service` |
| MySQL | `StatefulSet` + `PersistentVolumeClaim` |
| Redis | `StatefulSet` + `PersistentVolumeClaim` |
| MongoDB | `StatefulSet` + `PersistentVolumeClaim` |
| MinIO | `StatefulSet` + `PersistentVolumeClaim` |
| Ingress 路由 | 使用已有 Ingress Controller，创建项目 Ingress 资源 |
| 配置 | `ConfigMap` |
| 密钥 | `Secret` |

### 4.3 服务命名建议

| 服务 | K8s Service 名称 |
| --- | --- |
| API 网关 / 路由入口 | `zuoti-gateway` |
| 认证服务 | `zuoti-auth-service` |
| 用户服务 | `zuoti-user-service` |
| 内容服务 | `zuoti-content-service` |
| 题库服务 | `zuoti-bank-service` |
| 题目服务 | `zuoti-question-service` |
| 练习服务 | `zuoti-practice-service` |
| 考试服务 | `zuoti-exam-service` |
| 排名服务 | `zuoti-ranking-service` |
| 反馈服务 | `zuoti-feedback-service` |
| 后台聚合服务 | `zuoti-admin-service` |
| MySQL | `zuoti-mysql` |
| Redis | `zuoti-redis` |
| MongoDB | `zuoti-mongodb` |
| MinIO | `zuoti-minio` |

## 5. 中间件设计

### 5.1 MySQL

用途：

- 用户、管理员、角色、授权关系。
- 题库、课程、章节、套卷等结构化元数据。
- 练习记录、考试记录、错题、收藏、成绩。
- 首页内容配置、反馈、奖牌、排名快照、系统配置。

特点：

- 适合事务型数据和关系查询。
- 作为用户授权和业务状态的主数据源。
- 需要定期备份。

建议库名：

```text
zuoti
```

### 5.2 Redis

用途：

- 登录态、会话 token、验证码或临时授权态。
- 小程序接口限流。
- 热门题库、首页内容、用户授权结果缓存。
- 排名榜单缓存，例如总榜、周榜。
- 考试进行中的临时答题状态。

缓存策略：

- 用户授权缓存需要设置较短 TTL，避免授权变更后长时间不生效。
- 排名榜单可定时刷新或事件触发刷新。
- 关键写操作不能只写 Redis，必须最终落库到 MySQL。

### 5.3 MongoDB

用途：

- 题干、选项、解析、题目扩展字段。
- 题目版本快照。
- 离线缓存包内容。
- 复杂题目结构的扩展预留。

说明：

- 当前只支持单选、多选、判断题，但题目正文、选项、解析适合用文档结构保存。
- MySQL 保存题目索引和归属关系，MongoDB 保存题目正文和版本内容。
- 题目发布后生成版本号，小程序据此判断离线缓存是否需要更新。

### 5.4 MinIO

用途：

- 首页教学视频。
- 推广内容图片、Banner。
- 题目图片。
- 后台上传的其他静态资源。

存储桶建议：

| Bucket | 用途 |
| --- | --- |
| `zuoti-videos` | 教学视频 |
| `zuoti-images` | 图片、Banner、题目图片 |
| `zuoti-private` | 需要鉴权访问的私有资源 |

访问策略：

- 不建议小程序直接使用 MinIO 内网地址。
- 后端可生成短期有效的签名 URL，或通过 `/api/files/...` 代理访问。
- 私有资源必须鉴权后访问。

## 6. 微服务拆分

### 6.1 auth-service

职责：

- 微信登录。
- 通过微信 `code` 换取 `openid`。
- 使用小程序 AppID `wxb88840bf78c6cd4d` 和通过 Secret 注入的 AppSecret 调用微信服务端接口。
- 生成小程序访问 token。
- 管理登录态、token 刷新和退出登录。
- 后台管理员登录。

核心身份规则：

- 微信访问小程序的唯一 `openid` 作为用户身份的其中一个主键。
- 用户表中必须保存 `openid`，并对 `openid` 建唯一索引。
- 如后续接入 unionid，可作为跨应用身份辅助字段，不能替代当前小程序 `openid` 的唯一性。

### 6.2 user-service

职责：

- 小程序用户注册和资料维护。
- 用户授权状态查询。
- 管理员给用户授权题库或课程。
- 用户奖牌和排名基础资料查询。

核心规则：

- 未注册用户不能访问题库。
- 已注册但未授权用户不能查看题库。
- 授权范围第一阶段建议精确到题库或课程。
- 授权变更后需要清理或刷新 Redis 中的用户授权缓存。

### 6.3 content-service

职责：

- 首页教学视频配置。
- 学习推广内容、Banner、公告配置。
- 推广内容跳转目标配置。
- 图片、视频上传和资源引用管理。

依赖：

- MySQL 保存内容配置。
- MinIO 保存图片和视频文件。

### 6.4 bank-service

职责：

- 考试类、课程类题库管理。
- 科目、课程、分类、章节、知识点管理。
- 题库上下架和排序。
- 题库版本管理。
- 查询用户可访问的题库列表。

依赖：

- MySQL 保存题库、课程、章节、授权范围等元数据。
- MongoDB 可保存题库版本快照。

### 6.5 question-service

职责：

- 单选、多选、判断题维护。
- 题干、选项、正确答案、解析维护。
- 题目导入。
- 题目发布版本。
- 离线缓存包生成。

依赖：

- MongoDB 保存题目正文。
- MySQL 保存题目索引、章节关系、状态、版本。
- MinIO 保存题目图片。

### 6.6 practice-service

职责：

- 章节练习、随机练习、专项练习。
- 练习作答记录。
- 错题本。
- 题目收藏。
- 错题多次答对自动移出。
- 离线作答数据同步。

依赖：

- MySQL 保存练习记录、错题、收藏。
- MongoDB 查询题目正文。
- Redis 暂存练习状态和幂等提交标记。

### 6.7 exam-service

职责：

- 套卷列表。
- 考试说明。
- 考试开始、答题、交卷。
- 考试成绩。
- 考试解析查看。

依赖：

- MySQL 保存套卷、考试记录、成绩。
- MongoDB 查询题目正文和题目版本。
- Redis 暂存考试中的答题状态和倒计时状态。

### 6.8 ranking-service

职责：

- 总榜。
- 周榜。
- 个人当前排名。
- 奖牌规则计算。
- 用户奖牌获取记录。

依赖：

- MySQL 保存奖牌规则、用户奖牌、排名快照。
- Redis 缓存排行榜。

### 6.9 feedback-service

职责：

- 小程序用户反馈提交。
- 后台反馈列表、处理状态、处理备注。

依赖：

- MySQL 保存反馈数据。

### 6.10 admin-service

职责：

- 后台管理端聚合接口。
- 管理端仪表盘。
- 用户授权、题库管理、内容管理、反馈管理等后台聚合查询。
- 管理员权限校验。

说明：

- `admin-service` 不替代具体业务服务。
- 写操作建议转发或调用对应领域服务，避免业务规则分散。

## 7. 数据分层设计

### 7.1 MySQL 核心表建议

| 表 | 用途 |
| --- | --- |
| `users` | 小程序用户，包含 `openid` |
| `admins` | 后台管理员 |
| `roles` | 管理员角色 |
| `admin_roles` | 管理员角色关系 |
| `user_authorizations` | 用户题库或课程授权 |
| `banks` | 题库 |
| `courses` | 课程 |
| `chapters` | 章节 |
| `question_indexes` | 题目索引和 MongoDB 文档引用 |
| `papers` | 套卷 |
| `paper_questions` | 套卷题目关系 |
| `practice_records` | 练习记录 |
| `practice_answers` | 练习答题明细 |
| `mistakes` | 错题本 |
| `favorites` | 题目收藏 |
| `exam_records` | 考试记录 |
| `exam_answers` | 考试答题明细 |
| `home_contents` | 首页视频、推广内容、公告 |
| `medal_rules` | 奖牌规则 |
| `user_medals` | 用户奖牌 |
| `ranking_snapshots` | 排名快照 |
| `feedbacks` | 用户反馈 |
| `system_configs` | 系统配置 |

### 7.2 MongoDB 集合建议

| Collection | 用途 |
| --- | --- |
| `questions` | 题目正文、选项、答案、解析 |
| `question_versions` | 题目版本快照 |
| `offline_packages` | 离线缓存包元数据和题目集合 |
| `bank_snapshots` | 题库发布快照 |

### 7.3 Redis Key 建议

| Key 模式 | 用途 |
| --- | --- |
| `auth:token:{token}` | 小程序登录态 |
| `auth:admin:{token}` | 后台登录态 |
| `user:authz:{userId}` | 用户授权缓存 |
| `rate:miniapp:{openid}` | 小程序接口限流 |
| `exam:session:{examRecordId}` | 考试临时状态 |
| `practice:session:{practiceId}` | 练习临时状态 |
| `ranking:total` | 总榜 |
| `ranking:weekly:{week}` | 周榜 |
| `content:home` | 首页内容缓存 |

## 8. 身份与权限设计

### 8.1 小程序用户身份

- 微信 `openid` 是小程序用户身份的关键主键之一。
- `users.openid` 必须唯一。
- 用户首次微信登录后，如数据库不存在该 `openid`，创建用户记录。
- 用户默认状态为已注册但未授权。
- 管理员授权后，用户才能访问对应题库或课程。

建议用户状态：

| 状态 | 含义 |
| --- | --- |
| `REGISTERED` | 已注册，未授权 |
| `AUTHORIZED` | 已授权 |
| `DISABLED` | 已禁用 |

### 8.2 管理员身份

- 管理员账号使用独立身份体系，不使用小程序 `openid` 作为管理员登录凭证。
- 管理员密码必须加盐哈希保存，禁止明文保存。
- 建议使用 bcrypt、argon2 或 PBKDF2。
- 管理员登录 token 存入 Redis，并设置过期时间。

### 8.3 题库授权

授权维度建议：

| 维度 | 第一阶段建议 |
| --- | --- |
| 业务类型 | 可选 |
| 题库 | 推荐 |
| 课程 | 推荐 |
| 章节 | 暂缓 |
| 套卷 | 暂缓 |

授权校验必须在后端执行：

- 查询题库列表时过滤未授权题库。
- 查询章节、题目、套卷时校验授权。
- 获取离线缓存包前校验授权。
- 授权失效后拒绝访问，并提示小程序清理对应缓存。

## 9. 接口分组建议

### 9.1 小程序接口

| 分组 | 前缀 |
| --- | --- |
| 登录 | `/api/miniapp/auth` |
| 用户 | `/api/miniapp/user` |
| 首页内容 | `/api/miniapp/content` |
| 题库 | `/api/miniapp/banks` |
| 题目 | `/api/miniapp/questions` |
| 练习 | `/api/miniapp/practice` |
| 考试 | `/api/miniapp/exams` |
| 记录 | `/api/miniapp/records` |
| 排名奖牌 | `/api/miniapp/ranking` |
| 反馈 | `/api/miniapp/feedback` |
| 文件 | `/api/miniapp/files` |

### 9.2 后台管理接口

| 分组 | 前缀 |
| --- | --- |
| 管理员登录 | `/api/admin/auth` |
| 仪表盘 | `/api/admin/dashboard` |
| 用户授权 | `/api/admin/users` |
| 题库 | `/api/admin/banks` |
| 章节 | `/api/admin/chapters` |
| 题目 | `/api/admin/questions` |
| 套卷 | `/api/admin/papers` |
| 首页内容 | `/api/admin/content` |
| 奖牌排名 | `/api/admin/gamification` |
| 数据统计 | `/api/admin/statistics` |
| 反馈 | `/api/admin/feedback` |
| 系统设置 | `/api/admin/settings` |
| 文件上传 | `/api/admin/files` |

## 10. 离线缓存设计

### 10.1 缓存包生成

- 管理员发布题库或章节后，`question-service` 生成离线缓存包版本。
- 缓存包包含用户做题需要的数据：题干、选项、答案、解析、题型、章节、版本号。
- 缓存包不包含未授权题库内容。

### 10.2 小程序拉取缓存

流程：

1. 小程序请求可缓存题库列表。
2. 后端根据 `openid` 对应用户和授权范围过滤题库。
3. 小程序选择题库或章节缓存。
4. 后端返回缓存包下载地址或分页题目数据。
5. 小程序本地保存缓存版本。

### 10.3 缓存失效

- 题库版本变化时，小程序提示更新缓存。
- 用户授权取消时，后端接口返回授权失效状态，小程序清理对应缓存。
- 缓存包建议设置服务端版本号，不依赖客户端自行判断内容变化。

## 11. 安全设计

### 11.1 密码和密钥管理

所有涉及的密码均不能明文保存在仓库上，包括但不限于：

- MySQL 用户名和密码。
- Redis 密码。
- MongoDB 用户名和密码。
- MinIO access key 和 secret key。
- 微信小程序 app secret。
- JWT 或 token 签名密钥。
- 管理员初始密码。

要求：

- 仓库中只允许保存配置模板，例如 `.env.example`。
- 微信小程序 AppID 可作为非敏感配置保存；AppSecret 不能保存到仓库。
- 真实密钥必须通过 Kubernetes `Secret`、CI/CD Secret 或外部密钥系统注入。
- 不允许将真实密钥写入 YAML、Markdown、代码、测试文件或提交记录。
- 管理员密码必须哈希后入库，禁止可逆加密和明文保存。

### 11.2 K8s Secret 建议

建议 Secret 名称：

| Secret | 内容 |
| --- | --- |
| `zuoti-mysql-secret` | MySQL 用户、密码 |
| `zuoti-redis-secret` | Redis 密码 |
| `zuoti-mongodb-secret` | MongoDB 用户、密码 |
| `zuoti-minio-secret` | MinIO access key、secret key |
| `zuoti-wechat-secret` | 微信 app secret；AppID 可放 ConfigMap |
| `zuoti-token-secret` | token 签名密钥 |
| `zuoti-admin-secret` | 管理员初始化配置 |

### 11.3 接口安全

- 小程序接口必须校验登录 token。
- 题库、题目、考试、缓存包接口必须校验用户授权。
- 后台管理接口必须校验管理员登录态和角色权限。
- 文件上传接口限制文件类型、大小和来源。
- 管理端敏感操作需要记录审计日志。
- 建议对登录、提交答案、上传文件等接口做限流。

## 12. 日志与监控

建议采集：

- 接口请求日志。
- 登录失败日志。
- 授权变更日志。
- 题库发布日志。
- 题目导入日志。
- 考试交卷失败日志。
- 离线缓存生成失败日志。
- MinIO 上传失败日志。

建议指标：

- 服务 QPS、错误率、响应时间。
- MySQL 连接数和慢查询。
- Redis 命中率和内存使用。
- MongoDB 查询耗时。
- MinIO 存储容量。
- K8s Pod CPU、内存、重启次数。

## 13. 第一阶段实施建议

第一阶段优先实现：

1. `auth-service`
2. `user-service`
3. `bank-service`
4. `question-service`
5. `practice-service`
6. `exam-service`
7. `content-service`
8. `feedback-service`
9. `admin-service`
10. MySQL、Redis、MongoDB、MinIO 基础部署
11. 基于已有 Ingress Controller 配置项目 Ingress 路由到 `https://www.njwjxy.cn:30443`
12. Kubernetes Secret 和 ConfigMap 注入

第二阶段扩展：

- `ranking-service` 独立化。
- 更复杂的奖牌规则。
- 更细粒度的授权范围。
- 统计报表和数据导出。
- 更完整的审计日志和运维告警。

## 14. 待补充设计文档

后续建议继续补充：

- 数据库表结构设计文档。
- MongoDB 题目文档结构设计。
- API 接口设计文档。
- Kubernetes Deployment、Service、Ingress、ConfigMap、Secret 清单设计。
- MinIO 文件访问和签名 URL 设计。
- 离线缓存包格式设计。
