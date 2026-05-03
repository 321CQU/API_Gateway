# 321CQU_APIGateway——321CQU后端微服务网关
## 简介
该项目服务于321CQU后端微服务架构，采用Sanic框架，对API请求提供统一入口

## 本地运行前置条件

项目依赖外部包 `_321CQU`，该包不在本仓库内，提供 gRPC 管理器、数据库抽象、配置基类和服务枚举。运行服务或测试前需要让 Python 能导入它，例如：

```bash
export PYTHONPATH="/path/to/321CQU-package:${PYTHONPATH}"
uv sync
uv run pytest test/ -v
```

如果未接入该包，常见失败形态是收集测试或启动服务时出现 `ModuleNotFoundError: No module named '_321CQU'`。

## 依赖与容器

本地开发以 `pyproject.toml` 和 `uv.lock` 为依赖权威来源。Docker 构建也使用 uv lockfile 安装依赖，避免容器环境与本地 uv 环境漂移；更新依赖后请同步提交 lockfile。

## 兼容层边界

`api/legacy_compat.py` 只服务历史客户端路径和响应形态。新增正式 API 应优先放入对应业务模块，并沿用当前装饰器链和统一响应结构；除非确认为历史客户端兼容需求，不继续扩大兼容层。

## 预期功能
- [x] API请求权限校验
- [x] API请求参数校验
- [x] API调用文档通过OpenAPI自动生成（基于Sanic-ext提供的OpenAPI自动生成功能）
- [ ] 迁移旧有321CQU后端服务
- [ ] 微服务服务注册与发现
