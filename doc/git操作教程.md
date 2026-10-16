下面是最基本的 Git 教程，只使用标准命令，主分支统一为 `main`。  
远程名统一用 `origin`，远程地址用你们项目的：

```text
https://github.com/Dninelie/software-engineering.git
```

---

## 1. 首次配置

```bash
git config --global user.name "你的名字"
git config --global user.email "你的邮箱"
```

---

## 2. 获取项目

### 如果本地还没有项目，直接克隆

```bash
git clone https://github.com/Dninelie/software-engineering.git
cd software-engineering
```

### 如果本地已有文件夹，想关联远程

```bash
cd F:\华科\大三上\软件工程\software-engineering
git init
git branch -m main
git remote add origin https://github.com/Dninelie/software-engineering.git
git pull origin main
```

如果 `origin` 已存在但地址不对：

```bash
git remote set-url origin https://github.com/Dninelie/software-engineering.git
```

---

## 3. 查看状态

```bash
git status
git remote -v
git branch -a
git log --oneline
```

---

## 4. 同步远程最新代码

每次开始写代码前，先拉取远程 `main`：

```bash
git pull origin main
```

如果只想下载不合并：

```bash
git fetch origin
git merge origin/main
```

---

## 5. 提交修改

```bash
git add -A
git commit -m "提交说明"
```

只添加指定文件：

```bash
git add 文件名
```

---

## 6. 推送到远程 main

```bash
git push origin main
```

第一次推送可设置上游：

```bash
git push -u origin main
```

之后直接：

```bash
git push
```

---

## 7. 分支与合并

### 创建并切换到新分支

```bash
git checkout -b 分支名
```

### 查看当前分支

```bash
git branch
```

### 在新分支提交

```bash
git add -A
git commit -m "分支修改"
git push -u origin 分支名
```

### 合并回 main

```bash
git checkout main
git pull origin main
git merge 分支名
git push origin main
```

### 删除本地分支

```bash
git branch -d 分支名
```

### 删除远程分支

```bash
git push origin --delete 分支名
```

---

## 8. 解决冲突

合并或拉取时出现冲突：

```bash
git status
```

打开冲突文件，会看到：

```text
<<<<<<< HEAD
当前分支内容
=======
要合并进来的内容
>>>>>>> 分支名
```

手动保留需要的内容，删除 `<<<<<<<`、`=======`、`>>>>>>>`。

然后：

```bash
git add 冲突文件
git commit -m "解决冲突"
git push origin main
```

放弃本次合并：

```bash
git merge --abort
```

---

## 9. 日常最短流程

```bash
git pull origin main
git add -A
git commit -m "修改说明"
git push origin main
```

---

## 10. 常用查看

```bash
git status
git log --oneline
git diff
git remote -v
git branch -a
```

---

## 11. 强制覆盖远程 main（谨慎）

如果确实要用本地完全覆盖远程 `main`：

```bash
git push origin main --force-with-lease
```

如果远程分支有保护，会推送失败，需要管理员先取消保护。

---

## 12. 远程覆盖本地（谨慎）

```bash
git fetch origin
git reset --hard origin/main
```

这会丢弃本地所有未提交修改。

---

以上全部是 Git 标准命令，没有自定义别名或脚本。  
只要记住日常四步：**pull → add → commit → push**。