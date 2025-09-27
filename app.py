import os
import json
import random
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
# Enable CORS for local testing and deployment
CORS(app)

# --- EXPANDED HIGH-END AI MOCK DATA AND LOGIC ---

# 1. EXPANDED MOCK BARBER DATABASE (Atlanta, GA)
# We map multiple cuts to the existing specialist barbers for simplicity in this file.
ATLANTA_BARBERS = {
    # Specialist in Sharp Lines, Fades (Short/Medium)
    "Taper Specialist": [
        {"name": "The Fade Factory", "rating": 4.9, "distance": "1.2 mi", "address": "123 Peachtree St NE, Atlanta"},
        {"name": "Master Clippers ATL", "rating": 4.7, "distance": "3.5 mi", "address": "456 Northside Dr NW, Atlanta"},
    ],
    # Specialist in Structured, Classic Cuts (Medium/High Style)
    "Classic Specialist": [
        {"name": "Classic Gents Salon", "rating": 4.8, "distance": "0.8 mi", "address": "789 Ponce De Leon Ave NE, Atlanta"},
        {"name": "The Modern Barber", "rating": 4.6, "distance": "2.1 mi", "address": "101 BeltLine Trail, Atlanta"},
    ],
    # Specialist in Texture, Layers, and Volume (Curly/Wavy/Fine)
    "Texture Specialist": [
        {"name": "Texture Studio", "rating": 4.8, "distance": "1.5 mi", "address": "404 West End SW, Atlanta"},
        {"name": "Curly & Co.", "rating": 4.9, "distance": "2.9 mi", "address": "505 Decatur St SE, Atlanta"},
    ],
    # Specialist in Short/Military Cuts
    "Quick Cuts": [
        {"name": "The Quick Clip Shop", "rating": 4.3, "distance": "1.8 mi", "address": "606 Marietta St NW, Atlanta"},
    ],
}

