from flask import render_template, request, redirect, url_for, flash, jsonify, send_file
from app import app, db, socketio
from models import User, Team, Issue, Report
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
import json

# Admin Routes
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'Admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    total_issues = Issue.query.count()
    resolved_issues = Issue.query.filter_by(status='Solved').count()
    pending_issues = Issue.query.filter_by(status='Pending').count()
    total_teams = Team.query.count()
    recent_issues = Issue.query.order_by(Issue.created_at.desc()).limit(10).all()
    
    return render_template('admin_dashboard.html',
                         total_issues=total_issues,
                         resolved_issues=resolved_issues,
                         pending_issues=pending_issues,
                         total_teams=total_teams,
                         recent_issues=recent_issues)

@app.route('/admin/users', methods=['GET', 'POST'])
@login_required
def manage_users():
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
            return redirect(url_for('manage_users'))
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, password=hashed_password, role=role, team_id=team_id)
        db.session.add(new_user)
        db.session.commit()
        flash('User created successfully.', 'success')
        return redirect(url_for('manage_users'))
    
    users = User.query.all()
    teams = Team.query.all()
    return render_template('manage_users.html', users=users, teams=teams)

@app.route('/admin/teams', methods=['GET', 'POST'])
@login_required
def manage_teams():
    if current_user.role != 'Admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        team_name = request.form.get('team_name')
        new_team = Team(team_name=team_name)
        db.session.add(new_team)
        db.session.commit()
        flash('Team created successfully.', 'success')
        return redirect(url_for('manage_teams'))
    
    teams = Team.query.all()
    return render_template('manage_teams.html', teams=teams)

