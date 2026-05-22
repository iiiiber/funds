# FundQuant 管理后台系统 - 开发文档

**版本**: v2.0
**日期**: 2026-04-13
**状态**: 待确认

---

## 1. 项目概述

### 1.1 背景
FundQuant 基金量化助手现有前端面向用户展示，当前端功能已完善。现需要开发独立的管理后台系统，用于运维管理。

### 1.2 目标
为 FundQuant 开发独立的管理后台系统，实现持仓管理、AI模型配置、第三方API管理等功能。

### 1.3 数据库配置

| 配置项 | 值 |
|-------|-----|
| 数据库 | funds |
| 用户名 | funds |
| 密码 | 6NZ7Hp2Z5YWShARJ |
| 主机 | 127.0.0.1 |
| 端口 | 3306 |

---

## 2. 功能模块

### 2.1 功能清单

| 模块 | 功能点 | 优先级 |
|-----|-------|-------|
| **登录认证** | 独立登录页面、Session管理、密码修改 | P0 |
| **持仓管理** | 基金列表、新增/编辑/删除持仓、CSV导入导出 | P0 |
| **AI模型管理** | 模型列表、模型配置、模型切换、连接测试 | P0 |
| **API管理** | API密钥配置、服务监控、健康检查 | P1 |
| **系统设置** | 基本设置、缓存管理（预留） | P2 |
| **操作日志** | 日志查询（预留） | P2 |
| **定时任务** | 定时任务管理（预留） | P3 |
| **数据备份** | 备份功能（预留） | P3 |

### 2.2 功能详细说明

#### 2.2.1 登录认证模块
- **登录页面**: `/admin/login`
- **首页**: `/admin/dashboard`
- **功能**:
  - 用户名密码登录
  - 记住登录状态
  - 密码修改
  - 登出功能
  - 登录日志记录

#### 2.2.2 持仓管理模块
- **基金列表**
  - 分页展示（每页20条）
  - 按代码/名称搜索
  - 按盈亏/日期排序
  - 字段：代码、名称、成本、当前净值、盈亏、盈亏率、更新时间

- **新增持仓**
  - 基金代码（自动补全）
  - 基金名称（自动获取）
  - 持有份额
  - 买入成本
  - 备注

- **编辑持仓**
  - 修改所有字段
  - 修改历史记录

- **删除持仓**
  - 单个/批量删除
  - 二次确认

- **批量操作**
  - CSV导入
  - CSV导出

#### 2.2.3 AI模型管理模块
- **模型列表**
  - 展示所有已配置模型
  - 字段：名称、类型、API地址、状态、默认/非默认

- **模型配置**
  ```
  字段说明：
  - 模型名称: MiniMax v2
  - 模型类型: chat / embedding / image / music
  - API地址: https://api.minimaxi.com/anthropic/v1/messages
  - API密钥: 加密存储
  - 模型标识: MiniMax-M2.7-highspeed
  - 请求超时: 30秒
  - 温度参数: 0.5
  - 最大Token: 300
  - 状态: 启用/禁用
  ```

- **模型切换**
  - 设置默认模型
  - 手动/自动健康检查

#### 2.2.4 API管理模块
- **API配置列表**
  - 字段：名称、服务商、API地址、限流设置、状态

- **API配置项**
  ```
  - 服务名称: 行情数据服务
  - 服务商: 天天基金 / 东方财富 / 自定义
  - API地址: https://api.fund.eastmoney.com/
  - 接口限流: 100次/分钟
  - API密钥: 加密存储
  - 状态: 正常/异常
  ```

- **服务监控**
  - 可用性检测
  - 响应时间
  - 错误率统计
  - 健康检查

#### 2.2.5 系统设置模块（预留）
- 基本参数配置
- 缓存管理

#### 2.2.6 操作日志模块（预留）
- 登录日志
- 操作日志
- 错误日志

#### 2.2.7 定时任务模块（预留）
- 任务列表
- 任务配置
- 执行记录

#### 2.2.8 数据备份模块（预留）
- 手动备份
- 定时备份配置

---

## 3. 数据库设计

### 3.1 ER图

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  admins    │     │  holdings   │     │ ai_models   │
├─────────────┤     ├─────────────┤     ├─────────────┤
│ id (PK)     │     │ id (PK)     │     │ id (PK)     │
│ username    │     │ code        │     │ name        │
│ password    │     │ name        │     │ type        │
│ salt        │     │ shares      │     │ api_url     │
│ created_at  │     │ cost        │     │ api_key     │
│ updated_at  │     │ note        │     │ model_id    │
│ last_login  │     │ created_at  │     │ timeout     │
└─────────────┘     │ updated_at  │     │ temperature │
                    └─────────────┘     │ max_tokens  │
                                         │ is_default  │
