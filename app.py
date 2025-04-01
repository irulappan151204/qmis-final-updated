from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import os
from dotenv import load_dotenv
from extensions import db, login_manager, bcrypt, socketio
from flask_migrate import Migrate
from commands import create_admin_command
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from fpdf import FPDF

# Load environment variables
load_dotenv()

# Set Flask app environment variable
os.environ['FLASK_APP'] = 'app.py'

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://neondb_owner:npg_cjnTr6ulo7Kk@ep-broad-credit-a1jdqau8-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
bcrypt.init_app(app)
socketio.init_app(app)
migrate = Migrate(app, db)

# Register CLI commands
app.cli.add_command(create_admin_command)

# Import models after all extensions are initialized
from models import User, Team, Issue, Report

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Basic routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'Admin':
        users = User.query.all()
        teams = Team.query.all()
        total_issues = Issue.query.count()
        open_issues = Issue.query.filter_by(status='Open').count()
        recent_issues = Issue.query.order_by(Issue.created_at.desc()).limit(5).all()
        return render_template('admin_dashboard.html',
                             users=users,
                             teams=teams,
                             total_issues=total_issues,
                             open_issues=open_issues,
                             recent_issues=recent_issues)
    elif current_user.role == 'Team Lead':
        team_issues = Issue.query.filter_by(team_id=current_user.team_id).all()
        total_issues = len(team_issues)
        pending_issues = len([i for i in team_issues if i.status == 'Open'])
        in_progress_issues = len([i for i in team_issues if i.status == 'In Progress'])
        solved_issues = len([i for i in team_issues if i.status == 'Solved'])
        recent_issues = Issue.query.filter_by(team_id=current_user.team_id).order_by(Issue.created_at.desc()).limit(5).all()
        
        # Calculate performance data for charts
        performance_data = {
            'labels': ['Open', 'In Progress', 'Solved'],
            'data': [pending_issues, in_progress_issues, solved_issues]
        }
        
        return render_template('team_lead_dashboard.html',
                             team_issues=team_issues,
                             total_issues=total_issues,
                             pending_issues=pending_issues,
                             in_progress_issues=in_progress_issues,
                             solved_issues=solved_issues,
                             recent_issues=recent_issues,
                             performance_data=performance_data)
    elif current_user.role == 'Team Member':
        team_issues = Issue.query.filter_by(team_id=current_user.team_id).all()
        total_issues = len(team_issues)
        pending_issues = len([i for i in team_issues if i.status == 'Open'])
        in_progress_issues = len([i for i in team_issues if i.status == 'In Progress'])
        solved_issues = len([i for i in team_issues if i.status == 'Solved'])
        recent_issues = Issue.query.filter_by(team_id=current_user.team_id).order_by(Issue.created_at.desc()).limit(5).all()
        
        return render_template('team_member_dashboard.html',
                             team_issues=team_issues,
                             total_issues=total_issues,
                             pending_issues=pending_issues,
                             in_progress_issues=in_progress_issues,
                             solved_issues=solved_issues,
                             recent_issues=recent_issues)
    elif current_user.role == 'MD':
        users = User.query.all()
        teams = Team.query.all()
        total_issues = Issue.query.count()
        open_issues = Issue.query.filter_by(status='Open').count()
        recent_issues = Issue.query.order_by(Issue.created_at.desc()).limit(5).all()
        
        return render_template('md_dashboard.html',
                             users=users,
                             teams=teams,
                             total_issues=total_issues,
                             open_issues=open_issues,
                             recent_issues=recent_issues)
    return redirect(url_for('login'))

