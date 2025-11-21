"""
Train ML model for football predictions
Uses XGBoost with fallback to RandomForest
"""
import pandas as pd
import numpy as np
from pathlib import Path
import joblib
import json
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

# Optional scikit-learn (only if XGBoost unavailable)
try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    # Fallback implementations if sklearn not available
    print("⚠️ Warning: scikit-learn not available. Using simple implementations.")

BASE_DIR = Path(__file__).parent.parent.parent
MODEL_DIR = BASE_DIR / "models"
# Create models directory if it doesn't exist (handle permission errors gracefully)
try:
    MODEL_DIR.mkdir(exist_ok=True, parents=True)
except PermissionError:
    # If we can't create it, try to use /tmp/models instead
    MODEL_DIR = Path("/tmp/models")
    MODEL_DIR.mkdir(exist_ok=True, parents=True)
    print(f"⚠️ Warning: Could not create models directory in /app, using /tmp/models instead")

MODEL_PATH = MODEL_DIR / "football_model.pkl"
SCALER_PATH = MODEL_DIR / "scaler.pkl"
FEATURES_PATH = MODEL_DIR / "feature_names.json"


class FootballPredictor:
    """ML model for football prediction"""
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = []
        
    def extract_features(self, match_data: Dict) -> np.ndarray:
        """Extract features from match data for ML model"""
        features = []
        
        # Team performance features
        home_form = match_data.get('home_form', {})
        away_form = match_data.get('away_form', {})
        
        # Goals scored/conceded (last 5 matches)
        features.extend([
            home_form.get('goals_scored_5', 0),
            home_form.get('goals_conceded_5', 0),
            away_form.get('goals_scored_5', 0),
            away_form.get('goals_conceded_5', 0),
        ])
        
        # Form percentage
        features.extend([
            home_form.get('form_percentage', 0.5),
            away_form.get('form_percentage', 0.5),
        ])
        
        # Expected goals
        features.extend([
            match_data.get('home_xg', 1.5),
            match_data.get('away_xg', 1.5),
        ])
        
        # Shots on target
        features.extend([
            home_form.get('shots_on_target_avg', 4.0),
            away_form.get('shots_on_target_avg', 4.0),
        ])
        
        # League context
        features.extend([
            match_data.get('home_position', 10),
            match_data.get('away_position', 10),
            match_data.get('table_gap', 0),
        ])
        
        # Pressure index (0-1)
        features.append(match_data.get('pressure_index', 0.5))
        
        # Match importance
        features.extend([
            1.0 if match_data.get('is_derby', False) else 0.0,
            1.0 if match_data.get('is_must_win', False) else 0.0,
            match_data.get('fixture_congestion', 7),  # Days since last match
        ])
        
        # Odds
        features.extend([
            match_data.get('home_odds', 2.0),
            match_data.get('draw_odds', 3.0),
            match_data.get('away_odds', 2.0),
        ])
        
        # League tier encoding (one-hot like)
        tier = match_data.get('league_tier', 'other')
        tier_encoding = {
            'EPL': [1, 0, 0, 0, 0, 0],
            'LaLiga': [0, 1, 0, 0, 0, 0],
            'Bundesliga': [0, 0, 1, 0, 0, 0],
            'SerieA': [0, 0, 0, 1, 0, 0],
            'Ligue1': [0, 0, 0, 0, 1, 0],
            'Eredivisie': [0, 0, 0, 0, 0, 1],
        }
        features.extend(tier_encoding.get(tier, [0, 0, 0, 0, 0, 0]))
        
        self.feature_names = [
            'home_goals_scored_5', 'home_goals_conceded_5',
            'away_goals_scored_5', 'away_goals_conceded_5',
            'home_form_pct', 'away_form_pct',
            'home_xg', 'away_xg',
            'home_sot_avg', 'away_sot_avg',
            'home_position', 'away_position', 'table_gap',
            'pressure_index',
            'is_derby', 'is_must_win', 'fixture_congestion',
            'home_odds', 'draw_odds', 'away_odds',
            'tier_EPL', 'tier_LaLiga', 'tier_Bundesliga',
            'tier_SerieA', 'tier_Ligue1', 'tier_Eredivisie',
        ]
        
        return np.array(features).reshape(1, -1)
    
    def train(self, training_data: List[Dict], target_variable: str = "outcome"):
        """
        Train the model on historical data
        
        Args:
            training_data: List of match dictionaries with outcomes
            target_variable: What to predict (e.g., "over_0.5_goals", "home_win")
        """
        # Convert to DataFrame
        features_list = []
        targets = []
        
        for match in training_data:
            feat = self.extract_features(match)
            features_list.append(feat[0])
            
            # Target: 1 if prediction correct, 0 otherwise
            # For now, predict probability of safe markets
            if target_variable == "over_0.5_goals":
                target = 1.0 if match.get('total_goals', 0) > 0.5 else 0.0
            elif target_variable == "home_win":
                target = 1.0 if match.get('result') == 'home' else 0.0
            else:
                target = match.get('target', 0.5)
            
            targets.append(target)
        
        X = np.array(features_list)
        y = np.array(targets)
        
        # Split data
        if SKLEARN_AVAILABLE:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
        else:
            # Simple split if sklearn not available
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]
            # Simple normalization
            X_train_scaled = (X_train - X_train.mean(axis=0)) / (X_train.std(axis=0) + 1e-8)
            X_test_scaled = (X_test - X_train.mean(axis=0)) / (X_train.std(axis=0) + 1e-8)
        
        # Train model
        if XGBOOST_AVAILABLE:
            print("Training XGBoost model...")
            self.model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                subsample=0.8,
                random_state=42,
                eval_metric='logloss'
            )
            self.model.fit(
                X_train_scaled, y_train,
                eval_set=[(X_test_scaled, y_test)] if len(X_test_scaled) > 0 else None,
                verbose=False
            )
        elif SKLEARN_AVAILABLE:
            print("XGBoost not available, using RandomForest...")
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            self.model.fit(X_train_scaled, y_train)
        else:
            raise ImportError("Neither XGBoost nor scikit-learn is available. Please install at least one.")
        
        # Evaluate
        if len(X_test_scaled) > 0:
            y_pred = self.model.predict(X_test_scaled)
            y_pred_proba = self.model.predict_proba(X_test_scaled)
            if y_pred_proba.shape[1] > 1:
                y_pred_proba = y_pred_proba[:, 1]
            else:
                y_pred_proba = y_pred_proba[:, 0]
            
            if SKLEARN_AVAILABLE:
                accuracy = accuracy_score(y_test, y_pred)
                precision = precision_score(y_test, y_pred, zero_division=0)
                recall = recall_score(y_test, y_pred, zero_division=0)
            else:
                # Simple metrics without sklearn
                accuracy = (y_pred == y_test).mean()
                precision = (y_pred[y_test == 1] == 1).sum() / (y_pred == 1).sum() if (y_pred == 1).sum() > 0 else 0
                recall = (y_pred[y_test == 1] == 1).sum() / (y_test == 1).sum() if (y_test == 1).sum() > 0 else 0
        
        print(f"Model Performance:")
        print(f"  Accuracy: {accuracy:.3f}")
        print(f"  Precision: {precision:.3f}")
        print(f"  Recall: {recall:.3f}")
        
        # Save model
        joblib.dump(self.model, MODEL_PATH)
        joblib.dump(self.scaler, SCALER_PATH)
        
        with open(FEATURES_PATH, 'w') as f:
            json.dump(self.feature_names, f)
        
        print(f"✅ Model saved to {MODEL_PATH}")
        
    def predict(self, match_data: Dict, market_type: str = "over_0.5_goals") -> float:
        """Predict probability for a specific market"""
        if self.model is None:
            self.load()
        
        features = self.extract_features(match_data)
        features_scaled = self.scaler.transform(features)
        
        # Get probability
        proba = self.model.predict_proba(features_scaled)[0]
        probability = proba[1] if len(proba) > 1 else proba[0]
        
        return float(probability)
    
    def load(self):
        """Load trained model"""
        if MODEL_PATH.exists():
            self.model = joblib.load(MODEL_PATH)
            self.scaler = joblib.load(SCALER_PATH)
            
            with open(FEATURES_PATH, 'r') as f:
                self.feature_names = json.load(f)
            print(f"✅ Model loaded from {MODEL_PATH}")
        else:
            raise FileNotFoundError(f"Model not found at {MODEL_PATH}. Train the model first.")


