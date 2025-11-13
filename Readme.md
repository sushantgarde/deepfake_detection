# 🛡️ Deepfake Detection System  
A powerful and modular AI-based solution to analyze **images and audio** for deepfake manipulation using the **Reality Defender API**.  
This project is designed for security teams, students, developers, and researchers who want a reliable deepfake scanning tool.

---

## ⭐ **Main Features**
- **Deepfake Detection** for images & audio  
- **Reality Defender API Integration**  
- **Secure API Key Handling (Environment Variables)**  
- **Clean Output with Confidence Scores**  
- **Modular Code Architecture**  
- **Easy to run, easy to extend**

---

# 📘 **Introduction**
Deepfakes are an increasing threat in modern digital ecosystems.  
This project detects manipulated media by sending files through the **Reality Defender Deepfake Classification API**, which analyzes them using advanced machine-learning models.

The tool works with:
- **Images:** JPG, PNG, JPEG  
- **Audio:** WAV, MP3  

This README provides step-by-step setup instructions and complete usage guide.

---

# 🧠 **How it Works**
1. User submits a media file  
2. The file is uploaded securely to the Reality Defender API  
3. AI model analyzes manipulation levels  
4. A JSON result is returned containing:
   - **Authenticity score**  
   - **Deepfake confidence**  
   - **Detection explanation**  
   - **Model insights**  

---

# 🛠️ **Installation**

## **1. Clone the Repository**
```bash
git clone https://github.com/sushantgarde/deepfake_detection.git
cd deepfake_detection
```

## **2. Install the Required Libraries**
```bash
pip install -r requirements.txt
```

---

# 🔑 **API Key Setup**
Register at the Reality Defender dashboard.  
Set your API key as an environment variable:

### Windows:
```bash
setx RD_API_KEY "your_api_key_here"
```

### macOS/Linux:
```bash
export RD_API_KEY="your_api_key_here"
```

---

# 📁 **Project Structure**
```
deepfake_detection/
│
├── main.py             # Command line interface 
├── requirements.txt
└── README.md
```

---

# ▶️ **How to Run**
Run the program:
```bash
python app.py
```

Enter the media file path when prompted:
```
Enter file path: example.jpg
```

You will receive a detailed scan result.

---

# 📊 **Sample Output**
```json
{
  "status": "fake",
  "confidence": 0.94,
  "media_type": "image",
  "analysis": {
    "ai_generated": true,
    "manipulation": "GAN-based synthesis",
    "details": "Texture inconsistencies and digital artifact patterns detected."
  }
}
```

---

# 🚀 **Future Enhancements**
- Support for **video deepfake detection**  
- Real-time **web dashboard**  
- **PDF/HTML** report generator  
- Database-based scan history  

---

# 🔒 **Security Recommendations**
- Never commit your API key  
- Rotate API keys regularly  
- Validate file extensions before upload  
- Use HTTPS endpoints at all times  

---

# 🙌 **Contributors**
- **Sushant Garde**  
- **Shree Shinde**
- **Bijo Salu**
- **Omkar Bhor** 

---

# 📄 **License**
This project is protected under the **MIT License**.  
You are free to modify and distribute it.

---

# 📢 Notes
This project provides a clean, extensible foundation for future enhancements like web interfaces, automated workflows, or real-time detection systems.

