"""
Jinja2 template context processors and filters
for the NutriGuide Flask application.
"""
from datetime import datetime


def register_template_helpers(app):
    """Register context processors and template globals."""

    @app.context_processor
    def inject_now():
        return {"now": datetime.now}

    @app.template_filter("timesince")
    def timesince_filter(dt):
        diff = datetime.utcnow() - dt
        if diff.days > 0:
            return f"{diff.days}d ago"
        hours = diff.seconds // 3600
        if hours > 0:
            return f"{hours}h ago"
        minutes = diff.seconds // 60
        return f"{minutes}m ago" if minutes > 0 else "just now"
