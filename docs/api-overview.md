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
| user-service | GET | `/api/miniapp/users` | 管理员或超级管理员查看人员列表 |
| user-service | PUT | `/api/miniapp/users/{openid}/role` | 管理员或超级管理员配置用户角色 |
| content-service | GET | `/api/miniapp/content/home` | 首页教学视频、推广内容、公告 |
| content-service | GET | `/api/miniapp/files/{file_id}` | 返回 MinIO 公开资源 URL |
| bank-service | GET | `/api/miniapp/banks` | 已授权题库列表 |
| bank-service | GET | `/api/miniapp/banks/{bank_id}/chapters` | 章节列表 |
| question-service | GET | `/api/miniapp/questions/{question_id}` | 题目详情 |
| question-service | GET | `/api/miniapp/questions/offline-packages/{bank_id}` | 离线缓存包 |
| practice-service | POST | `/api/miniapp/practice/start` | 开始练习 |
| practice-service | POST | `/api/miniapp/practice/answers` | 提交练习答案 |
| practice-service | POST | `/api/miniapp/records` | 持久化保存一条已完成练习记录 |
| practice-service | GET | `/api/miniapp/records` | 记录页统计和最近练习 / 考试记录 |
| practice-service | GET | `/api/miniapp/records/trends` | 正确率趋势 |
| practice-service | GET | `/api/miniapp/records/mistakes` | 错题本 |
| practice-service | DELETE | `/api/miniapp/records/mistakes/{mistake_id}` | 手动移出错题本 |
| practice-service | GET | `/api/miniapp/records/{record_id}` | 单次完成记录详情 |
| practice-service | GET | `/api/miniapp/records/{record_id}/mistakes` | 单次完成记录中的错题 |
| practice-service | GET | `/api/miniapp/records/favorites` | 收藏题 |
| exam-service | GET | `/api/miniapp/exams/papers` | 套卷列表 |
| exam-service | POST | `/api/miniapp/exams/{paper_id}/start` | 开始考试 |
| exam-service | POST | `/api/miniapp/exams/{exam_record_id}/submit` | 交卷 |
| ranking-service | GET | `/api/miniapp/ranking/me` | 个人当前排名 |
| ranking-service | GET | `/api/miniapp/ranking/leaderboard` | 总榜 / 周榜占位数据 |
| ranking-service | GET | `/api/miniapp/ranking/medals` | 用户奖牌 |
| feedback-service | POST | `/api/miniapp/feedback` | 提交反馈 |

当前题库链路实现说明：

- `/api/miniapp/banks`
  - 直接读取 MongoDB `practice_sets`
  - 当前返回初级、中级、高级三个理论习题集
- `/api/miniapp/banks/{bank_id}/chapters`
  - 直接读取 MongoDB `questions`
  - 按 `knowledge.pathNames` 的叶子前层级聚合章节
  - 响应体包含 `bank` 和 `chapters`
- `/api/miniapp/practice/start`
  - 请求体字段：`bank_id`、`chapter_key`、`count`、`order`
  - 直接从 MongoDB `questions` 返回真实练习题列表
- `/api/miniapp/practice/answers`
  - 按题目 `_id` 回查 MongoDB `questions`
  - 返回真实答案与解析
- 记录、错题、趋势统计
  - 用户点击“完成”后，小程序会调用 `POST /api/miniapp/records`，由后端将记录持久化到 MySQL
  - “总做题数”“正确率”“考试数”“错题本”“趋势统计”都基于后端持久化记录统计
  - 正确率按总作答次数计算，不按题目去重；同一道题多次做错会累计多次错误记录
  - 当前“考试数”展示口径为完成次数，每次练习或考试点击“完成”后计一次
  - `GET /api/miniapp/records/{record_id}/mistakes` 只返回该次完成记录中的错题
  - `GET /api/miniapp/records/mistakes` 返回用户全量错题本，并按题目聚合 `wrongTimes`

## 小程序身份资料接口契约

### POST `/api/miniapp/auth/login`

用途：小程序启动时通过 `wx.login` 获取 code 后，提交给后端换取 `openid` 并建立本地业务身份。

请求体：

```json
{
  "code": "微信 wx.login 返回的 code"
}
```

响应体：

```json
{
  "token": "miniapp-openid:{openid}",
  "user": {
    "id": "{openid}",
    "openid": "{openid}",
    "nickname": "",
    "email": "",
    "avatarUrl": "",
    "role": "GUEST",
    "roleLabel": "游客",
    "status": "AUTHORIZED"
  }
}
```

规则：

- 前端不得自行生成或传入 openid。
- 后端通过微信 `jscode2session` 获取 openid。
- 如果 `users` 表中不存在该 openid，后端自动创建用户，默认角色为 `GUEST`。
- 小程序启动阶段如果旧 token 拉取 `/api/miniapp/user/me` 失败，前端应清理本地 `token/user` 缓存后重新执行 `POST /api/miniapp/auth/login`。
- 当前第一阶段 token 为简化格式，后续应替换为签名 JWT 或 Redis session。

