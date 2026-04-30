"""
FitTrack Pro - Notifications Routes
GET    /api/notifications           List notifications
POST   /api/notifications           Create reminder
PATCH  /api/notifications/<id>/read Mark as read
POST   /api/notifications/read-all  Mark all read
DELETE /api/notifications/<id>      Delete notification
"""

from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from api import db
from api.models import Notification

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.route("", methods=["GET"])
@jwt_required()
def list_notifications():
    user_id = int(get_jwt_identity())
    unread_only = request.args.get("unread_only", "false").lower() == "true"

    query = Notification.query.filter_by(user_id=user_id)
    if unread_only:
        query = query.filter_by(is_read=False)

    notifications = query.order_by(Notification.created_at.desc()).limit(50).all()
    unread_count = Notification.query.filter_by(user_id=user_id, is_read=False).count()

    return jsonify({
        "notifications": [n.to_dict() for n in notifications],
        "unread_count": unread_count,
    }), 200


@notifications_bp.route("", methods=["POST"])
@jwt_required()
def create_notification():
    user_id = int(get_jwt_identity())
    data = request.get_json()

    if not data.get("title") or not data.get("message"):
        return jsonify({"error": "title and message are required"}), 422

    scheduled_at = None
    if data.get("scheduled_at"):
        scheduled_at = datetime.fromisoformat(data["scheduled_at"])

    notif = Notification(
        user_id=user_id,
        title=data["title"],
        message=data["message"],
        reminder_type=data.get("reminder_type", "General"),
        scheduled_at=scheduled_at,
    )
    db.session.add(notif)
    db.session.commit()
    return jsonify({"message": "Reminder created", "notification": notif.to_dict()}), 201


@notifications_bp.route("/<int:notif_id>/read", methods=["PATCH"])
@jwt_required()
def mark_read(notif_id):
    user_id = int(get_jwt_identity())
    notif = Notification.query.filter_by(id=notif_id, user_id=user_id).first_or_404()
    notif.is_read = True
    db.session.commit()
    return jsonify({"message": "Marked as read"}), 200


@notifications_bp.route("/read-all", methods=["POST"])
@jwt_required()
def mark_all_read():
    user_id = int(get_jwt_identity())
    Notification.query.filter_by(user_id=user_id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"message": "All notifications marked as read"}), 200


@notifications_bp.route("/<int:notif_id>", methods=["DELETE"])
@jwt_required()
def delete_notification(notif_id):
    user_id = int(get_jwt_identity())
    notif = Notification.query.filter_by(id=notif_id, user_id=user_id).first_or_404()
    db.session.delete(notif)
    db.session.commit()
    return jsonify({"message": "Notification deleted"}), 200
