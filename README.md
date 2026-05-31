# 1C Clobus 数据爬虫

自动化从 Clobus.uz (1C云服务) 抓取数据的工具。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置

编辑 `config/settings.yaml` 填入您的 Clobus 账户信息。

### 3. 测试登录

```bash
python main.py --mode login
```

### 4. 交互式测试

```bash
python main.py --mode interactive
```

## 项目结构

```
1c/
├── config/
│   ├── settings.yaml      # 配置文件
│   └── selectors.yaml     # 页面选择器
├── src_scraper/
│   ├── browser/          # 浏览器驱动
│   ├── scrapers/         # 爬虫模块
│   ├── parsers/          # 解析器
│   ├── storage/          # 存储模块
│   ├── core/            # 核心配置
│   └── utils/           # 工具函数
├── sql/                  # 数据库脚本
├── data/                 # 数据目录
├── logs/                 # 日志目录
└── main.py              # 入口文件
```

## 使用方法

### 登录测试

```bash
python main.py --mode login
```

### 交互式调试

```bash
python main.py --mode interactive
```

### 数据爬取

```bash
# 爬取客户数据
python main.py --mode scrape --task customers

# 按日期范围爬取订单
python main.py --mode scrape --task orders --date-from 2024-01-01 --date-to 2024-12-31
```