### GET `/api/miniapp/user/me`

用途：根据 `Authorization` token 获取当前用户资料和基础授权状态。

请求头：

```text
Authorization: Bearer miniapp-openid:{openid}
```

响应体：

```json
{
  "id": "{openid}",
  "openid": "{openid}",
  "nickname": "用户昵称",
  "email": "user@example.com",
  "avatarUrl": "https://www.njwjxy.cn:30443/zuoti-minio/public-assets/users/{openid}/avatar-xxx.png",
  "role": "USER",
  "roleLabel": "普通用户",
  "status": "AUTHORIZED"
}
```

### PUT `/api/miniapp/user/me`

用途：保存“身份配置”页提交的头像、昵称、邮箱。

请求头：

```text
Authorization: Bearer miniapp-openid:{openid}
```

请求体：

```json
{
  "nickname": "用户昵称",
  "email": "user@example.com",
  "avatarBase64": "data:image/png;base64,..."
}
```

请求约束：

- 当前页面头像选择仅使用微信原生 `chooseAvatar`，前端提交给后端的是新头像的 base64 数据。
- 前端不得把本地临时文件路径当作 `avatarUrl` 回传给后端。

字段规则：

| 字段 | 规则 |
| --- | --- |
| `nickname` | 可为空；保存到 MySQL，必须支持中文 |
| `email` | 可为空；填写时需要符合邮箱格式 |
| `avatarBase64` | 可为空；提交时后端写入 MinIO 并生成公开 URL |

响应体：

```json
{
  "id": "{openid}",
  "openid": "{openid}",
  "nickname": "用户昵称",
  "email": "user@example.com",
  "avatarUrl": "https://www.njwjxy.cn:30443/zuoti-minio/public-assets/users/{openid}/avatar-xxx.png",
  "role": "USER",
  "roleLabel": "普通用户",
  "status": "AUTHORIZED"
}
```

错误处理：

| 场景 | 建议状态码 | 处理 |
| --- | --- | --- |
| token 缺失或无效 | `401` | 前端重新调用 `wx.login` 建立身份 |
| 邮箱格式错误 | `400` | 前端保留表单并提示修改 |
| 头像类型或大小不合法 | `400` | 前端保留预览并提示更换头像 |
| MinIO 上传失败 | `500` | 不覆盖旧头像 URL，前端允许重试 |

头像对象回收规则：

- 同一用户重新上传新头像并保存成功后，后端会删除旧头像对应的 MinIO 对象。
- MinIO 中只保留数据库当前 `avatarUrl` 正在引用的头像文件。

### GET `/api/miniapp/users`

用途：小程序“人员管理”页面获取用户列表。

权限：

- `ADMIN` 和 `SUPER_ADMIN` 可访问。
- `GUEST` 和 `USER` 访问返回 `403`。

响应体：

```json
[
  {
    "id": "{openid}",
    "openid": "{openid}",
    "nickname": "用户昵称",
    "email": "user@example.com",
    "avatarUrl": "https://www.njwjxy.cn:30443/zuoti-minio/public-assets/users/{openid}/avatar-xxx.png",
    "role": "USER",
    "roleLabel": "普通用户",
    "status": "AUTHORIZED"
  }
]
```

### PUT `/api/miniapp/users/{openid}/role`

用途：管理员或超级管理员配置用户角色。

请求体：

```json
{
  "role": "USER"
}
```

角色值：

| role | 展示 |
| --- | --- |
| `GUEST` | 游客 |
| `USER` | 普通用户 |
| `ADMIN` | 管理员 |
| `SUPER_ADMIN` | 超级管理员 |

权限规则：

- `SUPER_ADMIN` 可以将其他用户设置为 `ADMIN`、`USER`、`GUEST`。
- `ADMIN` 只能将其他用户设置为 `USER`、`GUEST`。
- 小程序人员管理接口不允许授予 `SUPER_ADMIN`。
- 不允许用户修改自己的角色。

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

公开资源路径约定：

| 路径 | 用途 |
| --- | --- |
| `/zuoti-minio/public-assets/video/zuoti-guide.mp4` | 首页教学视频 |
| `/zuoti-minio/public-assets/images/video-cover.png` | 首页教学视频封面 |
| `/zuoti-minio/public-assets/images/promo-*.png` | 首页推广图 |
| `/zuoti-minio/public-assets/users/{openid}/avatar-{uuid}.{ext}` | 用户头像 |

## 当前实现说明

- 身份与用户资料接口已接入 MySQL 和 MinIO：`openid` 作为 `users.id`，头像保存到 `public-assets/users/{openid}/...`。
- 题库、练习、考试、排名等接口仍以模拟数据为主，用于联调页面和验证路由。
- 除登录、公开首页内容外，小程序业务接口预期使用 `Authorization: Bearer <token>`。
- 第一阶段小程序 token 格式为 `miniapp-openid:{openid}`，后续建议替换为签名 JWT 或 Redis session。
- 后台接口预期使用管理员 token。
