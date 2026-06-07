# NJY 做题后端

后端采用 Python + FastAPI 微服务骨架，按设计文档拆分为：

- `auth-service`
- `user-service`
- `content-service`
- `bank-service`
- `question-service`
- `practice-service`
- `exam-service`
- `ranking-service`
- `feedback-service`
- `admin-service`

所有服务部署在 Kubernetes 的 `zuoti` namespace。中间件包含 MySQL、Redis、MongoDB、MinIO。

## 本地运行

安装依赖：

```bash
pip install -r requirements.txt
```

运行某个服务：

```bash
set SERVICE_MODULE=auth
uvicorn services.auth.main:app --reload --host 0.0.0.0 --port 8000
```

健康检查：

```bash
curl http://127.0.0.1:8000/healthz
```

## Docker

构建镜像：

```bash
docker build -t ghcr.io/luxuyuan-candi/njy-zuoti-be:latest .
```

运行示例：

```bash
docker run --rm -p 8000:8000 -e SERVICE_MODULE=auth ghcr.io/luxuyuan-candi/njy-zuoti-be:latest
```

## Kubernetes

先创建真实 Secret。不要把真实密码写入仓库，也不要把密钥文件放在仓库目录中。

```bash
kubectl create namespace zuoti
kubectl -n zuoti create secret generic zuoti-app-secret --from-env-file=/secure/path/zuoti-app-secret.env
```

`/secure/path/zuoti-app-secret.env` 应由密钥系统或运维流程提供，不提交到 Git。

部署：

```bash
kubectl apply -k k8s
```

Ingress 复用集群已有 Ingress Controller，本仓库只创建项目 Ingress 资源。外部入口：

```text
https://www.njwjxy.cn:30443
```

## 安全规则

- AppID 可作为非敏感配置保存。
- AppSecret、数据库密码、Redis 密码、MongoDB 密码、MinIO key、token 签名密钥不能明文入仓。
- `.env.example` 只保留空值模板。
- `k8s/base/secrets.example.yaml` 只是字段示例，不应携带真实值。
