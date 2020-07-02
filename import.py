import os
import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")
# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

db.execute("CREATE TABLE books (\
	id SERIAL PRIMARY KEY,\
	isbn VARCHAR NOT NULL,\
	title VARCHAR NOT NULL,\
	author VARCHAR NOT NULL,\
	year VARCHAR NOT NULL)")
db.commit()

f=open("books.csv")
reader=csv.reader(f)
i=0
for isbn, title, author, year in reader:
	if(i==0):
		i+=1
		continue
	db.execute("INSERT INTO books (isbn,title,author,year) VALUES (:isbn,:title,:author,:year)",{"isbn":isbn, "author":author, "title":title, "year":year})
	print("Inserted "+title+" by "+author+".")
db.commit()