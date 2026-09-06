# GlowGuide: AI-Powered Skin Type Analyzer & Product Recommender

![GlowGuide Banner](Frontend/secnd.png)

## 🌟 What is GlowGuide?

**GlowGuide** is an AI-powered web application that analyzes your skin type from an uploaded image and provides personalized skincare product recommendations. Built by a team of passionate students, making it easy for anyone to find products that truly suit their skin.

---

## 🚀 Features

- **AI Skin Type Detection:** Upload a photo of your skin and get instant analysis (Oily/Dry, Sensitive/Resistant, Pigmented/Non-pigmented).
- **Personalized Recommendations:** Receive tailored product suggestions based on your unique skin type.
- **Modern Frontend:** User-friendly interface built with HTML, CSS, and JavaScript.
- **FastAPI Backend:** Robust Python backend for image processing and ML inference.


## ⚡ Setup Instructions

### 1. **Clone the repository**

```sh
git clone https://github.com/yourusername/glowguide.git
cd glowguide
```

### 2. **Backend Setup (Python, FastAPI)**

  ```sh
  cd SkinTypeClassification
  python -m venv venv
  # Windows:
  venv\Scripts\activate
  # macOS/Linux:
  source venv/bin/activate
  ```
  Use Python 3.10 or 3.11 — TensorFlow 2.13 does not support Python 3.12+.
  ```


  ```sh
  pip install -r requirements.txt
  ```

- **Pull the model files (required — see notice below):**
  ```sh
  git lfs install
  git lfs pull
  ```


  ```sh
uvicorn app.app:app --reload
```
Note: the FastAPI instance lives at `SkinTypeClassification/app/app.py` inside the `app` package,
so the module path is `app.app:app`, not `app:app`. Run this from the `SkinTypeClassification` folder.
  ```
  The backend will be available at `http://localhost:8000`.

### 3. **Frontend Setup**

- Open `Frontend/index.html` in your web browser.
- The frontend will communicate with the backend at `http://localhost:8000`.

---

## ⚡ Important Notice

The three `.h5` model files in `SkinTypeClassification/app/models/` are tracked with **Git LFS**
(~600MB each). If you clone this repo without Git LFS installed, you will get tiny text
"pointer" files instead of the real models, and the server will fail to start.

**Before running the backend:**
```sh
git lfs install
git lfs pull
```

If you don't want to use Git LFS, download the models manually from this link and place them in `SkinTypeClassification/app/models/`:
```sh
  https://drive.google.com/drive/folders/1J-0y8fZgVZcsataaGYGgO3qcSBletV7J?usp=sharing
```
---

## 👨‍💻 Contributors

See [Frontend/about.html](Frontend/about.html) for the full team!

---

## 📸 Image Credits

Sample images used in this project are sourced from [Haut.AI](https://haut.ai/).

---

## 📄 License

This project is for educational purposes.

---

## 💡 Inspiration

What began as a classroom idea is now a platform empowering users to make informed skincare choices. We’re excited to keep improving and expanding GlowGuide!
