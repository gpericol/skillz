from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, unique=True)
    name = db.Column(db.String)
    surname = db.Column(db.String)
    password = db.Column(db.String)
    role = db.Column(db.String) # admin, user
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
    children = db.relationship('Category')
    
    def count_skills(self):
        return Skill.query.filter_by(category_id=self.id).count()
    
    def get_skills(self):
        return Skill.query.filter_by(category_id=self.id).order_by(Skill.name).all()

class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    category = db.relationship('Category')

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

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    data = db.Column(db.String)