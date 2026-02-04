# AI Approach Strategy for FreshFlow Inventory Management

## Executive Summary

This document outlines comprehensive AI/ML approaches to solve the inventory management challenges faced by restaurants and grocery stores. Based on the available data structure and business requirements, we propose a multi-model approach combining time series forecasting, optimization algorithms, and recommendation systems.

---

## Problem Statement

Restaurant and grocery owners face critical challenges:
- **Over-stocking**: Leads to waste and expired inventory, reducing profits
- **Under-stocking**: Causes stockouts, lost revenue, and customer frustration
- **Root Cause**: Poor demand forecasting and lack of intelligent inventory systems

**Solution**: Implement AI-driven systems that replace gut instinct with data-driven predictions and optimizations.

---

## Available Data Assets

### Dimensional Data (~235K records)
- **88,921 Items**: Menu items with pricing, descriptions
- **21,102 Add-ons**: Modifiers and customizations
- **2,091 Places**: Restaurant/store locations with operational details
- **22,956 Users**: Customer profiles with preferences
- **642 Campaigns**: Marketing promotions and discounts

### Transactional Data (~2.45M records)
- **400,009 Orders**: Sales transactions with timestamps, channels, and payment methods
- **1,999,341 Order Items**: Detailed line items with quantities and pricing
- **52,916 Cash Balances**: Shift-level financial data
- **95,436 Most Ordered**: Aggregated popularity metrics

### Key Features Available
- Temporal data: Order timestamps (created, updated, promise_time)
- Location data: Place IDs, delivery locations
- Customer behavior: User IDs, order channels (App, Counter), order types (Takeaway, Dine-in)
- Item relationships: Bill of Materials (recipes), SKUs, stock categories
- Batch tracking: Expiration dates, received dates (FIFO/FEFO support)

---

## AI Approaches by Business Question

### 1. Demand Forecasting: "How do we accurately predict daily, weekly, and monthly demand?"

#### Approach A: Time Series Forecasting with SARIMA/Prophet
**Methodology:**
- Use Facebook Prophet or SARIMA (Seasonal ARIMA) for univariate forecasting
- Model demand patterns at multiple granularities:
  - Item-level: Predict demand for each menu item
  - Category-level: Forecast by stock categories
  - Place-level: Location-specific predictions

**Features:**
- Historical order quantities from `fct_order_items`
- Temporal features: day of week, hour of day, month, seasonality
- Holiday indicators and special events

**Implementation Steps:**
1. Aggregate historical sales data by item/place/time
2. Handle missing data and outliers
3. Decompose time series into trend, seasonal, and residual components
4. Train separate models for different forecast horizons (daily/weekly/monthly)
5. Evaluate with MAPE, RMSE, and MAE metrics

**Pros:** Easy to implement, interpretable, handles seasonality well
**Cons:** Limited in capturing complex patterns, doesn't handle external factors directly

---

#### Approach B: Machine Learning with XGBoost/LightGBM
**Methodology:**
- Gradient boosting machines for multivariate demand forecasting
- Captures non-linear relationships and feature interactions

**Feature Engineering:**
```python
# Temporal Features
- day_of_week, is_weekend, is_holiday
- hour_of_day, day_of_month, week_of_year
- time_since_last_order

# Lag Features
- sales_lag_1_day, sales_lag_7_days, sales_lag_30_days
- rolling_mean_7d, rolling_std_7d
- exponential_moving_average

# Item Features
- item_price, item_category
- avg_order_quantity, popularity_rank
- is_new_item (days since first order)

# Place Features  
- place_location, place_type
- avg_daily_orders, place_capacity

# Customer Features
- customer_segment, order_frequency
- avg_order_value, preferred_channel

# External Features (if available)
- weather_temperature, weather_condition
- local_events, nearby_competitor_activity
```

**Implementation Steps:**
1. Create rolling time windows for training (e.g., use 90 days to predict next 7 days)
2. Engineer features capturing temporal patterns, lags, and trends
3. Split data chronologically (train/validation/test)
4. Train XGBoost model with cross-validation
5. Feature importance analysis to understand key drivers

