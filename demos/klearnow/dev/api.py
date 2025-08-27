from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn
import tempfile
import os
import logging
import json
from datetime import datetime
from pathlib import Path
from klearnow_ocr import extract_data

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Simple File Processing API", version="1.0.0")

# Create results directory
results_dir = Path(__file__).parent / "results"
results_dir.mkdir(exist_ok=True)


def save_extraction_results(extraction_result: dict, original_filename: str) -> Path:
    """Save extraction results to a nicely formatted JSON file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Clean filename for use in result filename
    clean_filename = original_filename.replace(".pdf", "").replace(".PDF", "")
    clean_filename = "".join(c for c in clean_filename if c.isalnum() or c in (' ', '-', '_')).strip()
    
    # Generate unique result filename
    result_filename = f"{timestamp}_{clean_filename}_extraction.json"
    result_path = results_dir / result_filename
    
    # Format the complete result with metadata
    formatted_result = {
        "metadata": {
            "original_filename": original_filename,
            "processed_timestamp": datetime.now().isoformat(),
            "processing_date": datetime.now().strftime("%Y-%m-%d"),
            "processing_time": datetime.now().strftime("%H:%M:%S"),
            "processor": "Mistral OCR + Agno Agent",
            "result_version": "1.0"
        },
        "processing_info": {
            "document_type": extraction_result.get("document_type", "unknown"),
            "ocr_engine": "Mistral OCR",
            "extraction_agent": "Agno Structured Data Converter"
        },
        "extracted_data": extraction_result.get("extracted_data"),
        "raw_ocr_text": extraction_result.get("ocr_text", "")
    }
    
    # Save with nice formatting
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(formatted_result, f, indent=2, ensure_ascii=False, default=str)
    
    return result_path


def process_invoice_background(file_path: Path, filename: str):
    """Background task to process invoice with OCR extraction."""
    try:
        logger.info(f"Starting background processing for {filename}")
        
        # Call the OCR extraction function
        extraction_result = extract_data(file_path)
        
        # Save results to JSON file
        result_file_path = save_extraction_results(extraction_result, filename)
        
        logger.info(f"Successfully processed {filename}")
        logger.info(f"Document type: {extraction_result['document_type']}")
        logger.info(f"Results saved to: {result_file_path}")
        logger.info(f"Extracted data preview: {str(extraction_result['extracted_data'])[:200]}...")
        
        # In a real application, you might also:
        # - Save results to database
        # - Send webhook notification
        # - Send email notification
        # - Update processing status in Redis/DB
        
    except Exception as e:
        logger.error(f"Failed to process {filename}: {str(e)}")
        # Save error information to file for debugging
        try:
            error_result = {
                "metadata": {
                    "original_filename": filename,
                    "processed_timestamp": datetime.now().isoformat(),
                    "status": "error"
                },
                "error": {
                    "message": str(e),
                    "type": type(e).__name__
                }
            }
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            error_file = results_dir / f"{timestamp}_{filename}_ERROR.json"
            with open(error_file, 'w') as f:
                json.dump(error_result, f, indent=2, default=str)
            logger.info(f"Error details saved to: {error_file}")
        except Exception as save_error:
            logger.error(f"Failed to save error details: {save_error}")
    finally:
        # Clean up temporary file
        if file_path.exists():
            try:
                file_path.unlink()
                logger.info(f"Cleaned up temporary file for {filename}")
            except Exception as e:
                logger.error(f"Failed to clean up {file_path}: {str(e)}")


@app.post("/process")
async def process_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Queue an uploaded invoice for background processing with Mistral OCR.
    
    Args:
        background_tasks: FastAPI background tasks
        file: The uploaded file (PDF)
        
    Returns:
        JSON response confirming the file has been queued for processing
    """
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            return JSONResponse(
                content={"error": "Only PDF files are supported. Please upload a PDF invoice."}, 
                status_code=400
            )
        
        # Read file content
        content = await file.read()
        
        # Create temporary file that will be processed in background
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # Convert to Path object
        file_path = Path(temp_file_path)
        
        # Queue the background processing task
        background_tasks.add_task(process_invoice_background, file_path, file.filename)
        
        # Return immediate response
        response_data = {
            "message": "📄 Invoice received and queued for processing!",
            "status": "processing",
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(content),
            "details": "Your invoice is being processed with advanced OCR technology. The extracted data will be saved as a JSON file and available via the /results endpoint.",
            "processing_info": {
                "ocr_engine": "Mistral OCR",
                "supported_documents": ["FedEx Labels", "Commercial Invoices", "Packing Lists"],
                "processing_time": "Typically 10-30 seconds depending on document complexity"
            }
        }
        
        logger.info(f"Queued {file.filename} for background processing")
        
        return JSONResponse(content=response_data, status_code=202)  # 202 = Accepted
        
    except Exception as e:
        logger.error(f"Failed to queue file for processing: {str(e)}")
        return JSONResponse(
            content={
                "error": f"Failed to queue file for processing: {str(e)}",
                "message": "Please try uploading your invoice again."
            }, 
            status_code=500
        )


@app.get("/results")
async def list_results():
    """List all saved extraction results."""
    try:
        result_files = list(results_dir.glob("*.json"))
        
        results = []
        for file_path in sorted(result_files, key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                # Extract summary info
                summary = {
                    "filename": file_path.name,
                    "original_document": data.get("metadata", {}).get("original_filename", "unknown"),
                    "processed_timestamp": data.get("metadata", {}).get("processed_timestamp", "unknown"),
                    "document_type": data.get("processing_info", {}).get("document_type", "unknown"),
                    "status": "error" if "_ERROR.json" in file_path.name else "completed",
                    "file_path": str(file_path.relative_to(Path.cwd()))
                }
                results.append(summary)
            except Exception as e:
                # Handle corrupted files
                results.append({
                    "filename": file_path.name,
                    "status": "corrupted",
                    "error": str(e)
                })
        
        return {
            "message": f"Found {len(results)} processing results",
            "total_results": len(results),
            "results": results,
            "results_directory": str(results_dir.relative_to(Path.cwd()))
        }
        
    except Exception as e:
        return JSONResponse(
            content={"error": f"Failed to list results: {str(e)}"}, 
            status_code=500
        )


@app.get("/results/{filename}")
async def get_result(filename: str):
    """Get a specific extraction result by filename."""
    try:
        file_path = results_dir / filename
        
        if not file_path.exists():
            return JSONResponse(
                content={"error": f"Result file '{filename}' not found"}, 
                status_code=404
            )
        
        with open(file_path, 'r') as f:
            result_data = json.load(f)
        
        return result_data
        
    except Exception as e:
        return JSONResponse(
            content={"error": f"Failed to read result file: {str(e)}"}, 
            status_code=500
        )


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "🚀 Invoice Processing API is running!",
        "status": "healthy",
        "features": {
            "ocr_engine": "Mistral OCR",
            "supported_formats": ["PDF"],
            "document_types": ["FedEx Labels", "Commercial Invoices", "Packing Lists"],
            "processing": "Background processing with immediate response"
        },
        "endpoints": {
            "POST /process": "Upload and process invoices/documents",
            "GET /results": "List all processed results",
            "GET /results/{filename}": "Get specific result file",
            "GET /": "Health check and API information"
        }
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
