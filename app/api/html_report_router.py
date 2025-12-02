from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
import logging

LOG = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["HTML Reports"])

HTML_REPORTS_DIR = Path("html_reports")

@router.get("/html/{user_id}/{report_id}", response_class=HTMLResponse)
async def get_html_report(user_id: str, report_id: str):
    """
    Serve HTML report for a specific user and test.
    
    Args:
        user_id: User's chat ID or identifier
        report_id: Unique report identifier (timestamp_hash)
        
    Returns:
        HTML content of the report
    """
    try:
        # Find matching report file
        report_pattern = f"result_report_{report_id}*.html"
        matching_files = list(HTML_REPORTS_DIR.glob(report_pattern))
        
        if not matching_files:
            # Try exact match
            exact_file = HTML_REPORTS_DIR / f"result_report_{report_id}.html"
            if exact_file.exists():
                matching_files = [exact_file]
        
        if not matching_files:
            LOG.warning(f"Report not found: {report_id} for user {user_id}")
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Return the first matching file
        report_file = matching_files[0]
        
        LOG.info(f"Serving HTML report: {report_file.name} for user {user_id}")
        
        # Read and return HTML content
        html_content = report_file.read_text(encoding="utf-8")
        return HTMLResponse(content=html_content, status_code=200)
        
    except HTTPException:
        raise
    except Exception as e:
        LOG.error(f"Error serving HTML report: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/html/latest/{user_id}", response_class=HTMLResponse)
async def get_latest_html_report(user_id: str):
    """
    Serve the latest HTML report for a specific user.
    
    Args:
        user_id: User's chat ID or identifier
        
    Returns:
        HTML content of the latest report
    """
    try:
        # Find all reports (we don't have user_id in filename, so get all)
        all_reports = sorted(
            HTML_REPORTS_DIR.glob("result_report_*.html"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        if not all_reports:
            raise HTTPException(status_code=404, detail="No reports found")
        
        # Return the most recent report
        latest_report = all_reports[0]
        
        LOG.info(f"Serving latest HTML report: {latest_report.name} for user {user_id}")
        
        html_content = latest_report.read_text(encoding="utf-8")
        return HTMLResponse(content=html_content, status_code=200)
        
    except HTTPException:
        raise
    except Exception as e:
        LOG.error(f"Error serving latest HTML report: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/list/{user_id}")
async def list_user_reports(user_id: str):
    """
    List all available HTML reports for a user.
    
    Args:
        user_id: User's chat ID or identifier
        
    Returns:
        List of available report IDs with metadata
    """
    try:
        all_reports = sorted(
            HTML_REPORTS_DIR.glob("result_report_*.html"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        reports_list = []
        for report_file in all_reports:
            # Extract report_id from filename: result_report_{timestamp}_{hash}.html
            filename = report_file.stem  # Remove .html
            parts = filename.split("_")
            if len(parts) >= 3:
                timestamp = parts[2]
                hash_part = parts[3] if len(parts) > 3 else ""
                report_id = f"{timestamp}_{hash_part}" if hash_part else timestamp
            else:
                report_id = filename
            
            reports_list.append({
                "report_id": report_id,
                "filename": report_file.name,
                "created_at": report_file.stat().st_mtime,
                "size_bytes": report_file.stat().st_size,
                "url": f"/reports/html/{user_id}/{report_id}"
            })
        
        return {
            "user_id": user_id,
            "total_reports": len(reports_list),
            "reports": reports_list
        }
        
    except Exception as e:
        LOG.error(f"Error listing reports: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