┌─────────────┐     ┌─────────────┐     │ status      │
│ api_configs │     │login_logs  │     │ created_at  │
├─────────────┤     ├─────────────┤     │ updated_at  │
│ id (PK)     │     │ id (PK)     │     └─────────────┘
│ name        │     │ admin_id    │
│ provider    │     │ ip          │
│ api_url     │     │ user_agent  │
│ api_key     │     │ login_time  │
│ rate_limit  │     │ status      │
│ status      │     └─────────────┘
│ created_at  │
│ updated_at  │
└─────────────┘
```

### 3.2 表结构

#### admins - 管理员表
```sql
CREATE TABLE admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL COMMENT '用户名',
    password VARCHAR(255) NOT NULL COMMENT '密码(SHA256+salt)',
    salt VARCHAR(32) NOT NULL COMMENT '盐值',
    real_name VARCHAR(50) DEFAULT '' COMMENT '真实姓名',
    email VARCHAR(100) DEFAULT '' COMMENT '邮箱',
    status TINYINT DEFAULT 1 COMMENT '状态: 1正常 0禁用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login DATETIME DEFAULT NULL COMMENT '最后登录时间',
    INDEX idx_username (username),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='管理员表';
```

#### holdings - 持仓表
```sql
CREATE TABLE holdings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(20) NOT NULL COMMENT '基金代码',
    name VARCHAR(100) NOT NULL COMMENT '基金名称',
    shares DECIMAL(12,4) DEFAULT 0 COMMENT '持有份额',
    cost DECIMAL(10,4) DEFAULT 0 COMMENT '买入成本',
    nav DECIMAL(10,4) DEFAULT 0 COMMENT '当前净值',
    amount DECIMAL(12,2) DEFAULT 0 COMMENT '持仓金额',
    profit DECIMAL(12,2) DEFAULT 0 COMMENT '盈亏金额',
    profit_pct DECIMAL(8,2) DEFAULT 0 COMMENT '盈亏率%',
    note TEXT COMMENT '备注',
    status TINYINT DEFAULT 1 COMMENT '状态: 1正常 0已删除',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_code (code),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='持仓表';