**Pros:** Captures complex patterns, handles mixed data types, excellent performance
**Cons:** Requires more feature engineering, less interpretable than Prophet

---

#### Approach C: Deep Learning with LSTM/Transformer
**Methodology:**
- Long Short-Term Memory (LSTM) networks or Temporal Fusion Transformers
- Ideal for capturing long-term dependencies and multiple seasonal patterns

**Architecture:**
- Input: Sequence of historical sales (e.g., 90 days)
- Output: Future demand predictions (e.g., next 30 days)
- Multi-head attention for multiple items/places simultaneously

**Features:**
- Time series embeddings for items and places
- Temporal encoding (cyclical features for time)
- Static features (item properties, place characteristics)

**Implementation Steps:**
1. Prepare sequences with sliding windows
2. Normalize data (min-max or z-score)
3. Design encoder-decoder architecture or use PyTorch Forecasting
4. Train with teacher forcing and early stopping
5. Ensemble multiple models for robustness

**Pros:** Best for complex patterns, handles multiple seasonality, can predict multiple items simultaneously
**Cons:** Requires more data, computationally expensive, harder to interpret

**Recommended:** Start with Approach B (XGBoost), then consider A (Prophet) for simplicity or C (LSTM) for scale

---

### 2. Prep Optimization: "What prep quantities should kitchens prepare to minimize waste?"

#### Approach: Stochastic Optimization with Demand Uncertainty

**Methodology:**
- Combine demand forecasts with Bill of Materials (BOM) data
- Optimize prep quantities considering:
  - Predicted demand with confidence intervals
  - Ingredient expiration dates (from `Batch` model)
  - Preparation time and shelf life
  - Cost of waste vs. cost of stockout

**Mathematical Formulation:**
```
Minimize: 
  Cost_waste × E[excess_inventory] + Cost_stockout × E[shortfall]

Subject to:
  - Prepared_quantity ≥ Predicted_demand_lower_bound
  - Prepared_quantity ≤ Available_inventory
  - Expiration_constraints (FIFO/FEFO)
  - Kitchen_capacity_constraints
```

**Implementation Steps:**
1. Get demand forecast with prediction intervals (80%, 95%)
2. Query BOM data to calculate required raw materials
3. Check batch expiration dates and quantities
4. Solve optimization problem using:
   - Linear Programming (if linear costs)
   - Dynamic Programming (for multi-period decisions)
   - Monte Carlo simulation (for uncertainty)
5. Generate prep recommendations with safety stock levels

**Features:**
- Demand predictions from Question 1
- `BillOfMaterial.quantity`: Recipe requirements
- `Batch.expiration_date`: Perishability constraints
- `SKU.low_stock_threshold`: Safety stock levels
- Historical waste data (if available)

**Output:**
- Daily prep lists by SKU
- Optimal order quantities from suppliers
- Alerts for items at risk of expiration
- Expected waste reduction metrics

---

### 3. Expiration Management: "How can we prioritize inventory based on expiration dates?"

#### Approach: FEFO (First-Expired, First-Out) with Priority Scoring

**Methodology:**
- Implement intelligent batch tracking system
- Score each batch based on multiple factors
- Recommend actions: use, discount, or dispose

**Priority Score Calculation:**
```python
Priority_Score = (
    W1 × Days_until_expiration_normalized +
    W2 × Quantity_on_hand_normalized +
    W3 × (1 - Demand_forecast_normalized) +
    W4 × Unit_cost_normalized
)

Where higher score = more urgent to use
```

**Implementation Steps:**
1. Query all `Batch` records with quantities > 0
2. Calculate days until expiration for each batch
3. Get demand forecast for the parent SKU
4. Compute priority scores
5. Generate prioritized action list:
   - **High Priority (< 3 days)**: Immediate promotion or use
   - **Medium Priority (3-7 days)**: Feature in menu, bundle offers
   - **Low Priority (> 7 days)**: Normal operations

**Machine Learning Enhancement:**
- Train classification model to predict "will expire unused" (binary)
- Features: days_to_expiration, current_stock, recent_demand, seasonality, price
- Use predictions to trigger proactive interventions

