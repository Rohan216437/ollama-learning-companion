import os

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    send_file,
    abort,
    redirect,
    url_for,
    session,
    flash,
)

from config import Config
from models import User, VideoAnalysis, db
from werkzeug.security import generate_password_hash, check_password_hash

from services.ollama_service import (
    OllamaGenerationError,
    generate_learning_material,
)

from services.pdf_service import build_pdf

from services.youtube_service import (
    TranscriptError,
    extract_video_id,
    fetch_transcript,
    fetch_video_metadata,
)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(
        os.path.join(app.root_path, "instance"),
        exist_ok=True
    )

    os.makedirs(
        app.config["EXPORT_FOLDER"],
        exist_ok=True
    )

    db.init_app(app)

    with app.app_context():
        db.create_all()

    register_routes(app)

    return app


def register_routes(app):

    # =========================================================
    # REGISTER
    # =========================================================

    @app.route("/register", methods=["GET", "POST"])
    def register():

        if request.method == "POST":

            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            if not name or not email or not password:
                flash(
                    "Please fill in all fields.",
                    "error"
                )
                return render_template("register.html")

            if len(password) < 6:
                flash(
                    "Password must be at least 6 characters.",
                    "error"
                )
                return render_template("register.html")

            existing_user = User.query.filter_by(
                email=email
            ).first()

            if existing_user:
                flash(
                    "An account with this email already exists.",
                    "error"
                )
                return render_template("register.html")

            user = User(
                name=name,
                email=email,
                password_hash=generate_password_hash(password)
            )

            db.session.add(user)
            db.session.commit()

            flash(
                "Registration successful! Please login.",
                "success"
            )

            return redirect(url_for("login"))

        return render_template("register.html")

    # =========================================================
    # LOGIN
    # =========================================================

    @app.route("/login", methods=["GET", "POST"])
    def login():

        if request.method == "POST":

            email = request.form.get(
                "email",
                ""
            ).strip().lower()

            password = request.form.get(
                "password",
                ""
            )

            user = User.query.filter_by(
                email=email
            ).first()

            if user and check_password_hash(
                user.password_hash,
                password
            ):

                session["user_id"] = user.id
                session["user_name"] = user.name
                session["is_admin"] = user.is_admin

                if user.is_admin:
                    return redirect(
                        url_for("admin_dashboard")
                    )

                return redirect(
                    url_for("dashboard")
                )

            flash(
                "Invalid email or password.",
                "error"
            )

        return render_template("login.html")


    # =========================================================
    # LOGOUT
    # =========================================================

    @app.route("/logout")
    def logout():

        session.clear()

        return redirect(
            url_for("login")
        )


    # =========================================================
    # HOME
    # =========================================================

    @app.route("/")
    def index():

        if "user_id" not in session:
            return redirect(
                url_for("login")
            )

        return redirect(
            url_for("dashboard")
        )


    # =========================================================
    # DASHBOARD
    # =========================================================

    @app.route("/dashboard")
    def dashboard():

        if "user_id" not in session:
            return redirect(
                url_for("login")
            )

        recent = VideoAnalysis.query.filter_by(
            user_id=session["user_id"]
        ).order_by(
            VideoAnalysis.created_at.desc()
        ).limit(6).all()

        return render_template(
            "dashboard.html",
            recent=recent
        )


    # =========================================================
    # HISTORY
    # =========================================================

    @app.route("/history")
    def history():

        if "user_id" not in session:
            return redirect(
                url_for("login")
            )

        analyses = VideoAnalysis.query.filter_by(
            user_id=session["user_id"]
        ).order_by(
            VideoAnalysis.created_at.desc()
        ).all()

        return render_template(
            "history.html",
            analyses=analyses
        )


    # =========================================================
    # USER PROFILE
    # =========================================================

    @app.route("/profile")
    def profile():

        if "user_id" not in session:
            return redirect(
                url_for("login")
            )

        user = User.query.get(
            session["user_id"]
        )

        if not user:
            session.clear()
            return redirect(
                url_for("login")
            )

        analysis_count = VideoAnalysis.query.filter_by(
            user_id=user.id
        ).count()

        return render_template(
            "profile.html",
            user=user,
            analysis_count=analysis_count
        )

    # =========================================================
    # ADMIN DASHBOARD
    # =========================================================

    @app.route("/admin")
    def admin_dashboard():

        if "user_id" not in session:
            return redirect(url_for("login"))

        admin = User.query.get(session["user_id"])

        if not admin or not admin.is_admin:
            abort(403)

        total_users = User.query.count()

        total_analyses = VideoAnalysis.query.count()

        recent_users = User.query.order_by(
            User.created_at.desc()
        ).limit(10).all()

        recent_analyses = VideoAnalysis.query.order_by(
            VideoAnalysis.created_at.desc()
        ).limit(10).all()

        return render_template(
            "admin_dashboard.html",
            total_users=total_users,
            total_analyses=total_analyses,
            recent_users=recent_users,
            recent_analyses=recent_analyses
        )

    # =========================================================
    # ADMIN - USER HISTORY
    # =========================================================

    @app.route("/admin/user/<user_id>/history")
    def admin_user_history(user_id):

        if "user_id" not in session:
            return redirect(url_for("login"))

        admin = User.query.get(session["user_id"])

        if not admin or not admin.is_admin:
            abort(403)

        user = User.query.get_or_404(user_id)

        analyses = VideoAnalysis.query.filter_by(
            user_id=user.id
        ).order_by(
            VideoAnalysis.created_at.desc()
        ).all()

        return render_template(
            "admin_user_history.html",
            user=user,
            analyses=analyses
        )

    # =========================================================
    # RESULT
    # =========================================================

    @app.route("/result/<analysis_id>")
    def result(analysis_id):

        if "user_id" not in session:
            return redirect(
                url_for("login")
            )

        analysis = VideoAnalysis.query.filter_by(
            id=analysis_id,
            user_id=session["user_id"]
        ).first()

        if not analysis:
            abort(404)

        return render_template(
            "result.html",
            a=analysis
        )


    # =========================================================
    # API: ANALYZE YOUTUBE VIDEO
    # =========================================================

    @app.route("/api/analyze", methods=["POST"])
    def api_analyze():

        # User must be logged in
        if "user_id" not in session:
            return jsonify({
                "ok": False,
                "error": "Please login first."
            }), 401

        payload = request.get_json(
            silent=True
        ) or {}

        url = (
            payload.get("url")
            or ""
        ).strip()

        if not url:
            return jsonify({
                "ok": False,
                "error": "Please paste a YouTube video URL."
            }), 400

        video_id = extract_video_id(url)

        if not video_id:
            return jsonify({
                "ok": False,
                "error": "That doesn't look like a valid YouTube URL."
            }), 400

        metadata = fetch_video_metadata(
            video_id
        )

        # Create analysis for CURRENT logged-in user
        analysis = VideoAnalysis(
            user_id=session["user_id"],
            video_id=video_id,
            video_url=url,
            video_title=metadata["title"],
            channel_name=metadata["channel_name"],
            thumbnail_url=metadata["thumbnail_url"],
            status="pending",
        )

        db.session.add(analysis)
        db.session.commit()


        # -----------------------------------------------------
        # Step 1: Fetch transcript
        # -----------------------------------------------------

        try:

            transcript_text, lang = fetch_transcript(
                video_id
            )

            analysis.transcript_text = transcript_text
            analysis.transcript_language = lang

            db.session.commit()

        except TranscriptError as exc:

            analysis.status = "failed"
            analysis.error_message = str(exc)

            db.session.commit()

            return jsonify({
                "ok": False,
                "error": str(exc),
                "analysis_id": analysis.id
            }), 422


        # -----------------------------------------------------
        # Step 2: Generate AI study material
        # -----------------------------------------------------

        try:

            material = generate_learning_material(
                transcript=transcript_text,
                video_title=analysis.video_title,
                base_url=app.config.get("OLLAMA_BASE_URL"),
                model_name=app.config.get("OLLAMA_MODEL"),
                timeout=app.config.get("OLLAMA_TIMEOUT"),
                temperature=app.config.get("OLLAMA_TEMPERATURE"),
                max_chars=app.config.get("OLLAMA_MAX_TRANSCRIPT_CHARS"),
            )

            analysis.summary = material.get(
                "summary",
                ""
            )

            analysis.key_points = material.get(
                "key_points",
                []
            )

            analysis.glossary = material.get(
                "glossary",
                []
            )

            analysis.quiz = material.get(
                "quiz",
                []
            )

            analysis.flashcards = material.get(
                "flashcards",
                []
            )

            analysis.status = "done"

            db.session.commit()

        except OllamaGenerationError as exc:

            analysis.status = "failed"
            analysis.error_message = str(exc)

            db.session.commit()

            return jsonify({
                "ok": False,
                "error": str(exc),
                "analysis_id": analysis.id
            }), 502


        return jsonify({
            "ok": True,
            "analysis_id": analysis.id,
            "redirect": f"/result/{analysis.id}"
        })


    # =========================================================
    # PDF EXPORT
    # =========================================================

    @app.route("/export/<analysis_id>/pdf")
    def export_pdf(analysis_id):

        if "user_id" not in session:
            return redirect(
                url_for("login")
            )

        # Only allow the owner to export
        analysis = VideoAnalysis.query.filter_by(
            id=analysis_id,
            user_id=session["user_id"]
        ).first()

        if not analysis or analysis.status != "done":
            abort(404)

        filename = (
            f"study-guide-{analysis.id}.pdf"
        )

        output_path = os.path.join(
            app.config["EXPORT_FOLDER"],
            filename
        )

        build_pdf(
            analysis,
            output_path
        )

        safe_title = "".join(
            c
            for c in analysis.video_title
            if c.isalnum() or c in " -_"
        ).strip()[:60]

        safe_title = (
            safe_title
            or "study-guide"
        )

        return send_file(
            output_path,
            as_attachment=True,
            download_name=f"{safe_title}.pdf"
        )


    # =========================================================
    # GET ANALYSIS API
    # =========================================================

    @app.route("/api/analysis/<analysis_id>")
    def api_get_analysis(analysis_id):

        if "user_id" not in session:
            return jsonify({
                "ok": False,
                "error": "Please login first."
            }), 401

        # Only current user's analysis
        analysis = VideoAnalysis.query.filter_by(
            id=analysis_id,
            user_id=session["user_id"]
        ).first()

        if not analysis:
            return jsonify({
                "ok": False,
                "error": "Not found"
            }), 404

        return jsonify({
            "ok": True,
            "analysis": analysis.to_dict()
        })


    # =========================================================
    # DELETE ANALYSIS
    # =========================================================

    @app.route(
        "/api/analysis/<analysis_id>/delete",
        methods=["POST"]
    )
    def api_delete_analysis(analysis_id):

        if "user_id" not in session:
            return jsonify({
                "ok": False,
                "error": "Please login first."
            }), 401

        # Only current user's analysis can be deleted
        analysis = VideoAnalysis.query.filter_by(
            id=analysis_id,
            user_id=session["user_id"]
        ).first()

        if not analysis:
            return jsonify({
                "ok": False,
                "error": "Not found"
            }), 404

        db.session.delete(
            analysis
        )

        db.session.commit()

        return jsonify({
            "ok": True
        })

    # =========================================================
    # 403 FORBIDDEN
    # =========================================================

    @app.errorhandler(403)
    def forbidden(e):

        return render_template(
            "403.html"
        ), 403

    
    # =========================================================
    # 404 ERROR
    # =========================================================

    @app.errorhandler(404)
    def not_found(e):

        return render_template(
            "404.html"
        ), 404


# =============================================================
# CREATE APP
# =============================================================

app = create_app()


# =============================================================
# RUN APP
# =============================================================

if __name__ == "__main__":

    app.run(
        debug=app.config["DEBUG"],
        host="0.0.0.0",
        port=5000
    )