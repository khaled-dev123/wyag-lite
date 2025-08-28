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

## 🎯 Goals

- Learn Git internals by coding them step by step

- Provide a reference for students & enthusiasts

- Create a playground for experimenting with version control

## 🤝 Contributing

Contributions, issues, and pull requests are welcome!
If you’re also studying Git internals, feel free to fork and extend the project.

## 📜 License

MIT License – free to use, modify, and distribute.

---

## 🚀 Getting Started  

### 🔧 Requirements  
- Python **3.10+**  
- No external libraries (only Python standard library)

### ▶️ Usage  
Clone the repository and run the `wyag.py` script:

```bash
git clone https://github.com/khaled-dev123/wyag-lite.git
cd git

# Initialize a new repository
python3 wyag.py init myrepo


