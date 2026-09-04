from app.extensions import db
from app.models.engagement import Report

def create_report(target_type, target_id, reason, session_hash):
    if target_type not in (Report.TARGET_ARTICLE, Report.TARGET_COMMENT, Report.TARGET_REACTION):
        raise ValueError("Invalid report target")
    reason=(reason or "").strip()
    if not reason or len(reason)>2000:
        raise ValueError("Please provide a short reason for the report")
    existing=Report.query.filter_by(target_type=target_type,target_id=target_id,session_hash=session_hash,status="open").first()
    if existing:
        return existing, False
    report=Report(target_type=target_type,target_id=target_id,reason=reason,session_hash=session_hash)
    db.session.add(report); db.session.commit()
    return report, True

def update_report(report_id, status):
    if status not in ("open","reviewed","dismissed"):
        raise ValueError("Invalid report status")
    report=db.session.get(Report, report_id)
    if not report: raise ValueError("Report not found")
    report.status=status; db.session.commit(); return report
