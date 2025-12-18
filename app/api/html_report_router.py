from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
import logging

LOG = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["HTML Reports"])

HTML_REPORTS_DIR = Path("/root/blue-psychology-test/reports/html")

@router.get("/html/{user_id}/{filename}", response_class=HTMLResponse)
async def get_html_report(user_id: str, filename: str):
    """
    Serve HTML report for a specific user and filename.
    
    Args:
        user_id: User's chat ID or identifier
        filename: Full filename of the report (e.g., report_5816681487_1764710756.html)
        
    Returns:
        HTML content of the report
    """
    try:
        # Construct the full path to the user's report directory
        user_reports_dir = HTML_REPORTS_DIR / str(user_id)
        report_file = user_reports_dir / filename
        
        if not report_file.exists():
            LOG.warning(f"Report not found: {filename} for user {user_id}")
            raise HTTPException(status_code=404, detail="Report not found")
        
        LOG.info(f"Serving HTML report: {filename} for user {user_id}")
        
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
        # Find all reports for this specific user
        user_reports_dir = HTML_REPORTS_DIR / str(user_id)
        
        if not user_reports_dir.exists():
            raise HTTPException(status_code=404, detail="No reports found for this user")
        
        all_reports = sorted(
            user_reports_dir.glob("*.html"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        if not all_reports:
            raise HTTPException(status_code=404, detail="No reports found for this user")
        
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
        List of available report files with metadata
    """
    try:
        user_reports_dir = HTML_REPORTS_DIR / str(user_id)
        
        if not user_reports_dir.exists():
            return {
                "user_id": user_id,
                "total_reports": 0,
                "reports": []
            }
        
        all_reports = sorted(
            user_reports_dir.glob("*.html"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        reports_list = []
        for report_file in all_reports:
            reports_list.append({
                "filename": report_file.name,
                "created_at": report_file.stat().st_mtime,
                "size_bytes": report_file.stat().st_size,
                "url": f"/reports/html/{user_id}/{report_file.name}"
            })
        
        return {
            "user_id": user_id,
            "total_reports": len(reports_list),
            "reports": reports_list
        }
        
    except Exception as e:
        LOG.error(f"Error listing reports: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
