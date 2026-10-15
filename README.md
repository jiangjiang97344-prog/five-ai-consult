# 五方会诊 · 云端版 部署说明

## 文件清单
- `index.html` —— 手机/电脑浏览器直接用的网页
- `api/consult.py` —— 后端：并行调用 5 家大模型 + Kimi 综合
- `vercel.json` —— 部署配置

## 部署步骤（共 10 分钟）

### 1. 注册 GitHub（有账号跳过）
打开 https://github.com → Sign up → 用邮箱注册，免费。

### 2. 新建代码仓库
- 登录后右上角 "+" → New repository
- 名字填 `five-ai-consult` → 选 Public → Create repository

### 3. 上传这 3 个文件
- 在新仓库页面点 "uploading an existing file"（或 "Add file" → "Upload files"）
- 把 `index.html`、`vercel.json` 直接拖进去
- 再点 "Add file" → "Create new file"，文件名填 `api/consult.py`，把 consult.py 内容粘贴进去（注意必须在 api/ 目录下）
- 每次点 "Commit changes" 确认

### 4. 注册 Vercel 并导入仓库
- 打开 https://vercel.com → Sign Up → **选 "Continue with GitHub"**（用 GitHub 登录）
- 登录后点 "Add New…" → "Project" → 找到 `five-ai-consult` → Import

### 5. 配置环境变量（最重要一步）
在 Import 页面的 "Environment Variables" 区域，逐个添加以下变量（值从本机 `five_ai_keys.txt` 里复制）：

| 变量名 | 值 |
|---|---|
| `SITE_PASSWORD` | 自己定一个网页访问密码，例如 wufang2026 |
| `MOONSHOT_API_KEY` | （从 five_ai_keys.txt 复制） |
| `MOONSHOT_MODEL` | kimi-k3 |
| `OPENAI_API_KEY` | （从 five_ai_keys.txt 复制） |
| `OPENAI_MODEL` | gpt-4o |
| `GEMINI_API_KEY` | （从 five_ai_keys.txt 复制） |
| `GEMINI_MODEL` | gemini-3.6-flash |
| `ARK_API_KEY` | （从 five_ai_keys.txt 复制） |
| `ARK_MODEL` | doubao-seed-2-1-pro-260915 |
| `DASHSCOPE_API_KEY` | （从 five_ai_keys.txt 复制） |
| `DASHSCOPE_MODEL` | qwen-plus |

### 6. 部署
点 "Deploy"。等约 1 分钟出现 🎉 就成功了。

### 7. 手机访问
- 部署成功后页面会显示访问地址，形如 `https://five-ai-consult-xxxx.vercel.app`
- 手机浏览器打开 → 输入第 5 步设的 `SITE_PASSWORD` → 提问 → 等 10–60 秒出结果
- 建议把这个网页"添加到主屏幕"，用起来像 App

## 备注
- **费用**：Vercel 免费额度（Hobby 套餐）对个人使用绰绰有余；5 家大模型按您各账号的 API 调用量计费，与网页无关
- **访问稳定性**：`vercel.app` 域名在国内部分网络下可能访问不稳。如遇打不开，可在 Vercel 项目 Settings → Domains 绑定自己的域名（阿里云/腾讯云便宜的 .top/.xyz 域名约 10 元/年）
- **安全**：Key 只存在 Vercel 服务端环境变量里，网页有密码门；不要把密码告诉别人
- **超时**：免费套餐单次请求最长 60 秒。5 家并行 + Kimi 综合通常在 10–40 秒完成；若某家长期超时会显示"缺席"，不影响其他家
