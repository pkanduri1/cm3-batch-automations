"""File operation endpoints."""

from fastapi import APIRouter, UploadFile, File, HTTPException, Body
import asyncio
import uuid
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
    FileCompareResult,
    FileValidateRequest,
    FileValidationResult,
    FileCompareAsyncCreateResponse,
    FileCompareAsyncStatusResponse,
)
from src.parsers.format_detector import FormatDetector
from src.parsers.fixed_width_parser import FixedWidthParser
from src.parsers.pipe_delimited_parser import PipeDelimitedParser
from src.config.universal_mapping_parser import UniversalMappingParser
from src.services.compare_service import run_compare_service
from src.reports.renderers.comparison_renderer import HTMLReporter

router = APIRouter()

UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

MAPPINGS_DIR = Path("config/mappings")

_COMPARE_JOBS: dict[str, dict] = {}


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


@router.post("/validate", response_model=FileValidationResult)
async def validate_file(
    file: UploadFile = File(...),
    request: FileValidateRequest = Body(...),
):
    """Validate a file with strict/chunked parity options."""
    upload_path = UPLOADS_DIR / f"validate_{file.filename}"
    with open(upload_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        import json
        from src.parsers.format_detector import FormatDetector
        from src.parsers.fixed_width_parser import FixedWidthParser
        from src.parsers.chunked_parser import ChunkedFixedWidthParser
        from src.parsers.chunked_validator import ChunkedFileValidator
        from src.parsers.enhanced_validator import EnhancedFileValidator
        from src.reports.renderers.validation_renderer import ValidationReporter
        from src.reports.adapters.result_adapter_chunked import adapt_chunked_validation_result

        mapping_file = MAPPINGS_DIR / f"{request.mapping_id}.json"
        if not mapping_file.exists():
            raise HTTPException(status_code=404, detail=f"Mapping '{request.mapping_id}' not found")

        mapping_config = json.loads(mapping_file.read_text(encoding="utf-8"))
        mapping_config["file_path"] = str(mapping_file)
        source_format = str((mapping_config.get("source") or {}).get("format") or "").lower()
        is_fixed_width = source_format in {"fixed_width", "fixedwidth"}

        report_url = None
        if request.use_chunked:
            parser_class = FixedWidthParser if is_fixed_width else FormatDetector().get_parser_class(str(upload_path))
            chunk_parser = None
            if parser_class == FixedWidthParser and is_fixed_width and mapping_config.get("fields"):
                field_specs = []
                current_pos = 0
                for field in mapping_config.get("fields", []):
                    length = int(field.get("length", 0))
                    start = int(field.get("position") - 1) if field.get("position") is not None else current_pos
                    end = start + length
                    field_specs.append((field["name"], start, end))
                    current_pos = end
                chunk_parser = ChunkedFixedWidthParser(str(upload_path), field_specs, chunk_size=request.chunk_size)

            expected_row_length = None
            if is_fixed_width and mapping_config.get("fields"):
                expected_row_length = sum(int(f.get("length", 0)) for f in mapping_config.get("fields", []))

            strict_fields = mapping_config.get("fields", []) if is_fixed_width else []

            validator = ChunkedFileValidator(
                file_path=str(upload_path),
                delimiter='|',
                chunk_size=request.chunk_size,
                parser=chunk_parser,
                expected_row_length=expected_row_length,
                strict_fixed_width=request.strict_fixed_width,
                strict_level=request.strict_level,
                strict_fields=strict_fields,
            )

            expected_columns = [f["name"] for f in mapping_config.get("fields", [])] if mapping_config.get("fields") else []
            if expected_columns:
                required_columns = [f["name"] for f in mapping_config.get("fields", []) if f.get("required", False)]
                result = validator.validate_with_schema(
                    expected_columns=expected_columns,
                    required_columns=required_columns if required_columns else expected_columns,
                    show_progress=request.progress,
                )
            else:
                result = validator.validate(show_progress=request.progress)

            if request.output_html:
                report_path = UPLOADS_DIR / f"validation_{upload_path.stem}.html"
                adapted = adapt_chunked_validation_result(result, file_path=str(upload_path), mapping=str(mapping_file))
                ValidationReporter().generate(adapted, str(report_path))
                report_url = f"/uploads/{report_path.name}"

            total_rows = int(result.get("total_rows", 0))
            invalid_rows = len({
                int(e.get("row")) for e in (result.get("errors", []) or [])
                if isinstance(e, dict) and e.get("row") is not None and str(e.get("row")).isdigit()
            })
            valid_rows = max(total_rows - invalid_rows, 0)

            return FileValidationResult(
                valid=bool(result.get("valid", False)),
                total_rows=total_rows,
                valid_rows=valid_rows,
                invalid_rows=invalid_rows,
                errors=[e if isinstance(e, dict) else {"message": str(e)} for e in (result.get("errors", []) or [])],
                warnings=[w.get("message", str(w)) if isinstance(w, dict) else str(w) for w in (result.get("warnings", []) or [])],
                quality_score=None,
                report_url=report_url,
            )

        # non-chunked
        parser_class = FixedWidthParser if is_fixed_width else FormatDetector().get_parser_class(str(upload_path))
        if parser_class == FixedWidthParser and is_fixed_width and mapping_config.get("fields"):
            field_specs = []
            current_pos = 0
            for field in mapping_config.get("fields", []):
                length = int(field.get("length", 0))
                start = int(field.get("position") - 1) if field.get("position") is not None else current_pos
                end = start + length
                field_specs.append((field["name"], start, end))
                current_pos = end
            parser = FixedWidthParser(str(upload_path), field_specs)
        else:
            parser = parser_class(str(upload_path))

        result = EnhancedFileValidator(parser, mapping_config).validate(
            detailed=request.detailed,
            strict_fixed_width=request.strict_fixed_width,
            strict_level=request.strict_level,
        )

        if request.output_html:
            report_path = UPLOADS_DIR / f"validation_{upload_path.stem}.html"
            ValidationReporter().generate(result, str(report_path))
            report_url = f"/uploads/{report_path.name}"

        qm = result.get("quality_metrics", {})
        total_rows = int(qm.get("total_rows", 0))
        invalid_rows = len({
            int(e.get("row")) for e in (result.get("errors", []) or [])
            if isinstance(e, dict) and e.get("row") is not None and str(e.get("row")).isdigit()
        })
        valid_rows = max(total_rows - invalid_rows, 0)

        return FileValidationResult(
            valid=bool(result.get("valid", False)),
            total_rows=total_rows,
            valid_rows=valid_rows,
            invalid_rows=invalid_rows,
            errors=[e if isinstance(e, dict) else {"message": str(e)} for e in (result.get("errors", []) or [])],
            warnings=[w.get("message", str(w)) if isinstance(w, dict) else str(w) for w in (result.get("warnings", []) or [])],
            quality_score=qm.get("quality_score"),
            report_url=report_url,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error validating file: {str(e)}")
    finally:
        if upload_path.exists():
            upload_path.unlink()


def _run_compare_with_mapping(upload_path1: Path, upload_path2: Path, request: FileCompareRequest) -> FileCompareResult:
    mapping_file = MAPPINGS_DIR / f"{request.mapping_id}.json"
    if not mapping_file.exists():
        raise HTTPException(status_code=404, detail=f"Mapping '{request.mapping_id}' not found")

    keys = ",".join(request.key_columns) if request.key_columns else None
    compare_result = run_compare_service(
        file1=str(upload_path1),
        file2=str(upload_path2),
        keys=keys,
        mapping=str(mapping_file),
        detailed=request.detailed,
        use_chunked=False,
    )

    report_path = UPLOADS_DIR / f"compare_{upload_path1.stem}_{upload_path2.stem}.html"
    HTMLReporter().generate(compare_result, str(report_path))

    return FileCompareResult(
        total_rows_file1=compare_result['total_rows_file1'],
        total_rows_file2=compare_result['total_rows_file2'],
        matching_rows=compare_result['matching_rows'],
        only_in_file1=compare_result.get('only_in_file1_count', len(compare_result.get('only_in_file1', []))),
        only_in_file2=compare_result.get('only_in_file2_count', len(compare_result.get('only_in_file2', []))),
        differences=compare_result.get('rows_with_differences', len(compare_result.get('differences', []))),
        report_url=f"/uploads/{report_path.name}",
        field_statistics=compare_result.get('field_statistics'),
    )


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
        return _run_compare_with_mapping(upload_path1, upload_path2, request)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error comparing files: {str(e)}")
    
    finally:
        # Clean up
        for path in [upload_path1, upload_path2]:
            if path.exists():
                path.unlink()


async def _run_compare_job(job_id: str, file1_path: Path, file2_path: Path, request: FileCompareRequest) -> None:
    try:
        result = _run_compare_with_mapping(file1_path, file2_path, request)
        _COMPARE_JOBS[job_id]["status"] = "completed"
        _COMPARE_JOBS[job_id]["result"] = result.model_dump()
    except Exception as e:
        _COMPARE_JOBS[job_id]["status"] = "failed"
        _COMPARE_JOBS[job_id]["error"] = str(e)
    finally:
        for p in [file1_path, file2_path]:
            if p.exists():
                p.unlink()


@router.post("/compare-async", response_model=FileCompareAsyncCreateResponse)
async def compare_files_async(
    file1: UploadFile = File(...),
    file2: UploadFile = File(...),
    request: FileCompareRequest = Body(...),
):
    """Create async compare job and return job id."""
    job_id = str(uuid.uuid4())
    upload_path1 = UPLOADS_DIR / f"job_{job_id}_file1_{file1.filename}"
    upload_path2 = UPLOADS_DIR / f"job_{job_id}_file2_{file2.filename}"

    with open(upload_path1, "wb") as buffer:
        shutil.copyfileobj(file1.file, buffer)
    with open(upload_path2, "wb") as buffer:
        shutil.copyfileobj(file2.file, buffer)

    _COMPARE_JOBS[job_id] = {"status": "queued", "result": None, "error": None}
    task = asyncio.create_task(_run_compare_job(job_id, upload_path1, upload_path2, request))
    _COMPARE_JOBS[job_id]["status"] = "running"
    _COMPARE_JOBS[job_id]["task"] = task

    return FileCompareAsyncCreateResponse(job_id=job_id, status="running")


@router.get("/compare-jobs/{job_id}", response_model=FileCompareAsyncStatusResponse)
async def compare_job_status(job_id: str):
    """Fetch async compare job status/result."""
    job = _COMPARE_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Compare job '{job_id}' not found")

    result = FileCompareResult(**job["result"]) if job.get("result") else None
    return FileCompareAsyncStatusResponse(
        job_id=job_id,
        status=job.get("status", "unknown"),
        result=result,
        error=job.get("error"),
    )
