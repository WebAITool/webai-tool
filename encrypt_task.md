Your goal is to store user passwords in DB hashed. use bcrypt. 
You need to:
 - change password column type to varchar 60 in users table
 - make password User class field type match with column
 - store password hashed in /auth/register using bcrypt.hashpw with bcrypt.gensalt
 - check password correcteness in /auth/login using bcrypt.checkpw
 End of work. There's nothing else to do. 
