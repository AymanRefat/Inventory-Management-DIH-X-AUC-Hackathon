# AI Approach Strategy for FreshFlow Inventory Management

## Executive Summary

This document outlines the implemented AI/ML approach to solve inventory management challenges, specifically focusing on **Demand Forecasting**. Based on the available data structure and business requirements, we have implemented a time series forecasting system using **Meta's Prophet**.

---

## Problem Statement

Restaurant and grocery owners face critical challenges:
- **Over-stocking**: Leads to waste and expired inventory
- **Under-stocking**: Causes stockouts and lost revenue
- **Root Cause**: Poor demand forecasting

**Solution**: Implement an AI-driven system that uses historical sales data to predict future demand with high accuracy and confidence intervals.

---

## Available Data Assets

### Dimensional Data (~235K records)
- **88,921 Items**: Menu items with pricing
- **2,091 Places**: Restaurant/store locations
- **22,956 Users**: Customer profiles

### Transactional Data (~2.45M records)
- **400,009 Orders**: Sales transactions
- **1,999,341 Order Items**: Detailed line items

### Key Features Used
- **Temporal data**: Order timestamps (`created_at`)
- **Location data**: Place IDs
- **Item relationships**: Menu items linked to orders
- **Sales Volume**: Quantity sold per item per day

---

## Implemented AI Approach: Demand Forecasting

### "How do we accurately predict daily demand?"

#### Method: Time Series Forecasting with Prophet
**Methodology:**
- **Prophet (by Meta)**: Additive regression model for time series forecasting.
- **Granularity**: 
  - **Item-level**: Predict demand for specific products (e.g., "Cappuccino").
  - **Place-level**: Forecast aggregate demand for a location.
- **Features**:
  - Historical daily sales volume (`quantity`)
  - Weekly seasonality (e.g., higher demand on weekends)
  - Yearly seasonality (if > 1 year of data available)
  - Custom holidays/events handled automatically

**Implementation Details:**
1. **Data Aggregation**: Daily sales (`y`) aggregated directly from `fct_order_items` vs date (`ds`).
2. **Missing Data Handling**: Zero-filling for days with no sales to ensure continuous time series.
3. **Model Training**: A separate Prophet model is trained for each requested Item/Place combination.
4. **Prediction**: Generates point forecasts (`yhat`) and confidence intervals (80% and 95%).
5. **Metrics**: Performance evaluated using MAPE (Mean Absolute Percentage Error) and RMSE.

**Why Prophet?**
- **Robustness**: Handles missing data and outliers well.
- **Interpretability**: Decomposable components (trend + seasonality).
- **Automation**: Requires minimal hyperparameter tuning for good baseline performance.
- **Fallback**: Includes a Moving Average fallback strategy for items with insufficient history (<14 days).

---

## Technology Stack

### Core AI Libraries
- **prophet**: The primary forecasting engine.
- **pandas**: Data manipulation and time series aggregation.
- **numpy**: Numerical operations for metrics calculation.

### Infrastructure
- **Database**: PostgreSQL (for reliable data storage)
- **Backend**: Django (orchestrates data fetching, training, and prediction)
- **Integration**: Database-direct aggregation for performance.

---

## Evaluation Metrics

### Forecasting Accuracy
- **MAPE** (Mean Absolute Percentage Error): Primary metric. Target < 20%.
- **RMSE** (Root Mean Squared Error): Used to penalize large errors.
- **MAE** (Mean Absolute Error): Average absolute error in units sold.

### Monitoring
- **Training Dates**: Tracking when models were last updated.
- **Data Points**: Monitoring sufficiency of historical data (e.g., > 14 days required).

---

## Risk Mitigation

### Data Challenges
1. **Missing Data**: Handled by zero-filling missing dates in the time series.
2. **Cold Start**: New items with < 14 days of history use a simple fallback (moving average) until sufficient data is collected.

### Model Challenges
1. **Model Drift**: Models track training dates to signal when retraining is needed.
2. **Interpretability**: Confidence intervals (80/95%) provide transparency on prediction uncertainty.

---

## Success Criteria

### Technical Success
- ✅ **Integration**: Seamlessly integrated into Django admin/dashboard.
- ✅ **Performance**: Sub-second inference time for cached models.
- ✅ **Scalability**: Capable of generating thousands of item-level forecasts in batch jobs.

### Business Value
- **Waste Reduction**: Accurate daily prep sheets reduce over-prep.
- **Stock Optimization**: Data-driven ordering prevents stockouts.
- **Efficiency**: Automates manual forecasting tasks.

---

## Conclusion

The implemented Prophet-based forecasting system provides a solid foundation for data-driven inventory management. By focusing on robustness and interpretability, the system delivers actionable insights directly to restaurant managers through the dashboard.
