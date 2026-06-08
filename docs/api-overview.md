# API 接口概览

当前后端代码为 FastAPI 微服务骨架，统一外部入口：

```text
https://www.njwjxy.cn:30443
```

## 小程序接口

| 服务 | 方法 | 路径 | 说明 |
| --- | --- | --- | --- |
| auth-service | POST | `/api/miniapp/auth/login` | 微信 code 换取 openid，自动创建 / 更新用户身份并返回 token |
| user-service | GET | `/api/miniapp/user/me` | 当前用户信息、授权状态、排名摘要 |
| user-service | PUT | `/api/miniapp/user/me` | 保存当前用户昵称、邮箱、头像；头像写入 MinIO |
| content-service | GET | `/api/miniapp/content/home` | 首页教学视频、推广内容、公告 |
| content-service | GET | `/api/miniapp/files/{file_id}` | 返回 MinIO 公开资源 URL |
| bank-service | GET | `/api/miniapp/banks` | 已授权题库列表 |
| bank-service | GET | `/api/miniapp/banks/{bank_id}/chapters` | 章节列表 |
| question-service | GET | `/api/miniapp/questions/{question_id}` | 题目详情 |
| question-service | GET | `/api/miniapp/questions/offline-packages/{bank_id}` | 离线缓存包 |
| practice-service | POST | `/api/miniapp/practice/start` | 开始练习 |
| practice-service | POST | `/api/miniapp/practice/answers` | 提交练习答案 |
| practice-service | GET | `/api/miniapp/records` | 最近练习 / 考试记录 |
| practice-service | GET | `/api/miniapp/records/mistakes` | 错题本 |
| practice-service | GET | `/api/miniapp/records/favorites` | 收藏题 |
| exam-service | GET | `/api/miniapp/exams/papers` | 套卷列表 |
| exam-service | POST | `/api/miniapp/exams/{paper_id}/start` | 开始考试 |
| exam-service | POST | `/api/miniapp/exams/{exam_record_id}/submit` | 交卷 |
| ranking-service | GET | `/api/miniapp/ranking/me` | 个人当前排名 |
| ranking-service | GET | `/api/miniapp/ranking/leaderboard` | 总榜 / 周榜占位数据 |
| ranking-service | GET | `/api/miniapp/ranking/medals` | 用户奖牌 |
| feedback-service | POST | `/api/miniapp/feedback` | 提交反馈 |

## 后台接口

| 服务 | 方法 | 路径 | 说明 |
| --- | --- | --- | --- |
| auth-service | POST | `/api/admin/auth/login` | 管理员登录，占位实现 |
| auth-service | POST | `/api/admin/auth/logout` | 管理员退出 |
| admin-service | GET | `/api/admin/dashboard` | 后台首页指标 |
| admin-service | GET | `/api/admin/settings` | 系统设置 |
| admin-service | GET | `/api/admin/statistics` | 数据统计 |
| user-service | GET | `/api/admin/users` | 用户列表 |
| user-service | POST | `/api/admin/users/authorizations` | 用户授权 |
| bank-service | GET | `/api/admin/banks` | 题库列表 |
| bank-service | GET | `/api/admin/banks/{bank_id}/chapters` | 章节管理 |
| question-service | GET | `/api/admin/questions` | 题目管理 |
| exam-service | GET | `/api/admin/papers` | 套卷管理 |
| content-service | GET | `/api/admin/content/home` | 首页内容管理 |
| content-service | POST | `/api/admin/files` | 文件上传占位接口 |
| feedback-service | GET | `/api/admin/feedback` | 反馈管理 |

## 公开资源入口

| 资源 | HTTPS 入口 |
| --- | --- |
| MinIO S3 公开资源 | `https://www.njwjxy.cn:30443/zuoti-minio/public-assets/...` |
| MinIO Console | `https://www.njwjxy.cn:30443/zuoti-minio-console/` |

## 当前实现说明

- 身份与用户资料接口已接入 MySQL 和 MinIO：`openid` 作为 `users.id`，头像保存到 `public-assets/users/{openid}/...`。
- 题库、练习、考试、排名等接口仍以模拟数据为主，用于联调页面和验证路由。
- 除登录、公开首页内容外，小程序业务接口预期使用 `Authorization: Bearer <token>`。
- 第一阶段小程序 token 格式为 `miniapp-openid:{openid}`，后续建议替换为签名 JWT 或 Redis session。
- 后台接口预期使用管理员 token。
