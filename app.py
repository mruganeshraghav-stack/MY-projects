from flask import Flask, render_template, request, jsonify
import cv2
import numpy as np
import base64
import mediapipe as mp

app = Flask(__name__)

# Initialize MediaPipe Hands once globally
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1)
mp_drawing = mp.solutions.drawing_utils

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        image_data = data['image'].split(',')[1]

        # Decode Base64 -> NumPy -> OpenCV
        nparr = np.frombuffer(base64.b64decode(image_data), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Convert to RGB for MediaPipe
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = hands.process(img_rgb)

        result_text = "No hand detected"

        if results.multi_hand_landmarks:
            result_text = "Hand detected"
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(img, hand_landmarks, mp_hands.HAND_CONNECTIONS)

        # Encode processed image back to Base64
        _, buffer = cv2.imencode('.png', img)
        processed_image = base64.b64encode(buffer).decode('utf-8')
        processed_image_url = f"data:image/png;base64,{processed_image}"

        return jsonify({"result": result_text, "image": processed_image_url})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(debug=True)
