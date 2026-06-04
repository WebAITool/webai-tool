# Add SQLAlchemy models for project management

The existing `models.py` has `User` and `Post` models. Add new models for a project management feature.

## Current models
- `User` (id, username, email, created_at) with `posts` relationship
- `Post` (id, title, content, user_id, created_at) with `user` backref

## New models to add

1. **Project**:
   - `id` (Integer, primary key)
   - `name` (String(100), not null)
   - `description` (Text, default "")
   - `owner_id` (ForeignKey to users.id, ondelete="CASCADE")
   - `status` (String(20), default "active") — values: "active", "archived", "deleted"
   - `created_at` (DateTime, server_default=func.now())
   - `updated_at` (DateTime, onupdate=func.now())
   - Relationship: `owner` → User, `tasks` → list of Task
   - Method: `to_dict()` returning dict

2. **Task**:
   - `id` (Integer, primary key)
   - `title` (String(200), not null)
   - `description` (Text, default "")
   - `project_id` (ForeignKey to projects.id, ondelete="CASCADE")
   - `assignee_id` (ForeignKey to users.id, ondelete="SET NULL", nullable=True)
   - `status` (String(20), default "todo") — values: "todo", "in_progress", "done"
   - `priority` (String(10), default "medium") — values: "low", "medium", "high"
   - `created_at` (DateTime, server_default=func.now())
   - `updated_at` (DateTime, onupdate=func.now())
   - Relationship: `project` → Project, `assignee` → User
   - Method: `to_dict()` returning dict

3. Update `User` to add `projects` relationship (owned projects) and `assigned_tasks` relationship

Keep all existing User/Post code unchanged.
