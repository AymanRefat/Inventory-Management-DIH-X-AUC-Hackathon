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

### 4. Data Loading (Crucial Step)
This project comes with a dataset of 19 CSV files. To populate the database with the initial data (users, products, orders, etc.), run:

```bash
python manage.py load_initial_data
```
*Note: This process may take a few minutes as it processes thousands of order items.*

### 5. Create Admin User
To access the admin interface:

```bash
python manage.py createsuperuser
```

### 6. Run Server

```bash
python manage.py runserver
```

Access the admin panel at: http://127.0.0.1:8000/admin/
