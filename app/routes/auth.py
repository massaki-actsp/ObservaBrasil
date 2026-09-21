from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.extensions import db
from app.models.user import User


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.get("/login")
def login_form():
    return render_template("login.html")


@auth_bp.post("/login")
def login():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        flash("E-mail ou senha inválidos.", "danger")
        return redirect(url_for("auth.login_form"))
    session["user_id"] = user.id
    session["user_email"] = user.email
    session["user_perfil"] = user.perfil
    return redirect(url_for("main.dashboard"))


@auth_bp.get("/cadastro")
def register_form():
    return render_template("register.html")


@auth_bp.post("/cadastro")
def register():
    nome = request.form.get("nome", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    if not nome or not email or len(password) < 8:
        flash("Informe nome, e-mail e uma senha com pelo menos 8 caracteres.", "danger")
        return redirect(url_for("auth.register_form"))
    if User.query.filter_by(email=email).first():
        flash("Este e-mail já está cadastrado.", "warning")
        return redirect(url_for("auth.register_form"))
    user = User(nome=nome, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    flash("Cadastro criado. Faça login para continuar.", "success")
    return redirect(url_for("auth.login_form"))


@auth_bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.dashboard"))
