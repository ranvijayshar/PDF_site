import os
import time
from flask import Flask, render_template, request, send_file
from PyPDF2 import PdfMerger, PdfWriter, PdfReader
import platform
from functools import partial

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

# Windows-specific fixes
if platform.system() == 'Windows':
    os.unlink = partial(os.unlink, missing_ok=True)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def cleanup_files(*paths):
    """Safely remove files with error handling"""
    for path in paths:
        try:
            if path and os.path.exists(path):
                os.unlink(path)
        except Exception as e:
            app.logger.error(f"Error deleting {path}: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/merge', methods=['POST'])
def merge_pdfs():
    if 'pdfs' not in request.files:
        return "No files uploaded", 400
        
    pdfs = request.files.getlist('pdfs')
    if not pdfs or all(pdf.filename == '' for pdf in pdfs):
        return "No selected files", 400

    merger = PdfMerger()
    saved_paths = []
    
    try:
        # Save all uploaded files
        for pdf in pdfs:
            if pdf.filename == '':
                continue
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf.filename)
            pdf.save(pdf_path)
            saved_paths.append(pdf_path)
            merger.append(pdf_path)
        
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], f'merged_{int(time.time())}.pdf')
        merger.write(output_path)
        
        response = send_file(
            output_path,
            as_attachment=True,
            download_name='merged.pdf',
            mimetype='application/pdf'
        )
        
        @response.call_on_close
        def cleanup():
            merger.close()
            cleanup_files(output_path, *saved_paths)
            
        return response
        
    except Exception as e:
        merger.close()
        cleanup_files(*saved_paths)
        return f"Error: {str(e)}", 500

@app.route('/split', methods=['POST'])
def split_pdf():
    if 'pdf' not in request.files:
        return "No file uploaded", 400
        
    pdf = request.files['pdf']
    if pdf.filename == '':
        return "No selected file", 400
        
    pages = request.form.get('pages', '')
    if not pages:
        return "No pages specified", 400

    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf.filename)
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], f'split_{int(time.time())}.pdf')
    pdf.save(pdf_path)
    
    try:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        
        # Single page check
        if total_pages == 1:
            cleanup_files(pdf_path)
            return "PDF contains only one page - nothing to split", 400
            
        writer = PdfWriter()
        extracted_pages = 0
        page_ranges = []
        
        # Parse page ranges
        for range_str in pages.split(','):
            if '-' in range_str:
                try:
                    start, end = map(int, range_str.split('-'))
                    start = max(1, start)
                    end = min(end, total_pages)
                    if start > end:
                        continue
                    page_ranges.append(f"{start}-{end}")
                    for pg in range(start-1, end):
                        writer.add_page(reader.pages[pg])
                        extracted_pages += 1
                except ValueError:
                    continue
            else:
                try:
                    pg = int(range_str)
                    if 1 <= pg <= total_pages:
                        writer.add_page(reader.pages[pg-1])
                        extracted_pages += 1
                        page_ranges.append(str(pg))
                except ValueError:
                    continue
        
        # No valid pages check
        if extracted_pages == 0:
            cleanup_files(pdf_path, output_path)
            return "No valid pages selected", 400
            
        # All pages check
        if extracted_pages == total_pages:
            cleanup_files(pdf_path, output_path)
            return "Selection includes all pages - no splitting needed", 400
        
        # Write output
        with open(output_path, 'wb') as f:
            writer.write(f)
        
        response = send_file(
            output_path,
            as_attachment=True,
            download_name=f'split_{os.path.splitext(pdf.filename)[0]}_pages_{"_".join(page_ranges)}.pdf',
            mimetype='application/pdf'
        )
        
        @response.call_on_close
        def cleanup():
            cleanup_files(pdf_path, output_path)
            
        return response
        
    except Exception as e:
        cleanup_files(pdf_path, output_path)
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)