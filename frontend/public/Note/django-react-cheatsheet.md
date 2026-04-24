# 🐍 + ⚛️ Django + React Cheatsheet
> Explained like you're 3 years old 🍼 — Everything you need in one place!

---

# 🐍 DJANGO CHEATSHEET

---

## 🛒 Installation — "Buy your ingredients first"

```powershell
# 🏠 Build a clean room just for your project (no mess with other projects!)
python -m venv venv

# 🚪 Walk INTO that room (Windows) — you'll see (venv) appear
venv\Scripts\activate

# 🚪 Walk INTO that room (Mac/Linux)
source venv/bin/activate

# 🛍️ Buy Django + its helpers. Like groceries but for code!
pip install django djangorestframework django-cors-headers python-dotenv

# 📝 Write down EVERYTHING you bought into a list file
pip freeze > requirements.txt
```

---

## 🏗️ Create Project & App — "Build the house"

```powershell
# 🏠 Build the foundation of your house. The dot means "right here!"
django-admin startproject core .

# 🛏️ Add a room called 'tasks' to your house
python manage.py startapp tasks
```

> 💡 `core` = the house foundation (settings, URLs)
> 💡 `tasks` = a room inside the house (your actual app logic)

---

## ⚙️ Daily Commands — "Your TV remote"

```powershell
# ▶️ Turn ON your Django server → http://localhost:8000
python manage.py runserver

# 📋 "Hey Django, I changed my database blueprint, write it down!"
python manage.py makemigrations

# ✅ "Okay now actually BUILD those changes in the database!"
python manage.py migrate

# 👑 Create an admin account so you can log into /admin
python manage.py createsuperuser

# 🧪 Open a Python playground to test your code live
python manage.py shell
```

> ⚠️ Always run `makemigrations` THEN `migrate` together after editing `models.py`!

---

## 📁 Important Files — "The rooms you'll visit every day"

| File | Emoji | What it does (simple!) |
|------|-------|------------------------|
| `settings.py` | 🧠 | The brain — controls everything: apps, database, CORS, secrets |
| `urls.py` | 🗺️ | The map — tells Django what URL goes to what page/API |
| `models.py` | 🗃️ | The blueprint — describes what your database table looks like |
| `serializers.py` | 🔄 | The translator — converts database data into JSON for React |
| `views.py` | 👨‍🍳 | The chef — receives requests and cooks up responses |
| `.env` | 🔐 | Your secret diary — passwords & keys. NEVER push to GitHub! |
| `.env.example` | 📋 | Blank template of `.env` — safe to share with teammates |
| `requirements.txt` | 🛍️ | Shopping list of everything you installed |

---

## ⚙️ settings.py Essentials — "Must-haves checklist"

```python
# 1️⃣ Always add these to INSTALLED_APPS
INSTALLED_APPS = [
    ...
    'rest_framework',   # lets Django act as an API
    'corsheaders',      # lets React talk to Django
    'tasks',            # YOUR app
]

# 2️⃣ corsheaders MUST be at the TOP of MIDDLEWARE
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # ← FIRST!
    ...
]

# 3️⃣ Tell Django which React ports are allowed
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vite
    "http://localhost:3000",  # Create React App
]

# 4️⃣ Load secrets from .env instead of hardcoding them
from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.environ.get('SECRET_KEY')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
```

---

## 🔐 .env File — "Your secret diary"

```env
# backend/.env  ← 🔴 NEVER share this / push to GitHub!
SECRET_KEY=your-super-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

```env
# backend/.env.example  ← ✅ Share this with teammates (no real values!)
SECRET_KEY=
DEBUG=
ALLOWED_HOSTS=
```

---

## 🏗️ Building the API — "Step by step"

### Step 1 — Model (the blueprint)
```python
# tasks/models.py
from django.db import models

class Task(models.Model):
    title      = models.CharField(max_length=200)  # a text field
    completed  = models.BooleanField(default=False) # true or false
    created_at = models.DateTimeField(auto_now_add=True)