**Output:**
- Daily prioritized batch report sorted by urgency
- Automated alerts for expiration risks
- Integration with menu planning and promotion systems

---

### 4. Dynamic Pricing & Promotions: "What promotions or bundles can move near-expired items profitably?"

#### Approach A: Reinforcement Learning for Dynamic Pricing

**Methodology:**
- Use Multi-Armed Bandit or Deep Q-Learning
- Learn optimal discount strategies based on item characteristics and time to expiration

**State Space:**
- Days until expiration
- Current inventory level
- Recent demand rate
- Day of week, time of day
- Item category and price point

**Action Space:**
- Discount levels: 0%, 10%, 20%, 30%, 40%, 50%
- Promotion types: BOGO, bundle, flash sale

**Reward Function:**
```python
Reward = (
    Revenue_from_sale - 
    Opportunity_cost_of_discount - 
    Waste_cost_if_expired
)
```

**Implementation:**
- Start with epsilon-greedy exploration
- Use Thompson Sampling for balancing exploration/exploitation
- Train on historical campaign data from `fct_campaigns` and `dim_campaigns`

---

#### Approach B: Recommendation System for Bundles

**Methodology:**
- Association rule mining (Apriori, FP-Growth) to find frequently bought together items
- Optimize bundles that include near-expired items with popular items

**Algorithm:**
1. Mine association rules from `fct_order_items`:
   ```
   IF item_A AND item_B THEN item_C (support=0.2, confidence=0.8, lift=2.5)
   ```
2. Filter rules where:
   - Consequent (item_C) has near-expiration inventory
   - Antecedent (items A, B) have high demand
   - Lift > 1.5 (strong association)
3. Create bundle with attractive pricing:
   ```
   Bundle_price = (Price_A + Price_B + Price_C) × (1 - discount)
   Where discount maximizes: Revenue × Probability_of_purchase
   ```

**Implementation Steps:**
1. Aggregate co-occurrence matrix from order items
2. Apply Apriori algorithm with min_support=0.1, min_confidence=0.6
3. For each item with expiration risk, find top 5 associated items
4. Calculate optimal bundle price using elasticity estimates
5. A/B test bundles and measure incremental revenue

**Advanced:** Use collaborative filtering to personalize bundle recommendations by customer segment

---

### 5. External Factors: "How do external factors (weather, holidays, weekends) impact sales?"

#### Approach: Feature Importance Analysis + Causal Inference

**Methodology Phase 1: Exploratory Analysis**
1. **Temporal Patterns:**
   - Extract weekend vs. weekday effects from `fct_orders.created`
   - Identify seasonality (summer vs. winter)
   - Detect holiday impacts using calendar data

2. **Channel Analysis:**
   - Compare demand across channels (App, Counter) from `fct_orders.channel`
   - Analyze order type effects (Takeaway, Dine-in)

3. **Feature Engineering:**
   ```python
   # Weekend effect
   is_weekend = (day_of_week >= 5)
   
   # Holiday indicator
   is_holiday = day in [holiday_calendar]
   
   # Weather (if external API available)
   temperature, precipitation, weather_condition
   
   # Special events
   is_payday = (day_of_month in [1, 15, 30])
   is_promo_period = (date in campaign_dates)
   ```

**Methodology Phase 2: Causal Impact**
- Use Google's CausalImpact library or Facebook's Prophet
- Measure the incremental effect of specific events
- Example: "Did the holiday promotion increase sales beyond normal holiday lift?"

**Implementation:**
1. Collect external data sources:
   - Weather API (OpenWeatherMap, WeatherAPI)
   - Holiday calendar
   - Local events calendar
2. Join external data with orders on date/place
3. Train XGBoost with external features and analyze SHAP values
4. Identify top 10 impactful features
5. Create "playbooks" for different scenarios:
   - Rainy day: +20% soup demand
   - Weekend: +35% brunch items
   - Holiday: +50% overall, -30% delivery

**Output:**
- External factor impact report
- Conditional forecasting models: "If rainy weekend, then forecast X"
- Scenario planning tools for managers

