from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from flask import session
import json

db = SQLAlchemy()

def model_audit_log(action, data):
    email = session.get('email', 'anonymous')
    data = json.dumps(data) # thank you
    new_log = AuditLog(email=email, action=action, data=data)
    db.session.add(new_log)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, unique=True)
    name = db.Column(db.String)
    surname = db.Column(db.String)
    password = db.Column(db.String)
    role = db.Column(db.String) # admin, user
    senior = db.Column(db.Boolean, default=False)
    accepted_privacy = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime, default=None)

    def get_skills(self):
        skills_info = []
        user_skills = UserSkill.query.filter_by(user_id=self.id).all()
        
        for user_skill in user_skills:
            skill = Skill.query.get(user_skill.skill_id)
            category_path = []
            current_category = skill.category
            
            while current_category is not None:
                category_path.insert(0, current_category.name)
                current_category = current_category.parent
            
            category_path = ' / '.join(category_path)
            skills_info.append({
                'id': skill.id,
                'category': category_path,
                'skill_name': skill.name,
                'level': user_skill.level
            })
        
        return skills_info
    
    def format_last_login(self):
        if self.last_login is None:
            return ''
        return self.last_login.strftime('%Y-%m-%d')

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    parent = db.relationship('Category', remote_side=[id])
    children = db.relationship('Category', cascade="all, delete-orphan")
    
    skills = db.relationship('Skill', backref='category', cascade="all, delete-orphan")
    
    def count_skills(self):
        return Skill.query.filter_by(category_id=self.id).count()
    
    def get_skills(self):
        return Skill.query.filter_by(category_id=self.id).order_by(Skill.name).all()
    
    def __repr__(self):
        children = "(" + ', '.join([child.name for child in self.children]) +" )"
        return self.name + " " + children

class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    

    def count_users(self):
        return UserSkill.query.filter_by(skill_id=self.id).count()
    
    def avg_level(self):
        value = UserSkill.query.filter_by(skill_id=self.id).with_entities(db.func.avg(UserSkill.level)).scalar()
        rounded_value = round(value, 1) if value is not None else 0
        return rounded_value

class UserSkill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    skill_id = db.Column(db.Integer, db.ForeignKey('skill.id'))
    level = db.Column(db.Integer) # 1-5
    user = db.relationship('User', backref='user_skills')

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String) 
    action = db.Column(db.String)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    data = db.Column(db.String)

@event.listens_for(Skill, 'after_insert')
def skill_after_insert(mapper, connection, target):
    model_audit_log(
        action='create skill', 
        data={
            'skill_id': target.id,
            'skill_name': target.name,
            'category_id': target.category_id,
            'category_name': target.name
        })

@event.listens_for(Skill, 'before_delete')
def skill_before_delete(mapper, connection, target):
    UserSkill.query.filter_by(skill_id=target.id).delete()

@event.listens_for(Skill, 'after_delete')
def skill_after_delete(mapper, connection, target):
    model_audit_log(
        action='delete skill', 
        data={
        'skill_id': target.id,
        'skill_name': target.name
    })


@event.listens_for(Category, 'after_insert')
def category_after_insert(mapper, connection, target):
    model_audit_log(
        action='create category', 
        data={
            'category_id': target.id,
            'name': target.name,
            'parent_id': target.parent_id
        })


@event.listens_for(Category, 'after_delete')
def category_after_delete(mapper, connection, target):
    model_audit_log(
        action='delete category', 
        data={
            'category_id': target.id,
            'category_name': target.name
    })

@event.listens_for(User, 'after_insert')
def skill_after_insert(mapper, connection, target): 
    model_audit_log(
        action='create user', 
        data={
            'skill_id': target.id,
            'skill_name': target.name,
            'surname': target.surname,
            'role': target.role,
            'email': target.email
        })
