# Smart Inventory System

A Django-based inventory management system with intelligence features for demand forecasting and waste reduction.

## Structure

- `apps/`: Contains isolated applications (inventory, sales, intelligence).
- `config/`: Project-wide settings and configuration.
- `data/`: Data storage/ingestion.
- `docs/`: Detailed project documentation.

## Installation & Setup

### 1. Prerequisites
- Python 3.10+
- Virtualenv (recommended)

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/AymanRefat/Inventory-Management-DIH-X-AUC-Hackathon.git
cd Inventory-Management-DIH-X-AUC-Hackathon

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Database Setup

```bash
# Apply migrations
python manage.py migrate
```

## 🧠 AI Features

### Demand Forecasting
The system uses Prophet (by Meta) to predict future demand for items based on historical sales data.

**Key Capabilities:**
- **Item-Level Predictions:** Forecast demand for specific products (e.g., "Cappuccino" vs "Latte")
- **Historical Analysis:** Learns from years of sales data
- **Confidence Intervals:** Provides 80% and 95% confidence bounds (best case/worst case)
- **Interactive Dashboard:** visualize trends and future demand

### 4. Data Loading
To populate the database with the provided CSV dataset:

```bash
# Load all data (places, items, orders, order items)
python manage.py load_csv_data --all --batch-size 10000
```
*Note: This processes ~400k orders and ~600k items, so it may take a few minutes.*

### 5. Create Admin User
To access the admin interface:

```bash
python manage.py createsuperuser
```

### 6. Run Server & Dashboard

```bash
python manage.py runserver
```

- **Admin Panel:** http://127.0.0.1:8000/admin/
- **Forecast Dashboard:** http://127.0.0.1:8000/forecast/

## 📊 Using the Dashboard
1. Go to `/forecast/`
2. Select a **Location** (e.g., "Kaffestuen Vesterbro")
3. (Optional) Select a specific **Item** to forecast
4. Click **"Generate Forecast"**
5. View the predicted demand graph and detailed table below