---

## Recommended Implementation Roadmap

### Phase 1: Foundation (Weeks 1-3)
**Goal:** Basic demand forecasting and data infrastructure

1. **Data Quality & EDA**
   - Clean and validate historical data
   - Handle missing values and outliers
   - Create data quality dashboard
   - Analyze seasonality and trends

2. **Baseline Model**
   - Implement Prophet for item-level daily forecasts
   - Measure baseline accuracy (MAPE < 30%)
   - Deploy simple REST API for predictions

3. **Infrastructure**
   - Set up MLflow for experiment tracking
   - Create training/inference pipelines
   - Set up monitoring and alerting

**Deliverables:**
- Working demand forecast API
- Data quality report
- Performance baseline metrics

---

### Phase 2: Optimization (Weeks 4-6)
**Goal:** Advanced forecasting and inventory optimization

1. **Enhanced Forecasting**
   - Implement XGBoost with engineered features
   - Multi-horizon predictions (1-day, 7-day, 30-day)
   - Ensemble Prophet + XGBoost for robustness
   - Target MAPE < 20%

2. **Prep Optimization**
   - Build BOM-based prep calculator
   - Implement FEFO batch prioritization
   - Create daily prep recommendation engine

3. **Expiration Management**
   - Develop priority scoring system
   - Build expiration alert system
   - Create waste tracking dashboard

**Deliverables:**
- Improved forecast accuracy (20% MAPE)
- Automated prep recommendations
- Expiration management system

---

### Phase 3: Intelligence (Weeks 7-10)
**Goal:** Dynamic pricing, promotions, and external factors

1. **Promotion Engine**
   - Market basket analysis for bundles
   - Dynamic pricing recommendations
   - Campaign effectiveness measurement

2. **External Factors**
   - Integrate weather and calendar data
   - Causal impact analysis
   - Scenario-based forecasting

3. **Personalization**
   - Customer segmentation
   - Personalized recommendations
   - Channel-specific strategies

**Deliverables:**
- Dynamic pricing system
- Bundle recommendation engine
- Comprehensive business insights dashboard

---

### Phase 4: Advanced AI (Weeks 11-16)
**Goal:** Deep learning and reinforcement learning

1. **Deep Learning Forecasting**
   - Implement LSTM/Transformer models
   - Multi-item joint forecasting
   - Transfer learning across locations

2. **Reinforcement Learning**
   - RL-based pricing agent
   - Automated A/B testing
   - Continuous learning system

3. **Real-time Adaptation**
   - Online learning for model updates
   - Real-time demand sensing
   - Automated retraining pipelines

**Deliverables:**
- Production-grade deep learning models
- Autonomous pricing system
- Self-improving AI platform

---

## Technology Stack Recommendations

### Core ML/AI Libraries
```python
# Forecasting
- prophet (Facebook Prophet for time series)
- statsmodels (SARIMA, statistical models)
- xgboost / lightgbm (Gradient boosting)
- pytorch-forecasting (Deep learning time series)

# Optimization
- scipy.optimize (Linear/nonlinear optimization)
- pulp / cvxpy (Linear programming)
- or-tools (Google optimization)

# Recommendation
- mlxtend (Association rules, FP-Growth)
- surprise (Collaborative filtering)

# Reinforcement Learning
- stable-baselines3 (RL algorithms)
- ray[rllib] (Distributed RL)

# Feature Engineering
- tsfresh (Time series features)
- featuretools (Automated feature engineering)

# Experiment Tracking
- mlflow (Experiment management)
- wandb (Weights & Biases)

# Model Serving
- FastAPI (REST API)
- celery (Task queue for batch predictions)
- redis (Caching)

# Monitoring
- prometheus + grafana (Metrics)
- evidently (ML monitoring)
```

### Infrastructure
- **Database:** PostgreSQL (production) + SQLite (development)
- **Task Queue:** Celery + Redis for async processing
- **Model Registry:** MLflow
- **Deployment:** Docker + Kubernetes (or simpler: Docker Compose)
- **Cloud:** AWS (SageMaker, S3, Lambda) or GCP (Vertex AI)

