"""File operation endpoints."""

from fastapi import APIRouter, UploadFile, File, HTTPException, Body
import sys
from pathlib import Path
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.api.models.file import (
    FileDetectionResult,
    FileParseRequest,
    FileParseResult,
    FileCompareRequest,
    FileCompareResult
)
from src.parsers.format_detector import FormatDetector
from src.parsers.fixed_width_parser import FixedWidthParser
from src.parsers.pipe_delimited_parser import PipeDelimitedParser
from src.config.universal_mapping_parser import UniversalMappingParser

router = APIRouter()

UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

MAPPINGS_DIR = Path("config/mappings")


@router.post("/detect", response_model=FileDetectionResult)
async def detect_format(file: UploadFile = File(...)):
    """
    Detect file format automatically.
    
    Analyzes the file and returns the detected format with confidence score.
    """
    # Save uploaded file temporarily
    upload_path = UPLOADS_DIR / file.filename
    with open(upload_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Detect format
        detector = FormatDetector()
        result = detector.detect(str(upload_path))
        
        return FileDetectionResult(
            format=result['format'],
            confidence=result['confidence'],
            delimiter=result.get('delimiter'),
            line_count=result['line_count'],
            record_length=result.get('record_length'),
            sample_lines=result.get('sample_lines', [])[:5]  # First 5 lines
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error detecting format: {str(e)}")
    
    finally:
        # Clean up
        if upload_path.exists():
            upload_path.unlink()


@router.post("/parse", response_model=FileParseResult)
async def parse_file(
    file: UploadFile = File(...),
    request: FileParseRequest = Body(...)
):
    """
    Parse file using specified mapping.
    
    - **file**: Data file to parse
    - **request**: Parse request with mapping_id and output_format
    
    Returns parsed data preview and download URL.
    """
    # Save uploaded file
    upload_path = UPLOADS_DIR / file.filename
    with open(upload_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Load mapping
        mapping_file = MAPPINGS_DIR / f"{request.mapping_id}.json"
        if not mapping_file.exists():
            raise HTTPException(status_code=404, detail=f"Mapping '{request.mapping_id}' not found")
        
        parser_obj = UniversalMappingParser(mapping_path=str(mapping_file))
        
        # Parse based on format
        if parser_obj.get_format() == 'fixed_width':
            positions = parser_obj.get_field_positions()
            parser = FixedWidthParser(str(upload_path), positions)
        else:
            parser = PipeDelimitedParser(str(upload_path))
        
        df = parser.parse()
        
        # Generate preview
        preview = df.head(10).to_dict('records')
        
        # Save output
        output_file = UPLOADS_DIR / f"parsed_{file.filename}.csv"
        df.to_csv(output_file, index=False)
        
        return FileParseResult(
            rows_parsed=len(df),
            columns=len(df.columns),
            preview=preview,
            download_url=f"/api/v1/files/download/{output_file.name}",
            errors=[]
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing file: {str(e)}")


@router.post("/compare", response_model=FileCompareResult)
async def compare_files(
    file1: UploadFile = File(...),
    file2: UploadFile = File(...),
    request: FileCompareRequest = Body(...)
):
    """
    Compare two files.
    
    - **file1**: First file
    - **file2**: Second file
    - **request**: Comparison request with mapping_id and key_columns
    
    Returns comparison results and report URL.
    """
    # Save uploaded files
    upload_path1 = UPLOADS_DIR / f"file1_{file1.filename}"
    upload_path2 = UPLOADS_DIR / f"file2_{file2.filename}"
    
    with open(upload_path1, "wb") as buffer:
        shutil.copyfileobj(file1.file, buffer)
    with open(upload_path2, "wb") as buffer:
        shutil.copyfileobj(file2.file, buffer)
    
    try:
        # Load mapping
        mapping_file = MAPPINGS_DIR / f"{request.mapping_id}.json"
        if not mapping_file.exists():
            raise HTTPException(status_code=404, detail=f"Mapping '{request.mapping_id}' not found")
        
        parser_obj = UniversalMappingParser(mapping_path=str(mapping_file))
        
        # Parse both files
        if parser_obj.get_format() == 'fixed_width':
            positions = parser_obj.get_field_positions()
            parser1 = FixedWidthParser(str(upload_path1), positions)
            parser2 = FixedWidthParser(str(upload_path2), positions)
        else:
            parser1 = PipeDelimitedParser(str(upload_path1))
            parser2 = PipeDelimitedParser(str(upload_path2))
        
        df1 = parser1.parse()
        df2 = parser2.parse()
        
        # Compare (simplified for now)
        matching = len(df1) if len(df1) == len(df2) else 0
        
        return FileCompareResult(
            total_rows_file1=len(df1),
            total_rows_file2=len(df2),
            matching_rows=matching,
            only_in_file1=max(0, len(df1) - len(df2)),
            only_in_file2=max(0, len(df2) - len(df1)),
            differences=abs(len(df1) - len(df2)),
            report_url=None  # TODO: Generate HTML report
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error comparing files: {str(e)}")
    
    finally:
        # Clean up
        for path in [upload_path1, upload_path2]:
            if path.exists():
                path.unlink()