# 2. COMPREHENSIVE HAIRCUT TAXONOMY (~40 Styles)
# Data structure: [Haircut Name, [Face Shapes Priority], [Texture Suitability], [Density Suitability], [Length], [Gender Focus], Barber Key]
HAIRCUT_TAXONOMY = [
    # SHORT CUTS (Gender Neutral/Male Focus)
    ["High Taper Fade", ["Round", "Square"], ["Straight", "Wavy"], ["Medium", "Thick"], "Short", "Male", "Taper Specialist"],
    ["Textured Crop", ["Oval", "Oblong"], ["Straight", "Wavy"], ["Thin", "Medium"], "Short", "Gender Neutral", "Taper Specialist"],
    ["French Crop", ["Diamond", "Oval"], ["Straight", "Wavy"], ["Medium"], "Short", "Male", "Taper Specialist"],
    ["Buzz Cut (Level 1)", ["All"], ["All"], ["Thin"], "Short", "Gender Neutral", "Quick Cuts"],
    ["Crew Cut", ["Round", "Heart"], ["Straight"], ["Medium", "Thick"], "Short", "Male", "Classic Specialist"],
    ["Undercut", ["Oval", "Square"], ["Straight", "Wavy"], ["Thick"], "Short", "Male", "Taper Specialist"],
    ["Pixie Cut (Layered)", ["Round", "Heart"], ["Wavy", "Curly"], ["Thin", "Medium"], "Short", "Female", "Texture Specialist"],
    ["Short Shag", ["Diamond", "Oval"], ["Wavy", "Curly"], ["Medium", "Thick"], "Short", "Gender Neutral", "Texture Specialist"],

    # MEDIUM CUTS (Diverse Focus)
    ["Classic Side Part", ["Oblong", "Round"], ["Straight", "Wavy"], ["Medium"], "Medium", "Male", "Classic Specialist"],
    ["Quiff (High Volume)", ["Square", "Round"], ["Straight"], ["Thick"], "Medium", "Classic Specialist"],
    ["Curtain Bangs", ["Oblong", "Square"], ["Straight", "Wavy"], ["Thin", "Medium"], "Medium", "Female", "Texture Specialist"],
    ["Medium Layers (Volume)", ["Heart", "Oval"], ["Wavy", "Curly"], ["Thin", "Medium"], "Medium", "Female", "Texture Specialist"],
    ["Shoulder-Length Bob", ["Round", "Oval"], ["Straight", "Wavy"], ["Medium", "Thick"], "Medium", "Female", "Classic Specialist"],
    ["Mullet (Modern)", ["All"], ["All"], ["All"], "Medium", "Gender Neutral", "Taper Specialist"],
    ["Bro Flow", ["Oval", "Oblong"], ["Wavy"], ["Thick"], "Medium", "Male", "Texture Specialist"],
    ["Asymmetrical Bob", ["Heart", "Diamond"], ["Straight"], ["Medium"], "Medium", "Female", "Classic Specialist"],
    ["Wavy Pompadour", ["Square", "Round"], ["Wavy"], ["Medium", "Thick"], "Medium", "Classic Specialist"],
    ["Shaggy Lob", ["Oval", "Diamond"], ["Wavy", "Curly"], ["Thin", "Medium"], "Medium", "Female", "Texture Specialist"],
    
    # LONG CUTS (Diverse Focus)
    ["Long Layers w/ Fringe", ["Heart", "Diamond"], ["Curly", "Coily"], ["Medium", "Thick"], "Long", "Gender Neutral", "Texture Specialist"],
    ["Coily Afro Shape Up", ["All"], ["Coily"], ["Thick"], "Long", "Gender Neutral", "Texture Specialist"],
    ["Straight Long Layers", ["Round", "Square"], ["Straight"], ["Medium", "Thick"], "Long", "Female", "Classic Specialist"],
    ["Thinning Hair Layers", ["All"], ["Straight", "Wavy"], ["Thin"], "Long", "Female", "Texture Specialist"],
    ["One-Length Cut", ["Oval"], ["Straight"], ["Thick"], "Long", "Female", "Classic Specialist"],
    ["Tapered Coils (Long)", ["Oval", "Oblong"], ["Coily"], ["Medium"], "Long", "Gender Neutral", "Texture Specialist"],
    
    # ADD MORE CUTS (Filler to reach 40+)
    ["Ivy League", ["Oval"], ["Straight"], ["Medium"], "Short", "Male", "Classic Specialist"],
    ["Brush Cut", ["Round"], ["Straight"], ["Medium", "Thick"], "Short", "Male", "Quick Cuts"],
    ["Faux Hawk", ["Square"], ["Straight", "Wavy"], ["Medium"], "Medium", "Male", "Taper Specialist"],
    ["Slick Back", ["Oval"], ["Straight"], ["Medium"], "Medium", "Male", "Classic Specialist"],
    ["Shaved Sides, High Top", ["Oblong"], ["Coily", "Curly"], ["Thick"], "Short", "Male", "Taper Specialist"],
    ["A-Line Bob", ["Heart"], ["Straight"], ["Medium"], "Medium", "Female", "Classic Specialist"],
    ["V-Shape Cut", ["Oval"], ["Straight"], ["Thick"], "Long", "Female", "Classic Specialist"],
    ["U-Shape Cut", ["Round"], ["Straight", "Wavy"], ["Medium"], "Long", "Female", "Classic Specialist"],
    ["Grown Out Pixie", ["Diamond"], ["Wavy"], ["Thin"], "Medium", "Female", "Texture Specialist"],
    ["Bangs (Full)", ["Oblong"], ["Straight"], ["Medium"], "Long", "Female", "Texture Specialist"],
]

# Feature Categories for simulation
FACE_SHAPES = ["Oval", "Round", "Square", "Oblong", "Diamond", "Heart"]
HAIR_TEXTURES = ["Straight (1A/1B)", "Wavy (2A/2B)", "Curly (3A/3B)", "Coily (4A/4B)"]
HAIR_DENSITY = ["Thin", "Medium", "Thick"]
HAIR_LENGTH = ["Short", "Medium", "Long"]
USER_GENDER = ["Male", "Female", "Gender Neutral"]