---

## Evaluation Metrics

### Forecasting Metrics
- **MAPE** (Mean Absolute Percentage Error): Industry standard, target < 20%
- **RMSE** (Root Mean Squared Error): Penalizes large errors
- **MAE** (Mean Absolute Error): Robust to outliers
- **Forecast Bias**: Check for systematic over/under-prediction

### Business Metrics
- **Waste Reduction**: % decrease in expired inventory
- **Stockout Rate**: % of time items are unavailable
- **Revenue Impact**: Incremental revenue from better stock
- **Profit Margin**: Net improvement after waste reduction
- **Customer Satisfaction**: Reduced stockouts, fresher inventory

### Model Performance Tracking
```python
# Daily monitoring
- Prediction vs. Actual comparison
- Drift detection (data distribution changes)
- Feature importance stability
- Model latency and throughput

# Weekly review
- Model retraining triggers
- Performance by item category
- Performance by location
- Seasonal adjustments needed
```

---

## Risk Mitigation & Challenges

### Data Challenges
1. **Missing Historical Weather/Events:** 
   - Solution: Start without, add incrementally via APIs
   
2. **Data Quality Issues:**
   - Solution: Implement data validation pipelines
   - Use anomaly detection to flag bad data
   
3. **Cold Start Problem (New Items/Places):**
   - Solution: Use hierarchical models, borrow strength from similar items
   - Implement content-based features (item category, price range)

### Model Challenges
1. **Model Drift:**
   - Solution: Automated retraining schedule (weekly/monthly)
   - Monitor prediction errors and trigger retraining
   
2. **Overfitting:**
   - Solution: Proper train/validation/test splits
   - Cross-validation with time-based folds
   
3. **Interpretability:**
   - Solution: Use SHAP values for feature importance
   - Provide confidence intervals with predictions
   - Create visual dashboards for business users

### Operational Challenges
1. **User Adoption:**
   - Solution: Start with pilot locations
   - Provide clear ROI metrics
   - Make UI intuitive and actionable
   
2. **Integration with Existing Systems:**
   - Solution: Build REST APIs for loose coupling
   - Provide export functionality (Excel, PDF)
   
3. **Computational Costs:**
   - Solution: Start with simpler models
   - Use batch processing for non-urgent predictions
   - Cache frequent queries

---

## Success Criteria

### Technical Success
- ✅ Achieve < 20% MAPE on demand forecasting
- ✅ 90%+ model uptime and reliability
- ✅ < 500ms API response time for predictions
- ✅ Automated retraining without manual intervention

### Business Success
- ✅ 30-40% reduction in food waste
- ✅ 20-30% reduction in stockouts
- ✅ 10-15% improvement in gross profit margin
- ✅ 5-10% increase in customer satisfaction scores
- ✅ ROI positive within 6 months

---

## Next Steps

1. **Immediate Actions:**
   - Review and approve AI approach strategy
   - Set up development environment and ML infrastructure
   - Begin Phase 1: Data quality assessment and baseline model
   
2. **Week 1 Deliverables:**
   - Comprehensive data quality report
   - EDA with key insights and patterns
   - Prophet baseline model with initial accuracy metrics
   
3. **Stakeholder Alignment:**
   - Present findings to business teams
   - Gather feedback on prioritization
   - Refine roadmap based on business urgency

---

## Conclusion

The proposed AI approach combines multiple proven methodologies to address FreshFlow's inventory challenges comprehensively. By starting with simpler models (Prophet, XGBoost) and progressively adding complexity (LSTM, RL), we minimize risk while maximizing learning.

The data assets available (400K orders, 2M order items) provide sufficient signal for accurate predictions. The key to success lies in:
1. **Incremental Implementation**: Start simple, add complexity as needed
2. **Business Alignment**: Focus on metrics that matter (waste, stockouts, profit)
3. **Continuous Improvement**: Monitor, measure, and refine models regularly

With this strategy, FreshFlow can transform from reactive "gut instinct" operations to proactive, data-driven inventory management, ultimately improving profitability and sustainability.