```

#### ai_models - AI模型配置表
```sql
CREATE TABLE ai_models (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT '模型名称',
    type VARCHAR(50) NOT NULL COMMENT '模型类型: chat/embedding/image/music',
    api_url VARCHAR(500) NOT NULL COMMENT 'API地址',
    api_key VARCHAR(255) NOT NULL COMMENT 'API密钥(加密)',
    model_id VARCHAR(100) NOT NULL COMMENT '模型标识',
    timeout INT DEFAULT 30 COMMENT '请求超时(秒)',
    temperature DECIMAL(3,2) DEFAULT 0.50 COMMENT '温度参数',
    max_tokens INT DEFAULT 300 COMMENT '最大Token数',
    is_default TINYINT DEFAULT 0 COMMENT '是否默认: 1是 0否',
    status TINYINT DEFAULT 1 COMMENT '状态: 1启用 0禁用',
    remark TEXT COMMENT '备注',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_type (type),
    INDEX idx_status (status),
    INDEX idx_default (is_default)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI模型配置表';
```

#### api_configs - API配置表
```sql
CREATE TABLE api_configs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT '配置名称',
    provider VARCHAR(50) NOT NULL COMMENT '服务商',
    api_url VARCHAR(500) NOT NULL COMMENT 'API地址',
    api_key VARCHAR(255) DEFAULT '' COMMENT 'API密钥(加密)',
    rate_limit INT DEFAULT 100 COMMENT '限流: 次/分钟',
    status TINYINT DEFAULT 1 COMMENT '状态: 1正常 0异常',
    last_check DATETIME DEFAULT NULL COMMENT '最后检查时间',
    last_response INT DEFAULT 0 COMMENT '最后响应时间(ms)',
    remark TEXT COMMENT '备注',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_provider (provider),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='API配置表';
```

#### login_logs - 登录日志表
```sql
CREATE TABLE login_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT DEFAULT NULL COMMENT '管理员ID',
    username VARCHAR(50) NOT NULL COMMENT '登录用户名',
    ip VARCHAR(50) DEFAULT '' COMMENT 'IP地址',
    user_agent TEXT COMMENT '浏览器信息',
    login_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'success' COMMENT '登录状态: success/failed',
    fail_reason VARCHAR(100) DEFAULT '' COMMENT '失败原因',
    INDEX idx_admin_id (admin_id),
    INDEX idx_username (username),
    INDEX idx_login_time (login_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='登录日志表';
```

#### operation_logs - 操作日志表（预留）
```sql
CREATE TABLE operation_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT NOT NULL COMMENT '管理员ID',
    module VARCHAR(50) NOT NULL COMMENT '模块',
    action VARCHAR(50) NOT NULL COMMENT '操作',
    target_type VARCHAR(50) DEFAULT '' COMMENT '操作对象类型',
    target_id INT DEFAULT NULL COMMENT '操作对象ID',
    detail TEXT COMMENT '操作详情',
    ip VARCHAR(50) DEFAULT '' COMMENT 'IP地址',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_admin_id (admin_id),
    INDEX idx_module (module),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='操作日志表';
```

#### system_settings - 系统设置表（预留）
```sql
CREATE TABLE system_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    setting_key VARCHAR(100) UNIQUE NOT NULL COMMENT '设置键',
    setting_value TEXT COMMENT '设置值',
    setting_type VARCHAR(20) DEFAULT 'string' COMMENT '类型: string/int/json',
    remark VARCHAR(255) DEFAULT '' COMMENT '说明',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_key (setting_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统设置表';
```

### 3.3 初始化数据

```sql
-- 管理员初始化数据 (密码: FundQuant@2026)
INSERT INTO admins (username, password, salt, real_name) VALUES 
('admin', 'a3f8c9b2d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1', 'random_salt_123456', '系统管理员');

-- AI模型初始化数据
INSERT INTO ai_models (name, type, api_url, api_key, model_id, timeout, temperature, max_tokens, is_default, status) VALUES 
('MiniMax v2', 'chat', 'https://api.minimaxi.com/anthropic/v1/messages', '', 'MiniMax-M2.7-highspeed', 30, 0.50, 300, 1, 1);

-- API配置初始化数据
INSERT INTO api_configs (name, provider, api_url, rate_limit, status) VALUES 
('天天基金行情', 'eastmoney', 'https://api.fund.eastmoney.com/', 100, 1),
('东方财富行情', 'eastmoney2', 'https://api.doctor.cc/index', 100, 1);

-- 系统设置初始化数据
INSERT INTO system_settings (setting_key, setting_value, setting_type, remark) VALUES 
('site_title', 'FundQuant 管理后台', 'string', '网站标题'),
('page_size', '20', 'int', '默认分页数'),
('cache_enabled', 'true', 'string', '缓存开关');
```

---

## 4. 技术架构

### 4.1 技术栈

| 层级 | 技术选型 | 说明 |
|-----|---------|-----|
| 前端 | HTML + TailwindCSS + Vanilla JS | 与主站一致 |
| 后端 | Flask (Python) | 复用现有框架 |
| 数据库 | MySQL 8.0 | 数据库名: funds |
| ORM | SQLAlchemy | 轻量级ORM |
| 认证 | Session + SHA256 | 独立认证系统 |
| 部署 | 独立端口 8081 | 与主站 8080 分离 |

### 4.2 目录结构

```
/www/wwwroot/funds.imoons.cn/
├── admin/
│   ├── __init__.py              # Flask蓝图初始化
│   ├── admin.py                 # 管理后台主入口
│   ├── templates/
│   │   ├── login.html           # 登录页面
│   │   └── dashboard.html       # 管理后台框架页
│   ├── static/
│   │   ├── css/
│   │   │   └── admin.css        # 管理后台样式
│   │   └── js/
│   │       └── admin.js         # 管理后台JS
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py              # 数据库基类
│   │   ├── admin.py             # 管理员模型
│   │   ├── holding.py            # 持仓模型
│   │   ├── ai_model.py           # AI模型配置
│   │   ├── api_config.py         # API配置
│   │   ├── login_log.py          # 登录日志
│   │   └── operation_log.py      # 操作日志
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py              # 认证路由
│   │   ├── holdings.py           # 持仓管理路由
│   │   ├── ai_models.py          # AI模型路由
│   │   ├── api_manage.py         # API管理路由
│   │   └── settings.py           # 系统设置路由
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py       # 认证服务
│   │   ├── holding_service.py    # 持仓服务
│   │   ├── ai_service.py         # AI模型服务
│   │   └── api_service.py        # API服务
│   └── utils/
│       ├── __init__.py
│       ├── db.py                 # 数据库连接
│       ├── encryption.py         # 加密工具
│       └── response.py           # 响应封装
├── app/
│   └── web.py                    # 现有主站（主端口8080）
├── data/
│   ├── holdings.json             # 持仓数据（现有，与MySQL同步）
│   └── ...
├── backups/                       # 备份目录
└── requirements_admin.txt         # 依赖文件
```

### 4.3 Flask蓝图结构

```
/admin (蓝图前缀)
├── /login        GET/POST  - 登录页
├── /logout       GET       - 登出
├── /             GET       - 管理后台首页(dashboard)
├── /holdings     GET       - 持仓管理页
├── /models       GET       - AI模型管理页
├── /api-manage   GET       - API管理页
└── /settings     GET       - 系统设置页

/admin/api (API前缀)
├── /auth/login        POST - 登录接口
├── /auth/logout       POST - 登出接口
├── /auth/password     POST - 修改密码
├── /holdings          GET/POST    - 持仓列表/新增
├── /holdings/<id>     PUT/DELETE  - 更新/删除
├── /holdings/import   POST        - CSV导入
├── /holdings/export   GET         - CSV导出
├── /models            GET/POST   - 模型列表/新增
├── /models/<id>       PUT/DELETE  - 更新/删除
├── /models/<id>/test  POST        - 测试连接
├── /models/default    POST        - 设置默认模型
├── /apis              GET/POST   - API列表/新增
├── /apis/<id>         PUT/DELETE - 更新/删除
├── /apis/<id>/test    POST       - 测试API
├── /apis/monitor      GET        - 服务监控
├── /settings          GET/PUT    - 获取/更新设置
└── /logs/login        GET        - 登录日志
```

---

## 5. API接口设计

### 5.1 认证接口

| 方法 | 路径 | 说明 | 参数 |
|-----|------|-----|-----|
| POST | /admin/api/auth/login | 登录 | username, password |
| POST | /admin/api/auth/logout | 登出 | - |
| POST | /admin/api/auth/password | 修改密码 | old_password, new_password |
| GET | /admin/api/auth/info | 当前用户信息 | - |

### 5.2 持仓管理接口

| 方法 | 路径 | 说明 | 参数 |
|-----|------|-----|-----|
| GET | /admin/api/holdings | 持仓列表 | page, page_size, search, sort |
| POST | /admin/api/holdings | 新增持仓 | code, name, shares, cost, note |
| PUT | /admin/api/holdings/:id | 更新持仓 | id, shares, cost, note |
| DELETE | /admin/api/holdings/:id | 删除持仓 | id |
| POST | /admin/api/holdings/import | CSV导入 | file (form-data) |
| GET | /admin/api/holdings/export | CSV导出 | - |
| GET | /admin/api/holdings/suggest | 基金代码补全 | keyword |

### 5.3 AI模型管理接口

| 方法 | 路径 | 说明 | 参数 |
|-----|------|-----|-----|
| GET | /admin/api/models | 模型列表 | - |
| POST | /admin/api/models | 新增模型 | name, type, api_url, api_key, model_id... |
| PUT | /admin/api/models/:id | 更新模型 | 同上 |
| DELETE | /admin/api/models/:id | 删除模型 | id |
| POST | /admin/api/models/:id/test | 测试连接 | id |
| POST | /admin/api/models/default | 设置默认 | id |
| GET | /admin/api/models/:id/health | 健康检查 | id |

### 5.4 API管理接口

| 方法 | 路径 | 说明 | 参数 |
|-----|------|-----|-----|
| GET | /admin/api/apis | API列表 | - |
| POST | /admin/api/apis | 新增配置 | name, provider, api_url, api_key... |
| PUT | /admin/api/apis/:id | 更新配置 | 同上 |
| DELETE | /admin/api/apis/:id | 删除配置 | id |
| POST | /admin/api/apis/:id/test | 测试API | id |
| GET | /admin/api/apis/monitor | 服务监控 | - |
| GET | /admin/api/apis/:id/health | 单项健康检查 | id |

### 5.5 系统设置接口（预留）

| 方法 | 路径 | 说明 | 参数 |
|-----|------|-----|-----|
| GET | /admin/api/settings | 获取设置 | key (可选) |
| PUT | /admin/api/settings | 更新设置 | key, value |
| POST | /admin/api/cache/clear | 清空缓存 | - |

### 5.6 日志接口（预留）

| 方法 | 路径 | 说明 | 参数 |
|-----|------|-----|-----|
| GET | /admin/api/logs/login | 登录日志 | page, page_size |
| GET | /admin/api/logs/operation | 操作日志 | page, page_size, module |

---

## 6. 安全设计

### 6.1 认证机制
- 登录页面：`/admin/login`
- Session存储在服务器端
- 密码加密：SHA256(password + salt)
- Session超时：2小时
- 连续登录失败5次，锁定10分钟

### 6.2 权限控制
- 单管理员模式（admin）
- 所有管理操作需登录
- 敏感操作记录日志

### 6.3 数据安全
- API密钥加密存储（AES）
- SQL注入防护（ORM）
- XSS防护（HTML转义）
- CSRF防护（Token）

---

## 7. UI设计

### 7.1 页面清单

| 页面 | 路径 | 说明 |
|-----|------|-----|
| 登录页 | /admin/login | 独立登录页面 |
| 首页 | /admin | Dashboard，展示统计信息 |
| 持仓管理 | /admin/holdings | 基金列表、新增/编辑 |
| AI模型 | /admin/models | 模型配置列表 |
| API管理 | /admin/api-manage | API配置列表 |
| 系统设置 | /admin/settings | 基本设置（预留） |

### 7.2 布局结构

```
┌─────────────────────────────────────────────────────────────┐
│  FundQuant Admin          │ 当前用户 │ 设置 │ 登出 │
├──────────┬──────────────────────────────────────────────────┤
│          │                                                  │
│  📊 持仓  │                                                  │
│  🤖 AI   │                                                  │
│  🔌 API  │              内容区域                            │
│  ⚙️ 设置 │                                                  │
│  📝 日志 │                                                  │
│          │                                                  │
├──────────┴──────────────────────────────────────────────────┤
│                      © 2026 FundQuant                       │
└─────────────────────────────────────────────────────────────┘
```

### 7.3 风格
- 与主站一致（深色主题 + 玻璃拟态）
- TailwindCSS 响应式设计
- 移动端适配

---

## 8. 部署方案

### 8.1 端口分配

| 服务 | 端口 | 访问地址 |
|-----|------|---------|
| 主站 | 8080 | https://funds.imoons.cn |
| 管理后台 | 8081 | https://funds.imoons.cn/admin |

### 8.2 Nginx配置

```nginx
# 管理后台代理
location /admin {
    proxy_pass http://127.0.0.1:8081;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}

# 管理后台API代理
location /admin/api {
    proxy_pass http://127.0.0.1:8081;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

### 8.3 初始账号

| 项目 | 值 |
|-----|-----|
| 用户名 | admin |
| 密码 | FundQuant@2026 |
| 角色 | 超级管理员 |

### 8.4 启动方式

```bash
# 使用独立进程管理
cd /www/wwwroot/funds.imoons.cn
/www/server/panel/pyenv/bin/python3 -m admin.admin

# 或使用Gunicorn
gunicorn -w 2 -b 127.0.0.1:8081 admin.admin:app
```

---

## 9. 开发计划

### Phase 1: 基础架构（预计1天）
- [ ] 数据库表创建
- [ ] Flask蓝图配置
- [ ] 数据库连接封装
- [ ] 登录认证功能
- [ ] 基础UI框架

### Phase 2: 持仓管理（预计1天）
- [ ] 持仓列表页
- [ ] 新增/编辑/删除功能
- [ ] CSV导入导出
- [ ] 与现有holdings.json同步

### Phase 3: AI模型管理（预计1天）
- [ ] 模型列表页
- [ ] 新增/编辑/删除功能
- [ ] 连接测试
- [ ] 默认模型切换

### Phase 4: API管理（预计1天）
- [ ] API配置列表页
- [ ] 新增/编辑/删除功能
- [ ] 健康检查
- [ ] 服务监控

### Phase 5: 系统设置（预留）
- [ ] 基本设置页
- [ ] 缓存管理

**总预计工时: 4天**

---

## 10. 待确认事项

以下事项已确认：

| 项目 | 确认 |
|-----|-----|
| 独立登录页面 | ✅ 是 |
| 数据库用MySQL | ✅ 是 |
| 数据库名: funds | ✅ 是 |
| 用户名: funds | ✅ 是 |
| 功能全部需要 | ✅ 是 |
| 其他功能预留 | ✅ 是 |

---

## 11. 预估成果物

1. 数据库表结构及初始化SQL
2. Flask管理后台（含蓝图）
3. 前端页面（HTML/CSS/JS）
4. API接口文档
5. 部署文档

---

**文档版本**: v2.0
**确认后**: 开始Phase 1开发
