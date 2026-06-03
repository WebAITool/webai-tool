# Fix SQLAlchemy relationship cascade delete

The `User` and `Post` models in `models.py` have a broken relationship. When a user is deleted, their posts should be cascade-deleted, but instead they become orphaned (remain in DB with `user_id=NULL`).

## Bug
- Deleting a user leaves their posts in the database with `user_id` set to NULL instead of deleting them
- The `posts` relationship on `User` is missing `cascade="all, delete-orphan"` and `passive_deletes=True`
- The `Post.user` backref is missing `passive_deletes=True` on the foreign key

## Requirements
1. Add `cascade="all, delete-orphan"` to the `User.posts` relationship
2. Add `ondelete="CASCADE"` to the `ForeignKey` on `Post.user_id`
3. Keep all existing model fields and methods working
4. The `to_dict()` methods must still work after the fix
