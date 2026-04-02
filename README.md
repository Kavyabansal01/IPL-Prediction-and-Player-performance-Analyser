# IPL Prediction and Player Performance Analyser

An interactive Streamlit web app for IPL player analytics, player comparison, and match winner prediction using machine learning.

Live app:
[Streamlit Deployment](https://ipl-prediction-and-player-performance-analyser-vsfrhbpc36muotr.streamlit.app/)

## Overview

This project combines data analysis and machine learning on IPL data to build a user-friendly dashboard. It helps users explore player performance, compare players side by side, and predict match winners based on team and toss details.

## Features

### Player Analysis
- Search players by name
- View matches, runs, and strike rate
- Analyze recent form using the last 10 matches
- Show a rolling average trend

### Player Comparison
- Compare two players side by side
- Review key batting metrics in a simple table

### Match Winner Prediction
- Predict the winning team using a Random Forest model
- Uses team names, toss winner, and toss decision
- Displays prediction confidence

### Interactive Dashboard
- Built with Streamlit
- Sidebar navigation
- Responsive card-based layout

## Tech Stack

- Python
- Streamlit
- Pandas
- NumPy
- Matplotlib
- Scikit-learn

## Project Structure

```text
IPL prediction/
|-- app.py
|-- deliveries.csv
|-- encoders.pkl
|-- model.pkl
|-- player_name_map.csv
|-- requirements.txt
|-- .streamlit/
|   |-- config.toml
```

## How to Run Locally

1. Clone the repository
2. Open the project folder
3. Install dependencies
4. Run the Streamlit app

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deployment

This project is deployed on Streamlit Community Cloud.

Deployment requirements:
- `app.py`
- `requirements.txt`
- `deliveries.csv`
- `model.pkl`
- `encoders.pkl`
- `player_name_map.csv`

## Model Details

- Model: `RandomForestClassifier`
- Library: `scikit-learn`
- Prediction inputs:
  - Team 1
  - Team 2
  - Toss winner
  - Toss decision

## Future Improvements

- Better player search aliases
- More advanced visualizations
- Team-level analytics
- Better model explanation and accuracy reporting

## Author

Kavya Bansal
