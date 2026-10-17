# ============================================================
# 前端镜像：两阶段构建
#   阶段一（build）：用 Node 构建 Vue 产物
#   阶段二（运行）：用 Nginx 托管静态文件，并把 /api、/uploads 转发给后端容器
# ============================================================

# ---------- 阶段一：构建 ----------
ARG NODE_VERSION=24
FROM node:${NODE_VERSION}-alpine AS build

WORKDIR /app

# 国内机器用 npm 镜像加速；海外网络可加 --build-arg NPM_REGISTRY=https://registry.npmjs.org 换回官方源。
ARG NPM_REGISTRY=https://registry.npmmirror.com

# 先复制依赖清单，利用层缓存：package.json 不变时不重新安装依赖。
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund --registry=${NPM_REGISTRY}

COPY . .

# 接口地址：部署时前端与后端同源（由 Nginx 统一转发 /api、/uploads），
# 所以传给 axios 的基地址是 "/"；构建参数可在 docker-compose.yml 中覆盖。
ARG VITE_API_BASE_URL=/
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

# ---------- 阶段二：Nginx 静态托管 + 反向代理 ----------
FROM nginx:stable-alpine

# tzdata：让 Nginx 日志时间与业务时间一致（东八区，由 compose 注入 TZ）
RUN apk add --no-cache tzdata

# 站点配置：history 路由回退 + /api 与 /uploads 反代 + SSE 流式特调
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 前端构建产物
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