# Report generation route
@app.route('/generate-report')
@login_required
def generate_report():
    if current_user.role not in ['Admin', 'MD']:
        flash('Access denied. Only Admin and MD can generate reports.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get all issues
    issues = Issue.query.all()
    
    # Calculate statistics
    total_issues = len(issues)
    open_issues = len([i for i in issues if i.status == 'Open'])
    in_progress = len([i for i in issues if i.status == 'In Progress'])
    solved = len([i for i in issues if i.status == 'Solved'])
    
    # Generate PDF report
    pdf = FPDF()
    pdf.add_page()
    
    # Add title
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'QMIS DSR System Report', ln=True, align='C')
    
    # Add date
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', ln=True)
    
    # Add statistics
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'System Statistics', ln=True)
    
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, f'Total Issues: {total_issues}', ln=True)
    pdf.cell(0, 10, f'Open Issues: {open_issues}', ln=True)
    pdf.cell(0, 10, f'In Progress: {in_progress}', ln=True)
    pdf.cell(0, 10, f'Solved: {solved}', ln=True)
    
    # Add issues table
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'Issues List', ln=True)
    
    # Table header
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(40, 10, 'Title', 1)
    pdf.cell(30, 10, 'Team', 1)
    pdf.cell(20, 10, 'Priority', 1)
    pdf.cell(20, 10, 'Status', 1)
    pdf.cell(30, 10, 'Created', 1)
    pdf.ln()
    
    # Table data
    pdf.set_font('Arial', '', 10)
    for issue in issues:
        pdf.cell(40, 10, issue.issue_title[:30] + '...', 1)
        pdf.cell(30, 10, issue.team.team_name, 1)
        pdf.cell(20, 10, issue.priority, 1)
        pdf.cell(20, 10, issue.status, 1)
        pdf.cell(30, 10, issue.created_at.strftime('%Y-%m-%d'), 1)
        pdf.ln()
    
    # Save the PDF
    filename = f'report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    pdf.output(filename)
    
    # Send the file to the user
    return send_file(filename, as_attachment=True)

# Issue management routes
@app.route('/issues')
@login_required
def list_issues():
    if current_user.role == 'Admin':
        issues = Issue.query.all()
    elif current_user.role == 'Team Lead':
        issues = Issue.query.filter_by(team_id=current_user.team_id).all()
    elif current_user.role == 'Team Member':
        issues = Issue.query.filter_by(team_id=current_user.team_id).all()
    else:  # MD
        issues = Issue.query.all()
    return render_template('issues/list.html', issues=issues)

@app.route('/issues/<int:issue_id>')
@login_required
def view_issue(issue_id):
    issue = Issue.query.get_or_404(issue_id)
    
    # Check access permissions
    if current_user.role not in ['Admin', 'MD'] and issue.team_id != current_user.team_id:
        flash('Access denied.', 'error')
        return redirect(url_for('list_issues'))
    
    return render_template('issues/view.html', issue=issue)

@app.route('/issues/create', methods=['GET', 'POST'])
@login_required
def create_issue():
    if current_user.role != 'Admin':
        flash('Access denied. Only Admin can create issues.', 'error')
        return redirect(url_for('list_issues'))
    
    if request.method == 'POST':
        issue_title = request.form.get('title')
        team_id = request.form.get('team_id')
        
        new_issue = Issue(
            issue_title=issue_title,
            issue_description="",  # Empty description as per requirement
            priority="Medium",     # Default priority as per requirement
            team_id=team_id,
            status='Open',
            created_by_id=current_user.user_id
        )
        db.session.add(new_issue)
        db.session.commit()
        flash('Issue created successfully.', 'success')
        return redirect(url_for('list_issues'))
    
    teams = Team.query.all()
    return render_template('issues/create.html', teams=teams)