# Team Lead Routes
@app.route('/team-lead/dashboard')
@login_required
def team_lead_dashboard():
    if current_user.role != 'Team Lead':
        flash('Access denied. Team Lead privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    team_issues = Issue.query.filter_by(team_id=current_user.team_id).all()
    total_issues = len(team_issues)
    resolved_issues = len([i for i in team_issues if i.status == 'Solved'])
    pending_issues = len([i for i in team_issues if i.status == 'Pending'])
    team_members = User.query.filter_by(team_id=current_user.team_id, role='Team Member').count()
    
    # Get performance data for the chart
    performance_data = []
    performance_labels = []
    for i in range(7):
        date = datetime.now() - timedelta(days=i)
        resolved_count = Issue.query.filter_by(
            team_id=current_user.team_id,
            status='Solved',
            updated_at=date
        ).count()
        performance_data.append(resolved_count)
        performance_labels.append(date.strftime('%Y-%m-%d'))
    
    return render_template('team_lead_dashboard.html',
                         total_issues=total_issues,
                         resolved_issues=resolved_issues,
                         pending_issues=pending_issues,
                         team_members=team_members,
                         team_issues_list=team_issues,
                         performance_data=performance_data,
                         performance_labels=performance_labels)

@app.route('/team-lead/resolve-issue/<int:issue_id>', methods=['GET', 'POST'])
@login_required
def resolve_issue(issue_id):
    if current_user.role != 'Team Lead':
        flash('Access denied. Team Lead privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    issue = Issue.query.get_or_404(issue_id)
    if issue.team_id != current_user.team_id:
        flash('Access denied. This issue belongs to another team.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        issue.status = 'Solved'
        issue.solved_by = current_user.user_id
        issue.solved_description = request.form.get('resolution')
        db.session.commit()
        
        socketio.emit('issue_update', {'issue_id': issue_id})
        flash('Issue resolved successfully.', 'success')
        return redirect(url_for('team_lead_dashboard'))
    
    return render_template('resolve_issue.html', issue=issue)

# Team Member Routes
@app.route('/team-member/dashboard')
@login_required
def team_member_dashboard():
    if current_user.role != 'Team Member':
        flash('Access denied. Team Member privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    team_issues = Issue.query.filter_by(team_id=current_user.team_id).all()
    team_issues_count = len(team_issues)
    resolved_issues = len([i for i in team_issues if i.status == 'Solved'])
    pending_issues = len([i for i in team_issues if i.status == 'Pending'])
    
    return render_template('team_member_dashboard.html',
                         team_issues=team_issues_count,
                         resolved_issues=resolved_issues,
                         pending_issues=pending_issues,
                         team_issues_list=team_issues)

@app.route('/team-member/update-issue/<int:issue_id>', methods=['GET', 'POST'])
@login_required
def update_issue_status(issue_id):
    if current_user.role != 'Team Member':
        flash('Access denied. Team Member privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    issue = Issue.query.get_or_404(issue_id)
    if issue.team_id != current_user.team_id:
        flash('Access denied. This issue belongs to another team.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        issue.status = request.form.get('status')
        issue.issue_description = request.form.get('description')
        db.session.commit()
        
        socketio.emit('issue_update', {'issue_id': issue_id})
        flash('Issue updated successfully.', 'success')
        return redirect(url_for('team_member_dashboard'))
    
    return render_template('update_issue.html', issue=issue)

# MD Routes
@app.route('/md/dashboard')
@login_required
def md_dashboard():
    if current_user.role != 'MD':
        flash('Access denied. MD privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get overall statistics
    total_issues = Issue.query.count()
    resolved_issues = Issue.query.filter_by(status='Solved').count()
    pending_issues = Issue.query.filter_by(status='Pending').count()
    total_teams = Team.query.count()
    
    # Get team performance data
    teams = Team.query.all()
    team_performance = []
    for team in teams:
        team_issues = Issue.query.filter_by(team_id=team.team_id).all()
        resolved = len([i for i in team_issues if i.status == 'Solved'])
        pending = len([i for i in team_issues if i.status == 'Pending'])
        
        # Calculate average resolution time
        resolved_issues = Issue.query.filter_by(team_id=team.team_id, status='Solved').all()
        total_time = sum((i.updated_at - i.created_at).days for i in resolved_issues)
        avg_time = total_time / len(resolved_issues) if resolved_issues else 0
        
        # Calculate efficiency score (example formula)
        efficiency = (resolved / len(team_issues) * 100) if team_issues else 0
        
        team_performance.append({
            'name': team.team_name,
            'total_issues': len(team_issues),
            'resolved': resolved,
            'pending': pending,
            'avg_resolution_time': round(avg_time, 1),
            'efficiency_score': round(efficiency, 1)
        })
    
    # Get data for charts
    team_issues_labels = [team.team_name for team in teams]
    team_issues_data = [len(Issue.query.filter_by(team_id=team.team_id).all()) for team in teams]
    
    resolution_time_labels = [team.team_name for team in teams]
    resolution_time_data = []
    for team in teams:
        resolved_issues = Issue.query.filter_by(team_id=team.team_id, status='Solved').all()
        if resolved_issues:
            avg_time = sum((i.updated_at - i.created_at).days for i in resolved_issues) / len(resolved_issues)
            resolution_time_data.append(round(avg_time, 1))
        else:
            resolution_time_data.append(0)
    
    # Get trend data
    trend_labels = []
    trend_new_issues = []
    trend_resolved_issues = []
    for i in range(7):
        date = datetime.now() - timedelta(days=i)
        trend_labels.append(date.strftime('%Y-%m-%d'))
        trend_new_issues.append(Issue.query.filter(
            Issue.created_at >= date,
            Issue.created_at < date + timedelta(days=1)
        ).count())
        trend_resolved_issues.append(Issue.query.filter(
            Issue.updated_at >= date,
            Issue.updated_at < date + timedelta(days=1),
            Issue.status == 'Solved'
        ).count())
    
    # Get priority distribution
    priority_distribution = [
        Issue.query.filter_by(priority='High').count(),
        Issue.query.filter_by(priority='Medium').count(),
        Issue.query.filter_by(priority='Low').count()
    ]
    
    return render_template('md_dashboard.html',
                         total_issues=total_issues,
                         resolved_issues=resolved_issues,
                         pending_issues=pending_issues,
                         total_teams=total_teams,
                         team_performance=team_performance,
                         team_issues_labels=team_issues_labels,
                         team_issues_data=team_issues_data,
                         resolution_time_labels=resolution_time_labels,
                         resolution_time_data=resolution_time_data,
                         trend_labels=trend_labels,
                         trend_new_issues=trend_new_issues,
                         trend_resolved_issues=trend_resolved_issues,
                         priority_distribution=priority_distribution)

# Common Routes
@app.route('/issue/<int:issue_id>')
@login_required
def view_issue(issue_id):
    issue = Issue.query.get_or_404(issue_id)
    if current_user.role == 'Team Member' and issue.team_id != current_user.team_id:
        flash('Access denied. This issue belongs to another team.', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('view_issue.html', issue=issue)

@app.route('/create-issue', methods=['GET', 'POST'])
@login_required
def create_issue():
    if current_user.role not in ['Admin', 'Team Lead']:
        flash('Access denied. Only Admin and Team Leads can create issues.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        priority = request.form.get('priority')
        team_id = request.form.get('team_id')
        
        new_issue = Issue(
            issue_title=title,
            issue_description=description,
            priority=priority,
            team_id=team_id
        )
        db.session.add(new_issue)
        db.session.commit()
        
        socketio.emit('new_issue', {'issue_id': new_issue.issue_id})
        flash('Issue created successfully.', 'success')
        return redirect(url_for('dashboard'))
    
    teams = Team.query.all()
    return render_template('create_issue.html', teams=teams)

@app.route('/generate-report')
@login_required
def generate_report():
    if current_user.role != 'Admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Create PDF report
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    # Add title
    title = "Issue Tracking System Report"
    elements.append(Table([[title]], colWidths=[500]))
    
    # Add statistics
    total_issues = Issue.query.count()
    resolved_issues = Issue.query.filter_by(status='Solved').count()
    pending_issues = Issue.query.filter_by(status='Pending').count()
    
    stats_data = [
        ['Total Issues', str(total_issues)],
        ['Resolved Issues', str(resolved_issues)],
        ['Pending Issues', str(pending_issues)]
    ]
    
    stats_table = Table(stats_data, colWidths=[200, 100])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(stats_table)
    
    # Add team performance
    teams = Team.query.all()
    team_data = [['Team', 'Total Issues', 'Resolved', 'Pending']]
    for team in teams:
        team_issues = Issue.query.filter_by(team_id=team.team_id).all()
        resolved = len([i for i in team_issues if i.status == 'Solved'])
        pending = len([i for i in team_issues if i.status == 'Pending'])
        team_data.append([team.team_name, str(len(team_issues)), str(resolved), str(pending)])
    
    team_table = Table(team_data, colWidths=[150, 100, 100, 100])
    team_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(team_table)
    
    # Build PDF
    doc.build(elements)
    
    # Return PDF
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name='issue_report.pdf'
    ) 