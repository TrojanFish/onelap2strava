# Onelap2Strava WebApp 🚴‍♂️➡️🏃‍♂️

**顽鹿竞技 (Onelap) 至 Strava 多用户室内骑行数据自动同步平台 (支持免 API Cookie 会话与官方 API 双模式)**

[**English Readme (英文文档)**](./README.md)

---

## ✨ 核心特性

- 👥 **多用户独立隔离**：支持多用户注册登录，各自绑定独立的顽鹿账号与 Strava 凭据。
- 🍪 **Strava 免 API Cookie 同步引擎**：突破 Strava 针对普通/非 API 会员账号的上传限制，自动解析 `_strava4_session` Cookie 会话与 CSRF Token 完成 `.fit` 文件上传。
- 🔑 **官方 Strava OAuth API 模式**：原生支持官方 Strava API 凭据（`Client ID`, `Client Secret`, `Refresh Token`）。
- 🪄 **网页一键 Token 换取助手**：无需在终端执行 `curl`，可在页面中直接一键换取 `Refresh Token`。
- 🔐 **零信任高强度加密**：所有敏感凭据（顽鹿密码、Strava Cookie、API 密钥）在数据库中均经过 **AES-256-GCM** 加密存储。
- ⏰ **定时自动化巡检**：支持后台自动定时拉取顽鹿骑行纪录并上传至 Strava，增量去重。
- 📊 **现代高颜值 Web 仪表盘**：暗黑风 SPA 界面，直观展示同步结果、错误日志及可视化配置教程。

---

## 🚀 部署指南 (VPS Docker Compose)

### 环境要求
- VPS 服务器 (Linux / Ubuntu / Debian / CentOS)
- 已安装 Docker 与 Docker Compose

### 第一步：克隆代码仓库
```bash
git clone https://github.com/TrojanFish/onelap2strava.git
cd onelap2strava
```

### 第二步：启动容器
```bash
docker-compose up -d
```
启动后在浏览器中访问 `http://<你的VPS公网IP>:8000` 即可进入 Web 管理界面！

---

## 🔑 配置 Strava 凭据教程

### 模式一：免 API Cookie 模式 (普通用户推荐)
1. 在电脑 Chrome/Edge 浏览器中打开并登录 [Strava 官网](https://www.strava.com)。
2. 按 `F12` 打开开发者工具，切换到 **Application (应用)** 选项卡。
3. 展开左侧 **Storage -> Cookies -> https://www.strava.com**。
4. 找到 `_strava4_session` 项，双击复制其 **Value** 值。
5. 登录 Web 平台，在 **“账号与 Cookie/API 配置”** 页面粘贴并保存。

---

### 模式二：官方 Strava API 模式 (开发者)

#### 1. 获取授权 Code
访问 [Strava API 设置页面](https://www.strava.com/settings/api) 获取 **Client ID (客户 ID)** 与 **Client Secret (客户端密钥)**。然后在浏览器中打开以下链接授权：
```text
https://www.strava.com/oauth/authorize?client_id=你的客户ID&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=read,activity:write,activity:read_all
```
点击“授权”后重定向至 `http://localhost/?code=...`，复制 `code=` 后面的字符串（如 `7754cccfa08317e4acd55f612dcc01f5465b4d11`）。

#### 2. 换取 Refresh Token
- **方式 A（网页一键换取助手）**：在 Web 界面中填入 `Client ID`、`Client Secret` 及第一步获取的 `Code`，点击 **【一键生成 Refresh Token】**。
- **方式 B（终端 curl）**：
```bash
curl -X POST https://www.strava.com/oauth/token   -F client_id=你的客户ID   -F client_secret=你的客户端密钥   -F code=第一步获取的code   -F grant_type=authorization_code
```
复制返回 JSON 中的 `refresh_token` 填入网页并保存即可。