```

### Step 2 — Serializer (the translator)
```python
# tasks/serializers.py
from rest_framework import serializers
from .models import Task

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'  # include every field
```

### Step 3 — View (the chef)
```python
# tasks/views.py
from rest_framework import viewsets
from .models import Task
from .serializers import TaskSerializer

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
```

### Step 4 — URLs (the map)
```python
# tasks/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskViewSet

router = DefaultRouter()
router.register(r'tasks', TaskViewSet)

urlpatterns = [path('', include(router.urls))]
```

```python
# core/urls.py
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('tasks.urls')),  # all API routes at /api/
]
```

### ✅ Auto-generated API Endpoints

| Method | URL | What it does |
|--------|-----|--------------|
| `GET` | `/api/tasks/` | 📋 Get ALL tasks |
| `POST` | `/api/tasks/` | ➕ Create a NEW task |
| `GET` | `/api/tasks/1/` | 🔍 Get task #1 only |
| `PUT` | `/api/tasks/1/` | ✏️ Update task #1 |
| `DELETE` | `/api/tasks/1/` | 🗑️ Delete task #1 |

---
---

# ⚛️ REACT CHEATSHEET

---

## 🛒 Installation — "Set up your toy box"

```powershell
# 📦 Create a brand new React app with Vite (the fast one!)
npm create vite@latest . -- --template react

# 🛍️ Download all the packages the app needs
npm install

# 📡 Install Axios — the tool that lets React TALK to Django
npm install axios
```

---

## ⚙️ Daily Commands — "Your toy remote"

```powershell
# ▶️ Turn ON your React app → http://localhost:5173
npm run dev

# 📦 Pack your app into a small box, ready for the internet
npm run build

# ➕ Add a new package/tool
npm install package-name

# ➖ Remove a package you no longer need
npm uninstall package-name
```

---

## 📁 Important Files — "The toy box rooms"

| File | Emoji | What it does (simple!) |
|------|-------|------------------------|
| `src/main.jsx` | 🚪 | The front door — where your React app starts |
| `src/App.jsx` | 🏠 | The living room — your main component |
| `src/api.js` | 📡 | Create this yourself! It's your phone to call Django |
| `src/components/` | 🧩 | Folder for your reusable building blocks |
| `.env` | 🔐 | React's secrets. Variables MUST start with `VITE_`! |
| `vite.config.js` | ⚙️ | Settings for Vite — you rarely touch this |
| `package.json` | 📝 | List of all packages your React app uses |

---

## ⚛️ Core Concepts — "The magic tricks"

### useState — "The sticky note"
```jsx
// 🧠 Remember things! Like a sticky note your component can update
import { useState } from 'react'

const [count, setCount] = useState(0)  // start at 0

<button onClick={() => setCount(count + 1)}>
  Count is {count}
</button>
```
> 💡 `count` = read the note. `setCount()` = write on the note.

---

### useEffect — "The alarm clock"
```jsx
// ⏰ "When the page loads, do this!" — perfect for fetching data
import { useEffect } from 'react'

useEffect(() => {
  // this runs when the page loads
  fetchDataFromDjango()
}, []) // ← the empty [] means "only run once on load"
```

---

### props — "Passing gifts"
```jsx
// 📨 Pass data from parent to child component
function Parent() {
  return <Child name="John" age={25} />
}

function Child({ name, age }) {
  return <p>{name} is {age} years old</p>
}
```
> 💡 Parent gives a gift 🎁 (props). Child unwraps and uses it.

---

### map() — "The copy machine"
```jsx
// 🔁 Loop through a list and display each item
const tasks = ['Buy milk', 'Walk dog', 'Code React']

tasks.map((task, index) => (
  <div key={index}>{task}</div>
))
```
> 💡 Always add `key=` when using map — React needs it to track items!

---

## 📡 Talking to Django — "Making phone calls"

### Step 1 — Create your Django phone (`src/api.js`)
```js
// 📞 Create once, import everywhere!
import axios from 'axios'

