# dsh-docker

把 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)（dsh）Web 界面
包成带登录认证的 Docker 镜像：**dsh 本体来自官方 npm 包 `@deepseek-ai/dsh`**，本仓库负责
「dsh + 认证网关」的打包，并提供 dsh-gateway 的一个稳定性修复。

- 镜像：`ghcr.io/zxcwan/dsh-docker:latest`（`linux/amd64` + `linux/arm64`）
- 认证网关源码：本仓库 `gateway/`（源自 [dsh-gateway](https://github.com/myflv/dsh-gateway)）
- 上游：`myflv/dsh-gateway`；本 fork 相对上游的改动见[下方](#本-fork-的修复)

## 快速开始

1. 新建目录并放入 `docker-compose.yml`：

```yaml
services:
  server:
    image: ghcr.io/zxcwan/dsh-docker:latest
    restart: unless-stopped
    environment:
      AUTH_USER: admin                 # 登录用户名，必填
      AUTH_PASSWORD: change-me-please  # 登录密码，必填（不填启动报错）
      # TZ: Asia/Shanghai              # 可选，默认容器时区
    ports:
      - 8080:8080    # HTTP：登录入口与 dsh Web
      - 8443:8443    # HTTPS 自签证书（仅供本机/调试）
    volumes:
      - ./workspace:/root              # 工作区 + dsh 配置 + ssh 密钥
```

2. 启动：

```sh
docker compose up -d
```

3. 登录：打开 `http://<宿主机IP>:8080/plugins/dsh-gateway-auth/login`，用
   `AUTH_USER` / `AUTH_PASSWORD` 登录，登录后自动带上 dsh 的启动令牌，直接进入 Web UI。

> 镜像包可见性：GHCR 上的包默认是 private。要么在 GitHub 包设置里改成 public
> （Settings → Packages → dsh-docker → Change visibility），要么在部署机执行
> `docker login ghcr.io` 并提供一个有 `read:packages` 权限的 token。

## 它是什么

```
浏览器 ──► dsh-gateway（Go，本仓库 gateway/）──► dsh web（npm @deepseek-ai/dsh）
             │  登录 / 会话 / CSRF / 启动令牌透传
             └─ /root 挂卷：工作区、~/.dsh 配置、~/.ssh
```

- **登录认证**：bcrypt 密码、会话 cookie、CSRF 防护；dsh 自身启动令牌由网关捕获并自动带上。
- **HTTPS**：8443 使用镜像内自签证书（只含 localhost/127.0.0.1），公网请用 frp + nginx 反代
  8080 并配正式证书（cookie 的 Secure 标志会自动适配）。
- **终端**：镜像内带 nvm（`/opt/nvm`），登录 shell 自动注入；`nvm install <ver> && nvm use <ver>`
  可以临时切换 Node 版本（重建容器后需重装）。

## 本 fork 的修复

上游 dsh-gateway 在重写 `__DSH_BOOT__` 启动清单时丢掉 `release` 字段，导致 dsh 客户端启动后
把自己的身份认成 `unknown`，随后收到带 `release` 的 Host graph 时误判「版本变化」并暂停热更新。
本 fork 的改动：

| 文件 | 改动 |
|---|---|
| `gateway/trust_plugin.go` | 保留 `release`（`json.RawMessage` + `omitempty`，旧版图形态不漂移） |
| `gateway/trust_plugin_test.go` | 覆盖 release 保留 / 旧版图不凭空获得 release |
| `Dockerfile` | gateway-build 阶段执行 `go test ./...` |

除这三处外网关与上游一致。

## 构建

GitHub Actions（`.github/workflows/build.yml`）自动构建推送 GHCR：

| 触发 | 说明 |
|---|---|
| push `main` | 立即构建（fork 需先在 Actions 页面点一次 "I understand my workflows"） |
| `workflow_dispatch` | 手动触发 |
| schedule 03:17 UTC | 每天检查 dsh 官方新版本，有新版才构建 |

dsh 版本 = GitHub release ∩ npm 已发布版本里的最新者，通过 `--build-arg DSH_VERSION`
注入，`npm install -g @deepseek-ai/dsh@$DSH_VERSION` 从官方 npm 拉取。镜像打两个标签：
`latest` 与 `:<dsh版本>`。

自己构建（不用 GitHub）：

```sh
git clone https://github.com/zxcwan/dsh-docker && cd dsh-docker
docker build -t dsh-docker:local --build-arg DSH_VERSION=0.2.2-rc.5 .
```

## 升级

```sh
docker compose pull && docker compose up -d
```

查看当前版本：`docker inspect -f '{{.Config.Image}}' <容器名>` 或看 `docker compose ps` 的镜像标签。

## 同步上游 / 二次开发

```sh
git fetch origin main
git merge origin/main     # 冲突主要集中在 gateway/ 与 Dockerfile
git push fork main        # push 触发 Actions 构建
```

## 常见问题

- **拉镜像 401**：包还是 private，改 public 或 `docker login ghcr.io`。
- **Actions 不跑 / push 不触发构建**：fork 仓库需要在 Actions 页面点一次
  "I understand my workflows, go ahead and enable them"。
- **dsh 提示新版本但镜像还是旧的**：Actions 的 schedule 任务是 03:17 UTC 检查一次；
  想立刻更新就手动 dispatch 或在仓库 push 一次。
- **8443 证书警告**：自签证书只用于本机调试，公网请用反代 + 正式证书。
- **容器重建后 nvm 装的 Node 丢了**：nvm 版本在容器层，重装即可（或写进自己的 Dockerfile）。

## 上游致谢

- [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)（dsh 本体，npm 包）
- [dsh-gateway](https://github.com/myflv/dsh-gateway)（认证网关原始实现，本 fork 的上游；
  上游未附许可证文件，二次分发前请自行确认授权）