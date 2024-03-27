from datetime import datetime
from functools import wraps
import json
import uuid
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for, session
from werkzeug.security import check_password_hash, generate_password_hash
from models import *
from forms import *
import config
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)

app.config['SECRET_KEY'] = config.SECRET_KEY
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///skillz.db"

csrf = CSRFProtect(app)
db.init_app(app)

with app.app_context():
    db.create_all()

def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash(f'Error in field "{getattr(form, field).label.text}": {error}', 'error')

def check_role(required_roles):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if 'id' not in session:
                return redirect(url_for('login'))
            elif session['role'] not in required_roles:
                return redirect(url_for('index'))
            # privacy is important
            elif session['accepted_privacy'] is False:
                return redirect(url_for('privacy'))
            return func(*args, **kwargs)
        return wrapper
    return decorator    

def prepare_categories_data(categories):
    categories_map = {cat.id: {"instance": cat, "children": []} for cat in categories}

    top_level_categories = []

    for cat in categories:
        if cat.parent_id:
            categories_map[cat.parent_id]["children"].append(categories_map[cat.id])
        else:
            top_level_categories.append(categories_map[cat.id])

    def build_category_tree(node):
        category_instance = node["instance"]
        category_instance.children = [build_category_tree(child) for child in node["children"]]
        return category_instance

    category_tree = [build_category_tree(cat) for cat in top_level_categories]

    return category_tree

def audit_log(action, data):
    user_id = session.get('id')
    data = json.dumps(data)
    new_log = AuditLog(user_id=user_id, action=action, data=data)
    db.session.add(new_log)
    db.session.commit()


@app.route('/install', methods=['GET'])
def install():
    existing_user = User.query.first()
    if not existing_user:
        admin_user = User(
            name='admin',
            surname='admin',
            email='admin@admin.it',
            role='admin',
            accepted_privacy=True,
            password=generate_password_hash('admin')
            )
        db.session.add(admin_user)
        db.session.commit()
        audit_log('create admin', {
            'user_id': admin_user.id,
            'email': admin_user.email
            })
    
    return redirect(url_for('login'))


@app.route('/', methods=['GET'])
@check_role(['user', 'admin'])
def index():
    user = User.query.get_or_404(session.get('id'))
    skills_info = user.get_skills()

    categories_with_skills = {}
    for skill in skills_info:
        category = skill['category']
        if category not in categories_with_skills:
            categories_with_skills[category] = []
        categories_with_skills[category].append({
            'name': skill['skill_name'],
            'level': skill['level']
        })

    return render_template('my_skills.html', categories_with_skills=categories_with_skills)


def add_skills_to_categories(categories):
    for category in categories:
        category.skills = category.get_skills()
        if category.children:
            add_skills_to_categories(category.children)

def add_user_skills_to_categories(categories, user_skills):
    user_skills_dict = {us['id']: us for us in user_skills}
    
    def mark_user_skills(category):
        if hasattr(category, 'skills'):
            for skill in category.skills:
                if skill.id in user_skills_dict:
                    skill.checked = True
                    skill.level = user_skills_dict[skill.id]['level']
                else:
                    skill.checked = False
                    skill.level = 0

        for child in category.children:
            mark_user_skills(child)
    
    for cat in categories:
        mark_user_skills(cat)

    return categories


@app.route('/skills', methods=['GET'])
@check_role(['user', 'admin'])
def skills():
    user_id = session.get('id')
    user = User.query.get_or_404(user_id)
    user_skills = user.get_skills()  # Ottieni le skills dell'utente

    categories = Category.query.all()
    categories_data = prepare_categories_data(categories)
    add_skills_to_categories(categories_data)
    
    categories_data_with_user_skills = add_user_skills_to_categories(categories_data, user_skills)

    return render_template('skills.html', categories_data=categories_data_with_user_skills)

@app.route('/set_skill', methods=['POST'])
@check_role(['user', 'admin'])
def update_skill():
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    form = UpdateSkillForm(formdata=None, data=data)

    if form.validate():
        user_id = session.get('id')
        skill_id = form.skill_id.data
        level = form.level.data

        user_skill = UserSkill.query.filter_by(user_id=user_id, skill_id=skill_id).first()

        if user_skill:
            user_skill.level = level
            if level == 0:
                db.session.delete(user_skill)
        else:
            if level > 0:
                user_skill = UserSkill(user_id=user_id, skill_id=skill_id, level=level)
                db.session.add(user_skill)

        db.session.commit()
        return jsonify({'success': 'Skill updated', 'skill_id': skill_id, 'level': level})
    else:
        # Se i dati non sono validi, restituisci un messaggio di errore con i dettagli
        errors = form.errors
        return jsonify({'error': 'Invalid data', 'details': errors}), 400



@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'id' in session:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['id'] = user.id
            session['email'] = user.email
            session['name'] = user.name
            session['surname'] = user.surname
            session['accepted_privacy'] = user.accepted_privacy
            session['role'] = user.role

            user.last_login = datetime.now()
            db.session.commit()

            return redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'error')
            return redirect(url_for('login'))
    return render_template('login.html', form=form)

@app.route('/logout', methods=['GET'])
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/users', methods=['GET'])
@check_role(['admin'])
def users():
    users = User.query.all()
    return render_template('users.html', users=users)

