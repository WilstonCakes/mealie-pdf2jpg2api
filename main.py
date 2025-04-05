import os
import requests
from PyPDF2 import PdfReader, PdfWriter
from pdf2image import convert_from_path
from dotenv import load_dotenv
import time

def configure():
    load_dotenv()

def split_pdf(input_pdf, output_folder, pages_per_split):
    print(f"Splitting PDF {input_pdf}")

    reader = PdfReader(input_pdf)
    total_pages = len(reader.pages)
    base_name = os.path.splitext(os.path.basename(input_pdf))[0]

    coverted_folder = os.path.join(base_name, "Converted")
    if not os.path.exists(coverted_folder):
        os.makedirs(coverted_folder)

    for start_page in range(0, total_pages, pages_per_split):
        writer = PdfWriter()
        for page_num in range(start_page, min(start_page + pages_per_split, total_pages)):
            writer.add_page(reader.pages[page_num])

        split_pdf_path = os.path.join(output_folder, f"{base_name}_part{start_page // pages_per_split + 1}.pdf")
        with open(split_pdf_path, "wb") as output_pdf:
            writer.write(output_pdf)
        yield split_pdf_path
    os.rename(input_pdf, os.path.join(coverted_folder, base_name + ".pdf"))

def convert_pdf_to_jpg(pdf_path, output_folder):
    print(f"Converting PDF {pdf_path} to jpg")
    images = convert_from_path(pdf_path)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]

    for i, image in enumerate(images):
        jpg_path = os.path.join(output_folder, f"{base_name}.jpg")
        image.save(jpg_path, "JPEG")

def process_pdfs(input_folder, output_folder, pages_per_split):
    print(f"Processing PDFs in folder {input_folder}")

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for file_name in os.listdir(input_folder):
        if file_name.endswith(".pdf"):
            input_pdf_path = os.path.join(input_folder, file_name)
            for split_pdf_path in split_pdf(input_pdf_path, output_folder, pages_per_split):
                convert_pdf_to_jpg(split_pdf_path, output_folder)
                os.remove(split_pdf_path)

def upload_to_mealie(jpg_folder):
    print(f"Starting upload to Mealie from folder {jpg_folder}")

    error_counter = 0

    uploaded_folder = os.path.join(jpg_folder, "Uploaded")
    if not os.path.exists(uploaded_folder):
        os.makedirs(uploaded_folder)

    error_folder = os.path.join(jpg_folder, "Errors")
    if not os.path.exists(error_folder):
        os.makedirs(error_folder)

    headers = {
        "Authorization": f"Bearer {os.getenv('MEALIE_API_TOKEN')}"
    }

    for file_name in os.listdir(jpg_folder):
        if file_name.endswith(".jpg"):
            print(f"Uploading {file_name}")
            file_path = os.path.join(jpg_folder, file_name)
            with open(file_path, "rb") as image_file:
                files = {"images": image_file}
                response = requests.post(os.getenv('MEALIE_API_URL'), headers=headers, files=files)

                if response.status_code == 201:
                    print(f"Uploaded {file_name} successfully.")
                    os.rename(file_path, os.path.join(uploaded_folder, file_name))
                    error_counter = 0
                else:
                    print(f"Failed to upload {file_name}. Status code: {response.status_code}, Response: {response.text}")
                    os.rename(file_path, os.path.join(error_folder, file_name))
                    error_counter += 1
                    if error_counter >= int(os.getenv('ERROR_LIMIT_MAX', 5)):
                        print("Error limit reached. Exiting.")
                        break
        time.sleep(int(os.getenv('WAIT_TIME', 0)))


if __name__ == "__main__":
    configure()
    if os.getenv('EXPORT_ONLY', 'false').lower() == 'true':
        print("Export only mode is enabled. Skipping PDF processing.")
    else:
        process_pdfs(os.getenv('INPUT_FOLDER'), os.getenv('OUTPUT_FOLDER'), int(os.getenv('PAGES_PER_SPLIT')))
    #upload_to_mealie(os.getenv('OUTPUT_FOLDER'))