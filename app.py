from flask import Flask, render_template, request, jsonify
import cv2
import numpy as np
from PIL import Image
import base64
import io
from sklearn.ensemble import RandomForestClassifier

app = Flask(__name__)

class SimpleHairAnalyzer:
    def __init__(self):
        self.face_shape_model = self._train_face_shape_model()
        
    def _train_face_shape_model(self):
        np.random.seed(42)
        # Generate synthetic training data
        oval_data = np.random.normal([0.85, 1.2, 0.8], [0.05, 0.1, 0.05], (100, 3))
        round_data = np.random.normal([0.95, 1.0, 0.9], [0.05, 0.08, 0.05], (100, 3))
        square_data = np.random.normal([0.9, 1.1, 0.9], [0.05, 0.08, 0.05], (100, 3))
        
        X = np.vstack([oval_data, round_data, square_data])
        y = np.hstack([np.zeros(100), np.ones(100), np.full(100, 2)])
