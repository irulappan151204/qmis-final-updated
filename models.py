from extensions import db
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.Enum('Admin', 'Team Lead', 'Team Member', 'MD', name='user_role'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.team_id'))
    
    # Relationships
    team = db.relationship('Team', foreign_keys=[team_id], back_populates='members')
    led_team = db.relationship('Team', back_populates='team_lead', foreign_keys='Team.lead_id')

    def get_id(self):
        return str(self.user_id)

class Team(db.Model):
    __tablename__ = 'teams'
    
    team_id = db.Column(db.Integer, primary_key=True)
    team_name = db.Column(db.String(100), unique=True, nullable=False)
    lead_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    
    # Relationships
    team_lead = db.relationship('User', foreign_keys=[lead_id], back_populates='led_team')
    members = db.relationship('User', back_populates='team', foreign_keys='User.team_id')
    issues = db.relationship('Issue', backref=db.backref('team', uselist=False), lazy=True)

class Issue(db.Model):
    __tablename__ = 'issues'
    
    issue_id = db.Column(db.Integer, primary_key=True)
    issue_title = db.Column(db.String(200), nullable=False)
    issue_description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.team_id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Pending')
    solved_by = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    solved_description = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by_id], backref=db.backref('created_issues', lazy=True))
    resolver = db.relationship('User', foreign_keys=[solved_by], backref=db.backref('resolved_issues', lazy=True))

class Report(db.Model):
    __tablename__ = 'reports'
    
    report_id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.team_id'), nullable=False)
    total_issues = db.Column(db.Integer, nullable=False)
    resolved_issues = db.Column(db.Integer, nullable=False)
    pending_issues = db.Column(db.Integer, nullable=False)
    avg_resolution_time = db.Column(db.Float)
    report_date = db.Column(db.Date, nullable=False) 