@app.route('/create_user', methods=['GET', 'POST'])
@check_role(['admin'])
def create_user():
    form = CreateUserForm()
    if form.validate_on_submit():
        name = form.name.data
        surname = form.surname.data
        email = form.email.data
        hashed_password = generate_password_hash(form.password.data)
        role = form.role.data
        new_user = User(
            name=name,
            surname=surname,
            email=email, 
            password=hashed_password,
            role=role
        )
        db.session.add(new_user)
        db.session.commit()
        audit_log('create user', {
            'user_id': new_user.id,
            'user_name': f'{new_user.name} {new_user.surname}',
            'email': new_user.email
            })
        return redirect(url_for('users'))
    else:
        flash_errors(form)
    return render_template('create_user.html', form=form)

@app.route('/privacy', methods=['GET', 'POST'])
def privacy():
    form = PrivacyForm()
    if form.validate_on_submit():
        accepted_privacy = form.accepted_privacy.data
        if accepted_privacy == 'True':
            accepted_privacy = True
            user = User.query.get_or_404(session.get('id'))
            user.accepted_privacy = accepted_privacy
            db.session.commit()
            session['accepted_privacy'] = accepted_privacy
            audit_log('accept privacy', {
                'user_id': user.id,
                'email': user.email
                })
            return redirect(url_for('index'))
    return render_template('privacy.html', form=form)

@app.route('/categories', methods=['GET'])
@check_role(['admin'])
def categories():
    def add_skills_to_categories(categories):
        for category in categories:
            category.skills = category.get_skills()
            if category.children:
                add_skills_to_categories(category.children)


    categories = Category.query.all()
    categories_data = prepare_categories_data(categories)
    add_skills_to_categories(categories_data)

    return render_template('categories.html', categories=categories_data)

@app.route('/create_category', methods=['GET', 'POST'])
@check_role(['admin'])
def create_category():
    form = CreateCategoryForm()
    form.parent_id.choices += [(category.id, category.name) for category in Category.query.all()]
    
    if form.validate_on_submit():
        name = form.name.data
        parent_id = form.parent_id.data if form.parent_id.data != 0 else None

        if parent_id is not None:
            parent_category = Category.query.get(parent_id)
            if parent_category.skills:
                flash('Cannot create subcategory because the parent category has associated skills.', 'error')
                return redirect(url_for('create_category'))
        new_category = Category(name=name, parent_id=parent_id)
        db.session.add(new_category)
        db.session.commit()
    else:
        flash_errors(form)

    return render_template('create_category.html', form=form)

def delete_sub_categories(category):
    for child in category.children:
        delete_sub_categories(child)
    db.session.delete(category)

@app.route('/delete_category', methods=['POST'])
@check_role(['admin'])
def delete_category():
    form = DeleteCategoryForm()
    if form.validate_on_submit():
        category_id = form.category_id.data
        category = Category.query.get_or_404(category_id)
        delete_sub_categories(category)
        db.session.delete(category)
        db.session.commit()
        audit_log('delete category', {
            'category_id': category_id
        })
    return redirect(url_for('categories'))

@app.route('/showskills/<int:category_id>', methods=['GET'])
@check_role(['admin'])
def show_skills(category_id):
    form = CreateSkillForm()
    category = Category.query.get_or_404(category_id)
    # get skills ordered by name
    skills = Skill.query.filter_by(category_id=category_id).order_by(Skill.name).all()
    return render_template('show_skills.html', category=category, skills=skills, form=form)

@app.route('/createskill/<int:category_id>', methods=['POST'])
@check_role(['admin'])
def create_skill(category_id):
    category = Category.query.get_or_404(category_id)
    # only leaf
    if category.children:
        return redirect(url_for('show_skills', category_id=category_id))
    
    form = CreateSkillForm()
    if form.validate_on_submit():
        name = form.name.data
        new_skill = Skill(name=name, category_id=category_id)
        db.session.add(new_skill)
        db.session.commit()
        return redirect(url_for('show_skills', category_id=category_id))
    
    redirect(url_for('show_skills', category_id=category_id))

@app.route('/deleteskill', methods=['POST'])
@check_role(['admin'])
def delete_skill():
    form = DeleteSkillForm()
    if form.validate_on_submit():
        skill_id = form.skill_id.data
        skill = Skill.query.get_or_404(skill_id)
        UserSkill.query.filter_by(skill_id=skill_id).delete()
        db.session.delete(skill)
        db.session.commit()
        audit_log('delete skill', {
            'skill_id': skill_id
        })
    return redirect(url_for('show_skills', category_id=skill.category_id))

@app.route('/removeprivacy', methods=['GET', 'POST'])
@check_role(['user'])
def remove_privacy():
    form = RemovePrivacyForm()
    if form.validate_on_submit():
        if form.revoke_consent.data:
            # Assumi che current_user sia l'utente loggato
            user = User.query.get_or_404(session.get('id'))
            user.accepted_privacy = False
            UserSkill.query.filter_by(user_id=user.id).delete()
            db.session.commit()
            session['accepted_privacy'] = False
            audit_log('revoke privacy', {
                'user_id': user.id,
                'email': user.email
                })
            return redirect(url_for('index')) 
    return render_template('remove_privacy.html', form=form)

@app.route('/search', methods=['GET'])
def search():
    categories = Category.query.all()
    categories_data = prepare_categories_data(categories)
    add_skills_to_categories(categories_data)
    return render_template('search.html', categories=categories_data)

@app.route('/skill_details/<int:skill_id>', methods=['GET'])
def skill_details(skill_id):
    skill = Skill.query.get_or_404(skill_id)
    user_skills = UserSkill.query.filter_by(skill_id=skill_id).order_by(UserSkill.level.desc()).all()
    users_with_skill = [
        {
            'user': User.query.get(user_skill.user_id),
            'level': user_skill.level
        } for user_skill in user_skills
    ]
    return render_template('skill_details.html', skill=skill, users_with_skill=users_with_skill)
