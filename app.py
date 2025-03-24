import os
import logging
import io
from uuid import uuid4
from flask import Flask, request, jsonify, send_from_directory, url_for
from pypdf import PdfReader
from PIL import Image

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = "uploads"
EXTRACTED_FOLDER = "extracted_images"
ALLOWED_EXTENSIONS = {"pdf"}

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXTRACTED_FOLDER, exist_ok=True)


def extract_images_from_pdf(pdf_file_path: str, output_path: str):
    """Extract images from a PDF and rename first two images as user-img.png and sign-img.png."""
    try:
        reader = PdfReader(pdf_file_path)
        seen_images = set()
        extracted_files = []
        image_count = 0

        for page in reader.pages:
            for image in page.images:
                image_data = image.data
                image_hash = hash(image_data)

                if image_hash in seen_images:
                    continue

                seen_images.add(image_hash)
                ext = ".png"

                # Convert JP2 to PNG if necessary
                try:
                    with Image.open(io.BytesIO(image_data)) as img:
                        if img.mode == "RGBA":
                            img = img.convert("RGB")
                        image_data = io.BytesIO()
                        img.save(image_data, format="PNG")
                        image_data = image_data.getvalue()
                except Exception as e:
                    logging.error(f"Failed to process image: {e}")
                    continue

                # Naming logic
                if image_count == 0:
                    image_filename = f"user-img-{str(uuid4())[:18]}.png"
                elif image_count == 1:
                    image_filename = f"sign-img-{str(uuid4())[:18]}.png"
                else:
                    image_filename = f"{uuid4()}{ext.lower()}"

                image_count += 1

                file_path = os.path.join(output_path, image_filename)
                with open(file_path, "wb") as fp:
                    fp.write(image_data)

                extracted_files.append(image_filename)

        return extracted_files

    except Exception as e:
        logging.error(f"Failed to extract images from {pdf_file_path}: {e}")
        return []

@app.route("/")
def home():
	return jsonify({"message": "Nothing here"})

@app.route("/extract_image", methods=["POST"])
def upload_file():
    """Handle file upload and extract images."""
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if file and file.filename.split(".")[-1].lower() in ALLOWED_EXTENSIONS:
        file_path = os.path.join(UPLOAD_FOLDER, f"{uuid4()}.pdf")
        file.save(file_path)

        extracted_images = extract_images_from_pdf(file_path, EXTRACTED_FOLDER)

        if extracted_images:
            image_urls = [url_for("download_file", filename=f, _external=True) for f in extracted_images]
            return jsonify({"message": "Images extracted successfully", "images": image_urls})

        return jsonify({"message": "No images found in the PDF"}), 200

    return jsonify({"error": "Invalid file type"}), 400


@app.route("/images/<filename>")
def download_file(filename):
    """Serve extracted images."""
    return send_from_directory(EXTRACTED_FOLDER, filename)

if __name__ == "__main__":
    app.run(debug=True)