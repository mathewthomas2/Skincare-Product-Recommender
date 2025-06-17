# Skincare Recommendation System

An AI-powered web application that analyzes skin types and recommends personalized skincare products.

## Project Structure
```bash
.
├── Frontend/          # React-based web interface
└── SkinTypeClassification/          # FastAPI ML service with skin analysis
```

## Setup Instructions

### Backend
```bash
# Navigate to Backend directory
cd SkinTypeClassification

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Frontend
```bash
# Navigate to Frontend directory
cd Frontend

# Open index.html in a browser or use a local server
# For example, using Python's built-in server:
python -m http.server 8080
```

## Running the Application

1. Start the Backend server:
```bash
cd Backend
uvicorn app.app:app --host 0.0.0.0 --port 8000
```

2. Access the Frontend:
- Open `Frontend/index.html` in your browser
- Or navigate to `http://localhost:8080` if using a local server

## Repository Structure
```
├── Frontend/
│   ├── index.html
│   ├── script.js
│   └── style.css
├── SkinTypeClassification/
│   ├── app/
│   │   ├── models/
│   │   ├── app.py
│   │   └── preprocess_image.py
│   ├── requirements.txt
│   └── setup.py
└── README.md
```

## ML Models
The machine learning models are not included in the repository due to size constraints. Download them from [provide_link_here] and place them in:
```
Backend/app/models/
```

Required models:
- pigmented_nonpigmented_model.h5
- oily_dry_model.h5
- sensitive_resistant_model.h5