@app.route('/issues/<int:issue_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_issue(issue_id):
    issue = Issue.query.get_or_404(issue_id)
    
    # Allow admin to edit any issue, team lead to edit their team's issues
    if current_user.role not in ['Admin', 'Team Lead'] or (current_user.role == 'Team Lead' and issue.team_id != current_user.team_id):
        flash('Access denied.', 'error')
        return redirect(url_for('list_issues'))
    
    if request.method == 'POST':
        issue.issue_title = request.form.get('title')
        issue.issue_description = request.form.get('description')
        issue.priority = request.form.get('priority')
        issue.status = request.form.get('status')
        
        # Only admin can change team assignment
        if current_user.role == 'Admin':
            new_team_id = request.form.get('team_id')
            if new_team_id:
                issue.team_id = new_team_id
        
        # Handle issue resolution
        if issue.status == 'Solved':
            issue.solved_by = current_user.user_id
            issue.solved_description = request.form.get('solved_description')
        
        db.session.commit()
        flash('Issue updated successfully.', 'success')
        return redirect(url_for('list_issues'))
    
    teams = Team.query.all()
    return render_template('issues/edit.html', issue=issue, teams=teams)

@app.route('/issues/<int:issue_id>/delete')
@login_required
def delete_issue(issue_id):
    issue = Issue.query.get_or_404(issue_id)
    
    # Only admin can delete any issue
    if current_user.role != 'Admin':
        flash('Access denied. Only administrators can delete issues.', 'error')
        return redirect(url_for('list_issues'))
    
    db.session.delete(issue)
    db.session.commit()
    flash('Issue deleted successfully.', 'success')
    return redirect(url_for('list_issues'))

@app.route('/issues/<int:issue_id>/resolve', methods=['POST'])
@login_required
def resolve_issue(issue_id):
    issue = Issue.query.get_or_404(issue_id)
    
    # Allow admin to resolve any issue, team lead to resolve their team's issues
    if current_user.role not in ['Admin', 'Team Lead'] or (current_user.role == 'Team Lead' and issue.team_id != current_user.team_id):
        flash('Access denied.', 'error')
        return redirect(url_for('list_issues'))
    
    issue.status = 'Solved'
    issue.solved_by = current_user.user_id
    issue.solved_description = request.form.get('solved_description')
    
    db.session.commit()
    flash('Issue resolved successfully.', 'success')
    return redirect(url_for('view_issue', issue_id=issue_id))

# Admin routes
@app.route('/admin/users')
@login_required
def manage_users():
    if current_user.role != 'Admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    users = User.query.all()
    return render_template('admin/manage_users.html', users=users)

@app.route('/admin/users/add', methods=['GET', 'POST'])
@login_required
def add_user():
    if current_user.role != 'Admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        team_id = request.form.get('team_id')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return redirect(url_for('add_user'))
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(
            username=username, 
            password=hashed_password, 
            role=role,
            team_id=team_id if team_id else None
        )
        db.session.add(new_user)
        db.session.commit()
        flash('User created successfully.', 'success')
        return redirect(url_for('manage_users'))
    
    teams = Team.query.all()
    return render_template('admin/add_user.html', teams=teams)

@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if current_user.role != 'Admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.username = request.form.get('username')
        user.role = request.form.get('role')
        team_id = request.form.get('team_id')
        
        # Handle team assignment
        if team_id:
            user.team_id = team_id
        else:
            user.team_id = None
        
        if 'password' in request.form and request.form['password']:
            user.password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        
        db.session.commit()
        flash('User updated successfully.', 'success')
        return redirect(url_for('manage_users'))
    
    teams = Team.query.all()
    return render_template('admin/edit_user.html', user=user, teams=teams)

@app.route('/admin/users/delete/<int:user_id>')
@login_required
def delete_user(user_id):
    if current_user.role != 'Admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    if user == current_user:
        flash('Cannot delete your own account.', 'error')
        return redirect(url_for('manage_users'))
    
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully.', 'success')
    return redirect(url_for('manage_users'))

# Team management routes
@app.route('/admin/teams')
@login_required
def manage_teams():
    if current_user.role != 'Admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    teams = Team.query.all()
    return render_template('admin/manage_teams.html', teams=teams)

@app.route('/admin/teams/add', methods=['GET', 'POST'])
@login_required
def add_team():
    if current_user.role != 'Admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        team_name = request.form.get('team_name')
        lead_id = request.form.get('lead_id')
        
        if Team.query.filter_by(team_name=team_name).first():
            flash('Team name already exists.', 'error')
            return redirect(url_for('add_team'))
        
        new_team = Team(team_name=team_name)
        if lead_id:
            new_team.lead_id = lead_id
            # Update the team lead's team_id
            team_lead = User.query.get(lead_id)
            if team_lead:
                team_lead.team_id = new_team.team_id
        
        db.session.add(new_team)
        db.session.commit()
        flash('Team created successfully.', 'success')
        return redirect(url_for('manage_teams'))
    
    team_leads = User.query.filter_by(role='Team Lead').all()
    return render_template('admin/add_team.html', team_leads=team_leads)

@app.route('/admin/teams/edit/<int:team_id>', methods=['GET', 'POST'])
@login_required
def edit_team(team_id):
    if current_user.role != 'Admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    team = Team.query.get_or_404(team_id)
    
    if request.method == 'POST':
        old_lead_id = team.lead_id
        team.team_name = request.form.get('team_name')
        new_lead_id = request.form.get('lead_id')
        
        if new_lead_id != old_lead_id:
            # Remove team_id from old team lead
            if old_lead_id:
                old_lead = User.query.get(old_lead_id)
                if old_lead:
                    old_lead.team_id = None
            
            # Update team with new lead
            team.lead_id = new_lead_id
            if new_lead_id:
                new_lead = User.query.get(new_lead_id)
                if new_lead:
                    new_lead.team_id = team_id
        
        db.session.commit()
        flash('Team updated successfully.', 'success')
        return redirect(url_for('manage_teams'))
    
    team_leads = User.query.filter_by(role='Team Lead').all()
    return render_template('admin/edit_team.html', team=team, team_leads=team_leads)

@app.route('/admin/teams/delete/<int:team_id>')
@login_required
def delete_team(team_id):
    if current_user.role != 'Admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    team = Team.query.get_or_404(team_id)
    db.session.delete(team)
    db.session.commit()
    flash('Team deleted successfully.', 'success')
    return redirect(url_for('manage_teams'))

@app.route('/statistics')
@login_required
def view_statistics():
    if current_user.role != 'MD':
        flash('Access denied. Only MD can view statistics.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get status statistics
    status_stats = {
        'open': Issue.query.filter_by(status='Open').count(),
        'in_progress': Issue.query.filter_by(status='In Progress').count(),
        'solved': Issue.query.filter_by(status='Solved').count()
    }
    
    # Get priority statistics
    priority_stats = {
        'high': Issue.query.filter_by(priority='High').count(),
        'medium': Issue.query.filter_by(priority='Medium').count(),
        'low': Issue.query.filter_by(priority='Low').count()
    }
    
    # Get team statistics
    teams = Team.query.all()
    team_stats = []
    for team in teams:
        total_issues = Issue.query.filter_by(team_id=team.team_id).count()
        open_issues = Issue.query.filter_by(team_id=team.team_id, status='Open').count()
        in_progress = Issue.query.filter_by(team_id=team.team_id, status='In Progress').count()
        solved = Issue.query.filter_by(team_id=team.team_id, status='Solved').count()
        
        resolution_rate = (solved / total_issues * 100) if total_issues > 0 else 0
        
        team_stats.append({
            'name': team.team_name,
            'total_issues': total_issues,
            'open_issues': open_issues,
            'in_progress': in_progress,
            'solved': solved,
            'resolution_rate': resolution_rate
        })
    
    return render_template('statistics.html', 
                         status_stats=status_stats,
                         priority_stats=priority_stats,
                         team_stats=team_stats)

@app.route('/update_issue', methods=['POST'])
@login_required
def update_issue():
    if current_user.role not in ['Team Lead', 'Team Member']:
        flash('Access denied. Only team members can update issues.', 'danger')
        return redirect(url_for('dashboard'))
    
    issue_id = request.form.get('issue_id')
    description = request.form.get('description')
    priority = request.form.get('priority')
    status = request.form.get('status')
    
    issue = Issue.query.get_or_404(issue_id)
    
    # Check if the user is part of the team that owns this issue
    if current_user.team_id != issue.team_id:
        flash('Access denied. You can only update issues for your team.', 'danger')
        return redirect(url_for('dashboard'))
    
    issue.issue_description = description
    issue.priority = priority
    issue.status = status
    
    db.session.commit()
    
    # Emit socket event for real-time updates
    socketio.emit('issue_update', {'issue_id': issue_id})
    
    flash('Issue updated successfully!', 'success')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True) 