def mock_ai_analyze(image_data_b64):
    """
    Simulates a comprehensive, multi-stage AI analysis and recommendation.
    """

    # --- Step 1: Image Validation (Simulated filtering) ---
    # High chance of failure for comprehensive AI, as it must reject bad images.
    if random.random() < 0.15: # 15% chance of non-hair image/poor quality
        return None, "High-End AI Filter engaged: Image quality poor, non-hair content detected, or key facial features obscured. Please submit a clearer photo of the face and hair."

    # --- Step 2: AI Feature Analysis (Simulated results) ---
    # These are the 5 data points the AI extracts from the image
    face_shape = random.choice(FACE_SHAPES)
    hair_texture = random.choice(HAIR_TEXTURES)
    hair_density = random.choice(HAIR_DENSITY)
    detected_length = random.choice(HAIR_LENGTH)
    detected_gender = random.choice(USER_GENDER)
    
    # --- Step 3: Comprehensive Recommendation Matrix (The Core AI Simulation) ---
    
    suitable_cuts = []
    
    for cut in HAIRCUT_TAXONOMY:
        cut_name, shapes, textures, densities, length, gender_focus, barber_key = cut
        
        # 3.1. Primary Filter: Texture and Density are non-negotiable hard requirements
        texture_match = any(t in hair_texture for t in textures)
        density_match = hair_density in densities
        
        if not (texture_match and density_match):
            continue

        # 3.2. Secondary Filter: Length and Gender focus
        length_match = detected_length == length
        gender_match = (gender_focus == "Gender Neutral" or gender_focus == detected_gender)
        
        if not (length_match and gender_match):
            continue

        # 3.3. Tertiary Filter: Face Shape Optimization
        # Score the cut based on how well it matches the face shape detected
        face_score = 0
        if face_shape in shapes:
            face_score = 2 # Best match
        elif face_shape in FACE_SHAPES: # Simple check for any shape match
            face_score = 1 # Decent match

        # If a cut is suitable, add it to the list with its score
        if face_score > 0:
             suitable_cuts.append({
                "name": cut_name,
                "score": face_score,
                "barber_key": barber_key
            })

    # 4. Final Selection: Choose the highest scoring cut
    if not suitable_cuts:
        # Fallback if no specific match is found (e.g., recommend a safe, versatile cut)
        recommendation_name = "Long Layers w/ Fringe" if detected_length == "Long" else "Textured Crop"
        barber_key = "Texture Specialist"
    else:
        # Sort by score (highest first) and then pick a random winner among the top scorers
        suitable_cuts.sort(key=lambda x: x['score'], reverse=True)
        top_score = suitable_cuts[0]['score']
        
        best_matches = [c for c in suitable_cuts if c['score'] == top_score]
        final_cut = random.choice(best_matches)
        
        recommendation_name = final_cut['name']
        barber_key = final_cut['barber_key']


    # --- Step 4: Assemble Analysis Results ---
    # Find the generic description (not included in the massive taxonomy list to save space, but simulated here)
    cut_description = f"The AI highly recommends the **{recommendation_name}** because it optimally balances your {face_shape} shape and manages your {hair_density}, {hair_texture} hair. This style is ideally suited for your current {detected_length} length."

    analysis_results = {
        "face_shape": face_shape,
        "hair_texture": hair_texture,
        "hair_density": hair_density,
        "detected_length": detected_length,
        "detected_gender": detected_gender,
        "recommendation": recommendation_name,
        "cut_description": cut_description,
        "barber_key": barber_key, # New key to find specialists
    }

    return analysis_results, None

@app.route('/analyze', methods=['POST'])
def analyze_image():
    """Endpoint to receive image data and return AI analysis and barber results."""
    
    data = request.get_json()
    image_data_b64 = data.get('image_data', '')

    # 1. Run AI Simulation
    analysis_results, error_message = mock_ai_analyze(image_data_b64)

    if error_message:
        return jsonify({"success": False, "message": error_message}), 400

    # 2. Look up Barbers specializing in the required key
    barber_key = analysis_results['barber_key']
    specialists = ATLANTA_BARBERS.get(barber_key, [])

    # Prepare the final response payload
    response_payload = {
        "success": True,
        "analysis": analysis_results,
        "barbers": specialists
    }
    
    return jsonify(response_payload)


@app.route('/')
def health_check():
    """Simple health check for Render deployment."""
    return "LineUp AI Haircut Recommender Backend is running."

if __name__ == '__main__':
    # Use environment variable for port in production
    port = int(os.environ.get('PORT', 5000))
    # Using host='0.0.0.0' for deployment compatibility
    app.run(host='0.0.0.0', port=port, debug=True)