export default axios.create({
  baseURL: 'http://localhost:8000/api'  // ← Django lives here
})
```

### Step 2 — Use it in your components
```jsx
import { useState, useEffect } from 'react'
import API from './api'

function Tasks() {
  const [tasks, setTasks] = useState([])

  // 📥 GET — "Give me all tasks" (runs on page load)
  useEffect(() => {
    API.get('/tasks/')
      .then(res => setTasks(res.data))
  }, [])

  // 📤 POST — "Save this new task"
  const addTask = async () => {
    const res = await API.post('/tasks/', { title: 'New Task', completed: false })
    setTasks(prev => [...prev, res.data])
  }

  // 🗑️ DELETE — "Remove this task"
  const deleteTask = async (id) => {
    await API.delete(`/tasks/${id}/`)
    setTasks(prev => prev.filter(t => t.id !== id))
  }

  return (
    <div>
      <button onClick={addTask}>Add Task</button>
      {tasks.map(task => (
        <div key={task.id}>
          {task.title}
          <button onClick={() => deleteTask(task.id)}>Delete</button>
        </div>
      ))}
    </div>
  )
}
```

---
---

# 🤝 DJANGO + REACT TOGETHER

---

## 🚀 Running Both Servers

```powershell
# ─── Terminal 1 — Django Backend 🐍 ───
cd backend/app
venv\Scripts\activate
python manage.py runserver
# → Running at http://localhost:8000

# ─── Terminal 2 — React Frontend ⚛️ ───
cd frontend
npm run dev
# → Running at http://localhost:5173
```

> 💡 You need TWO terminals open at the same time! One for each!

---

## 📁 Full Project Structure

```
my-project/
│
├── backend/
│   ├── app/                  ← Django lives here
│   │   ├── core/             ← settings.py, urls.py (the brain)
│   │   ├── tasks/            ← your app (models, views, urls)
│   │   ├── .env              ← 🔐 secret diary (NEVER share!)
│   │   ├── .env.example      ← 📋 blank template (safe to share)
│   │   ├── .gitignore        ← 🛡️ protects .env from GitHub
│   │   └── manage.py         ← Django's remote control
│   ├── venv/                 ← your clean room
│   └── requirements.txt      ← your shopping list
│
└── frontend/
    ├── src/
    │   ├── api.js             ← 📡 your Django phone
    │   ├── App.jsx            ← 🏠 main component
    │   └── components/        ← 🧩 reusable pieces
    ├── .env                   ← React secrets (VITE_ prefix!)
    └── package.json           ← React's shopping list
```

---

## 🚨 Most Common Mistakes — "Don't step on these!"

| ❌ Mistake | ✅ Fix |
|-----------|--------|
| Forgot `corsheaders` in `INSTALLED_APPS` | React gets BLOCKED. Add `'corsheaders'` to the list! |
| `corsheaders` not at TOP of `MIDDLEWARE` | Move it to be the very FIRST item! |
| Forgot `makemigrations` + `migrate` | Your database changes won't exist. Always run BOTH! |
| Pushed `.env` to GitHub | Your secret key is public 😱 Add `.env` to `.gitignore`! |
| Wrong port in React's `api.js` | Django = `:8000`, React = `:5173`. Don't mix them up! |
| Forgot to activate `venv` | Packages won't be found. Always activate before working! |
| App not in `INSTALLED_APPS` | Django doesn't know your app exists. Register it! |

---

## 🧠 The Big Picture — "How it all fits"

```
👤 User clicks button in React (port 5173)
        ↓
⚛️  React sends request via Axios → http://localhost:8000/api/tasks/
        ↓
🐍  Django receives it, checks urls.py
        ↓
👨‍🍳  views.py (the chef) handles the request
        ↓
🗃️  models.py talks to the database
        ↓
🔄  serializers.py converts data to JSON
        ↓
📦  Django sends JSON response back to React
        ↓
⚛️  React updates the screen with useState()
        ↓
👤 User sees the result! 🎉
```

---

*Happy coding! 🚀 Remember: mistakes are how you learn. Break things, fix them, repeat!*