def create_sample_training_data() -> List[Dict]:
    """
    Create sample training data for initial model
    In production, load from API-Football or database
    """
    # This is sample data - replace with real historical data
    sample_data = []
    
    # Example: Safe match (high-scoring teams, stable league)
    for i in range(100):
        sample_data.append({
            'home_form': {
                'goals_scored_5': np.random.uniform(8, 12),
                'goals_conceded_5': np.random.uniform(2, 5),
                'form_percentage': np.random.uniform(0.7, 0.9),
                'shots_on_target_avg': np.random.uniform(5, 7),
            },
            'away_form': {
                'goals_scored_5': np.random.uniform(6, 10),
                'goals_conceded_5': np.random.uniform(3, 6),
                'form_percentage': np.random.uniform(0.6, 0.8),
                'shots_on_target_avg': np.random.uniform(4, 6),
            },
            'home_xg': np.random.uniform(1.5, 2.0),
            'away_xg': np.random.uniform(1.2, 1.8),
            'home_position': np.random.randint(3, 12),
            'away_position': np.random.randint(5, 15),
            'table_gap': np.random.randint(0, 5),
            'pressure_index': np.random.uniform(0.2, 0.5),
            'is_derby': False,
            'is_must_win': False,
            'fixture_congestion': np.random.randint(3, 7),
            'home_odds': np.random.uniform(1.5, 2.5),
            'draw_odds': np.random.uniform(3.0, 4.0),
            'away_odds': np.random.uniform(2.0, 3.5),
            'league_tier': np.random.choice(['EPL', 'LaLiga', 'Bundesliga', 'SerieA']),
            'total_goals': np.random.randint(1, 5),  # For "over_0.5_goals" target
            'target': 1.0 if np.random.random() > 0.1 else 0.0,  # 90% safe
        })
    
    return sample_data


if __name__ == "__main__":
    print("🚀 Training Football Prediction Model...\n")
    
    # Create sample data (replace with real data)
    training_data = create_sample_training_data()
    print(f"Training on {len(training_data)} matches...")
    
    # Train model
    predictor = FootballPredictor()
    predictor.train(training_data, target_variable="over_0.5_goals")
    
    print("\n✅ Training complete!")

