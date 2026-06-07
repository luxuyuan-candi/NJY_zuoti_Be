# API 接口概览

当前后端代码为 FastAPI 微服务骨架，统一外部入口：

```text
https://www.njwjxy.cn:30443
```

## 小程序接口

| 服务 | 方法 | 路径 | 说明 |
| --- | --- | --- | --- |
| auth-service | POST | `/api/miniapp/auth/login` | 微信 code 登录，占位实现 |
| user-service | GET | `/api/miniapp/user/me` | 当前用户信息、授权状态、排名摘要 |
| content-service | GET | `/api/miniapp/content/home` | 首页教学视频、推广内容、公告 |
| content-service | GET | `/api/miniapp/files/{file_id}` | 文件访问占位接口 |
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

## 当前实现说明

- 目前接口使用模拟数据，主要用于联调页面和验证路由。
- 真实 MySQL、Redis、MongoDB、MinIO 访问层后续在 `src/zuoti_common` 中补充。
- 除登录、公开首页内容外，小程序业务接口预期使用 `Authorization: Bearer <token>`。
- 后台接口预期使用管理员 token。
