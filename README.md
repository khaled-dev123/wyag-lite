# 🌀 Wyag Lite  
*A minimal Git reimplementation in Python*

---

## 📌 Overview  
**Wyag Lite** (Write Yourself A Git - Lite) is a simplified reimplementation of Git written entirely in Python.  
It’s designed as an **educational project** to help developers understand the internal mechanics of Git:  
repositories, objects, commits, trees, and more — by rebuilding them from scratch.  

---

## ✨ Features  
- 📂 Initialize a new repository (`wyag init`)  
- 📝 Add and commit files *(Work in Progress)*  
- 🔍 Inspect objects (`cat-file`, `ls-tree`, etc.)  
- 🏷️ Manage refs and tags  
- ✅ Basic status and log commands  

---

## 🚀 Getting Started  

### 🔧 Requirements  
- Python **3.10+**  
- No external libraries (only Python standard library)

### ▶️ Usage  
Clone the repository and run the `wyag.py` script:

```bash
git clone https://github.com/your-username/wyag-lite.git
cd wyag-lite

# Initialize a new repository
python3 wyag.py init myrepo
