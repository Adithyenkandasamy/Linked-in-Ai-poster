import os
import requests

def post_to_linkedin(text, image_path=None):
    url = "https://hook.eu2.make.com/d6eank315humfn1i9ml9v4nd4qj7pp6k"

    files = {}
    data = {"text": text}

    if image_path:
        # Get file extension and determine content type
        ext = os.path.splitext(image_path)[1].lower()
        content_type = "image/png" if ext == ".png" else "image/jpeg"
        
        try:
            # Use a context manager to ensure the file is properly closed
            with open(image_path, 'rb') as img_file:
                files['image'] = (os.path.basename(image_path), img_file, content_type)
                response = requests.post(url, data=data, files=files)
                response.raise_for_status()
                print("✅ Sent to Make.com with image successfully.")
                return response.status_code, response.text
        except FileNotFoundError:
            print(f"❌ Error: Image file not found at {image_path}")
            return 404, "Image file not found"
        except Exception as e:
            print(f"❌ Error sending to Make.com: {e}")
            return 500, str(e)
    else:
        try:
            response = requests.post(url, data=data)
            response.raise_for_status()
            print("✅ Sent to Make.com successfully.")
            return response.status_code, response.text
        except Exception as e:
            print(f"❌ Error sending to Make.com: {e}")
            return 500, str(e)

# Example usage
if __name__ == "__main__":
    # Test with just text
    status, response = post_to_linkedin("Test post")
    print(f"Status: {status}, Response: {response}")
    
    # Test with an image (uncomment and replace with actual path)
    # status, response = post_to_linkedin("Test post with image", "/path/to/your/image.jpg")
    # print(f"Status: {status}, Response: {response}")
