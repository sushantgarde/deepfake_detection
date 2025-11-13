# Deepfake Detection System - Setup Guide (Reality Defender API)

## Project Overview
This deepfake detection system uses the **Reality Defender API** via its dedicated Python SDK to analyze media (images and audio) and determine if it is authentic or manipulated.

---

## ⚠️ **CRITICAL FREE TIER LIMITATION**

The Reality Defender **API Free Tier** only supports the detection of **Audio and Image** files (up to 50 scans per month). **Video detection is not available** on the free plan.

---

## Prerequisites
- Python 3.8 or higher
- **Reality Defender API Key** (You must obtain this by signing up on the Reality Defender platform).

## Installation Steps

### 1. Get Your Reality Defender API Key
1. Go to the **Reality Defender Platform** and sign up/log in.
2. Navigate to your **Developer Dashboard** to generate your unique **API Key**.
3. **Best Practice:** Set this key as an **environment variable** named `RD_API_KEY` for security.
    * Example (Linux/macOS): `export RD_API_KEY="your-actual-key-here"`

### 2. Install Dependencies
You need the Reality Defender SDK and `nest_asyncio` to run the asynchronous detection within the GUI.

```bash
pip install -r requirements.txt