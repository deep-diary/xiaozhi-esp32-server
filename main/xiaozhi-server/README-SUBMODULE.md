# 子模块管理指南

本文档说明如何在 demo 项目中使用 Git Submodule 管理项目A和项目B。

## 项目结构

```
my-demo-project/
├── libs/
│   ├── xiaozhi-esp32-server/    # 项目A（子模块）
│   └── xiaozhi-other/           # 项目B（子模块）
├── src/                          # 你的自定义代码
├── .gitmodules                   # 子模块配置文件
├── setup-submodules.sh          # 初始化脚本
└── update-submodules.sh         # 更新脚本
```

## 初始设置

### 1. 克隆包含子模块的项目

```bash
# 克隆demo项目（包含子模块）
git clone --recurse-submodules <你的demo项目URL> my-demo-project
cd my-demo-project

# 或者如果已经克隆了，初始化子模块
git submodule update --init --recursive
```

### 2. 设置本地修改分支

```bash
# 运行初始化脚本
chmod +x setup-submodules.sh
./setup-submodules.sh
```

这会为每个子模块创建 `local-customizations` 分支，用于保存你的本地修改。

## 日常开发流程

### 修改子模块代码

```bash
# 1. 进入项目A子模块
cd libs/xiaozhi-esp32-server

# 2. 确保在本地修改分支
git checkout local-customizations

# 3. 进行你的修改
vim core/some_file.py

# 4. 提交到本地分支（不会推送到原始仓库）
git add .
git commit -m "本地修改：添加xxx功能"

# 5. 返回demo项目根目录
cd ../..
```

### 提交demo项目

```bash
# 在demo项目根目录
git add libs/xiaozhi-esp32-server  # 提交子模块的引用
git commit -m "更新项目A的本地修改"
git push origin main
```

## 定期更新上游代码

### 方法1：使用更新脚本（推荐）

```bash
chmod +x update-submodules.sh
./update-submodules.sh
```

脚本会：
1. 检查每个子模块的上游更新
2. 询问是否合并
3. 自动处理合并冲突提示
4. 更新demo项目中的子模块引用

### 方法2：手动更新

```bash
# 更新项目A
cd libs/xiaozhi-esp32-server
git checkout local-customizations
git fetch origin
git merge origin/main  # 合并上游更新
# 如果有冲突，解决后：
# git add . && git commit
cd ../..

# 更新项目B
cd libs/xiaozhi-other
git checkout local-customizations
git fetch origin
git merge origin/main
cd ../..

# 更新demo项目引用
git add libs/
git commit -m "同步上游更新"
```

## 处理合并冲突

当上游更新与你的本地修改冲突时：

```bash
cd libs/xiaozhi-esp32-server
git status  # 查看冲突文件

# 手动解决冲突
vim <冲突文件>

# 标记为已解决
git add <冲突文件>
git commit -m "解决合并冲突"
cd ../..
```

## 重要说明

### ✅ 优点

1. **保持更新**：可以定期同步上游最新代码
2. **本地修改**：你的修改保存在本地分支，不会影响原始项目
3. **版本控制**：所有修改都有完整的Git历史记录
4. **团队协作**：团队成员可以共享你的demo项目（包括子模块的本地修改）

### ⚠️ 注意事项

1. **不推送到原始仓库**：`local-customizations` 分支只存在于你的demo项目中，不会推送到项目A/B的原始仓库
2. **冲突处理**：定期更新时可能需要解决合并冲突
3. **子模块引用**：demo项目只保存子模块的commit引用，不保存实际代码

### 🔒 保护原始项目

你的操作**绝对不会**影响原始项目A和B，因为：
- 你的修改在本地分支中
- 你没有原始仓库的推送权限（除非你是维护者）
- 即使有权限，你也没有推送到原始仓库

## 常见问题

### Q: 如何查看子模块的修改？

```bash
cd libs/xiaozhi-esp32-server
git log local-customizations --oneline
git diff origin/main..local-customizations
```

### Q: 如何回退子模块的修改？

```bash
cd libs/xiaozhi-esp32-server
git checkout local-customizations
git reset --hard HEAD~1  # 回退最后一次提交
```

### Q: 如何完全重置子模块到上游版本？

```bash
cd libs/xiaozhi-esp32-server
git checkout local-customizations
git reset --hard origin/main
```

### Q: 团队成员如何获取子模块的本地修改？

```bash
# 克隆项目
git clone --recurse-submodules <demo项目URL>

# 切换到本地修改分支
cd libs/xiaozhi-esp32-server
git checkout local-customizations
cd ../..
```

## 最佳实践

1. **定期更新**：建议每周或每月更新一次上游代码
2. **提交信息**：为本地修改写清晰的提交信息
3. **最小化修改**：尽量少修改子模块代码，优先使用 `custom/` 目录扩展功能
4. **备份**：重要修改前先备份或创建tag

