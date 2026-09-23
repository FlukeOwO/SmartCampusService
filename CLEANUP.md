# Repository Cleanup Guide

## 🧹 ปัญหาที่แก้ไข

### 1. ไฟล์ขยะจาก Refactoring

ไฟล์เหล่านี้ถูกย้ายไปโครงสร้างใหม่แล้ว แต่ยังค้างอยู่:

- ❌ `backend/app/database.py` → ✅ `backend/app/core/database.py`
- ❌ `backend/app/api/` → ✅ `backend/app/modules/`
- ❌ `backend/app/services/` → ✅ `backend/app/modules/*/service.py`
- ❌ `backend/app/crud/` → ✅ `backend/app/modules/*/service.py`

### 2. ไฟล์ที่ถูก Track ผิด

ไฟล์เหล่านี้อยู่ใน `.gitignore` แต่ถูก commit ไปก่อนหน้านี้:

- ❌ `backend/venv/` - Python virtual environment (Windows binaries)
- ❌ `frontend/node_modules/` - Node.js dependencies (platform-specific)
- ❌ `backend/campus.db` - SQLite database (ไม่ใช้แล้ว, เปลี่ยนเป็น PostgreSQL)

### 3. ปัญหาที่เกิด

1. **Cross-platform incompatibility**
   - `venv/` และ `node_modules/` มี binaries ที่เฉพาะ platform
   - บน Windows มี `.node`, `.exe` ที่ใช้บน Mac/Linux ไม่ได้

2. **Confusion**
   - มีโค้ดเก่าและใหม่ปนกัน
   - ไม่รู้ว่าอันไหนเป็นของจริง

3. **Repository bloat**
   - ขนาด repo ใหญ่เกินความจำเป็น
   - Clone ช้า

---

## ✅ วิธีแก้ไข

### Option 1: ใช้ Script อัตโนมัติ (แนะนำ)

#### Windows (PowerShell):
```powershell
.\git-cleanup.ps1
```

#### Linux/Mac:
```bash
chmod +x .git-cleanup.sh
./.git-cleanup.sh
```

#### หรือใช้ Makefile:
```bash
make git-cleanup
```

### Option 2: Manual Cleanup

```bash
# 1. Remove from git tracking (but keep files locally)
git rm -r --cached backend/venv/
git rm -r --cached frontend/node_modules/
git rm --cached backend/campus.db
git rm --cached backend/*.db

# 2. Remove old refactored files
git rm --cached backend/app/database.py
git rm -r --cached backend/app/api/
git rm -r --cached backend/app/services/
git rm -r --cached backend/app/crud/

# 3. Check status
git status

# 4. Commit changes
git commit -m "chore: remove tracked files that should be ignored"

# 5. Push to remote
git push
```

---

## 📋 Verification

หลังจาก cleanup ตรวจสอบว่าสะอาดแล้ว:

```bash
# ไม่ควรเห็น venv/, node_modules/, *.db
git ls-files | grep -E "(venv|node_modules|\.db$)"

# ไม่ควรเห็น app/api, app/services, app/crud
git ls-files | grep -E "app/(api|services|crud)/"

# ตรวจสอบ .gitignore ทำงานถูกต้อง
git status  # ควรไม่เห็นไฟล์ที่ ignore
```

---

## 🎯 Best Practices

### 1. สร้าง .gitignore ก่อน commit อะไรก็ตาม

```bash
# เมื่อเริ่มโปรเจกต์ใหม่
cp .gitignore.example .gitignore
git add .gitignore
git commit -m "chore: add gitignore"
```

### 2. ใช้ global gitignore

สร้างไฟล์ `~/.gitignore_global`:

```
# IDEs
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Environment
.env
.env.local
```

จากนั้น config git:

```bash
git config --global core.excludesfile ~/.gitignore_global
```

### 3. ตรวจสอบก่อน commit

```bash
# ดูว่า stage อะไรบ้าง
git status

# ดูว่ามีไฟล์ใหญ่หรือ sensitive files หรือไม่
git diff --cached --stat

# Unstage ถ้าเจอไฟล์ที่ไม่ควร commit
git reset HEAD <file>
```

### 4. ใช้ pre-commit hooks

สร้าง `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Block commits that include sensitive files

# Check for files that shouldn't be committed
FORBIDDEN_FILES=$(git diff --cached --name-only | grep -E "(venv/|node_modules/|\.db$|\.env$)")

if [ -n "$FORBIDDEN_FILES" ]; then
    echo "❌ Error: You're trying to commit files that should be ignored:"
    echo "$FORBIDDEN_FILES"
    echo ""
    echo "Please unstage these files:"
    echo "  git reset HEAD <file>"
    exit 1
fi
```

---

## 🔧 Recovery

ถ้าลบไฟล์ผิดพลาด:

```bash
# Restore from last commit
git checkout HEAD -- <file>

# Restore working directory files
git restore <file>

# Get file from specific commit
git checkout <commit-hash> -- <file>
```

---

## 📚 Additional Resources

- [GitHub: Removing sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
- [Git: gitignore patterns](https://git-scm.com/docs/gitignore)
- [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/) - สำหรับลบไฟล์ใหญ่จาก history

---

## ⚠️ Important Notes

1. **Local files จะไม่หาย** - `git rm --cached` ลบเฉพาะจาก git tracking ไฟล์ยังอยู่ใน working directory
2. **Collaborators ต้อง pull ใหม่** - หลัง push cleanup แล้ว คนอื่นต้อง `git pull`
3. **History ยังมีไฟล์อยู่** - ถ้าต้องการลบจาก history ทั้งหมด ใช้ `git filter-branch` หรือ BFG (ระวัง!)

---

## ✅ Checklist

- [ ] Run cleanup script (`git-cleanup.ps1` หรือ `.git-cleanup.sh`)
- [ ] Review changes (`git status`)
- [ ] Commit (`git commit -m "chore: remove tracked files that should be ignored"`)
- [ ] Verify (`git ls-files | grep -E "(venv|node_modules)"` should return nothing)
- [ ] Push to remote (if applicable)
- [ ] Update team members

---

**Status**: Repository cleaned ✨
