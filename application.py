import os
import requests
from flask import Flask, session, request, redirect, render_template, url_for, flash, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

#disable sorting of json response by keys for api request
app.config["JSON_SORT_KEYS"] = False

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

#home page for login
@app.route("/", methods=["POST","GET"])
def index():
	if("user_id" in session):
		return redirect(url_for("profile"))
	if(request.method=="POST"):
		email=request.form.get('email')
		password=request.form.get('password')
		user=db.execute("SELECT id, email, password FROM users WHERE (email = :email AND password = :password)", {"email":email, "password":password}).first()
		if(user):
			session["user_id"]=user.id
			return redirect(url_for("profile"))
		else:
			flash("No user exists with this email")
			return redirect(url_for('index'))
	return render_template("login.html")

#signup page
@app.route("/signup", methods=["POST","GET"])
def signup():
	if(request.method=="POST"):
		name=request.form.get('name')
		email=request.form.get('email')
		password=request.form.get('password')
		user=db.execute("SELECT email FROM users WHERE email = :email", {"email":email}).first()
		if(user):
			flash("User already exists with this email")
			return redirect(url_for('signup'))
		else:
			db.execute("INSERT INTO users (name,email,password) VALUES (:name, :email, :password)", {"name":name, "email":email, "password":password})
			db.commit()
			flash("You are registered. Please login to continue.")
			return redirect(url_for("index"))
	if("user_id" in session):
		return redirect(url_for("profile"))
	return render_template("signup.html")

#logout page
@app.route("/logout")
def logout():
	session.pop("user_id",None)
	flash("You are logged out")
	return redirect(url_for("index"))

#progile page on login
@app.route("/profile")
def profile():
	if("user_id" not in session):
		return redirect(url_for("index"))
	return render_template("profile.html")

#search page
@app.route("/search",methods=["POST","GET"])
def search():
	if("user_id" not in session):
		return redirect(url_for("index"))
	if(request.method=="POST"):
		book_detail=request.form.get("booksearch")
		books=db.execute("SELECT isbn,title,author FROM books WHERE (isbn ILIKE :book_detail OR title ILIKE :book_detail OR author ILIKE :book_detail)",{"book_detail":"%"+book_detail+"%"}).fetchall()
		return render_template("search.html",books=books)

#page for displaying info of particular book and giving reviews
@app.route("/book/<book_isbn>",methods=["POST","GET"])
def book_info(book_isbn):
	if("user_id" not in session):
		return redirect(url_for("index"))

	if(request.method=="POST"):
		rating=request.form.get("options")
		review=request.form.get("opinion")
		if(rating and review):
			db.execute("INSERT INTO reviews (isbn,user_id,rating,review) VALUES (:isbn,:user,:rating,:review)",{"isbn":book_isbn, "user":session['user_id'], "rating":int(rating), "review":review})
			db.commit()
		elif(rating):
			db.execute("INSERT INTO reviews (isbn,user_id,rating) VALUES (:isbn,:user,:rating)",{"isbn":book_isbn, "user":session['user_id'], "rating":int(rating)})
			db.commit()
		elif(review):
			db.execute("INSERT INTO reviews (isbn,user_id,review) VALUES (:isbn,:user,:review)",{"isbn":book_isbn, "user":session['user_id'], "review":review})
			db.commit()
		flash("Review submitted")
		return redirect(url_for("book_info", book_isbn=book_isbn))

	info=requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "KEY", "isbns": book_isbn})  # use key provided by Goodreads
	try:
		info=info.json()
	except:
		return redirect(url_for("profile"))

	review_given=db.execute("SELECT rating FROM reviews WHERE (isbn = :isbn AND user_id = :user)",{"isbn":book_isbn, "user":session['user_id']}).first()
	queried_book=db.execute("SELECT isbn,title,author,year FROM books WHERE isbn = :book_isbn",{"book_isbn":book_isbn}).first()
	user_rating=db.execute("SELECT ROUND(AVG(rating)::numeric,2),COUNT(*) FROM reviews WHERE isbn = :isbn",{"isbn":book_isbn}).first()
	return render_template("book_detail.html", ratingInfo=info['books'][0], bookInfo=queried_book, user_rating=user_rating, revgiven=review_given)

#page for displaying reviews of a book
@app.route("/book/<book_isbn>/reviews")
def book_reviews(book_isbn):
	if("user_id" not in session):
		return redirect(url_for("index"))

	info=requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "y0ajndLiwuluEMsdmEHkbw", "isbns": book_isbn})
	try:
		info=info.json()
	except:
		return redirect(url_for("profile"))

	queried_book=db.execute("SELECT isbn,title,author,year FROM books WHERE isbn = :book_isbn",{"book_isbn":book_isbn}).first()
	user_rating=db.execute("SELECT ROUND(AVG(rating)::numeric,2),COUNT(*) FROM reviews WHERE isbn = :isbn",{"isbn":book_isbn}).first()
	allReviews=db.execute("SELECT user_id,review FROM reviews WHERE isbn = :isbn",{"isbn":book_isbn}).fetchall()
	allReviewers=db.execute("SELECT name FROM users WHERE id IN (SELECT user_id FROM reviews WHERE isbn = :isbn)",{"isbn":book_isbn}).fetchall()
	return render_template("reviews.html", ratingInfo=info['books'][0], bookInfo=queried_book, user_rating=user_rating, reviews=zip(allReviews, allReviewers))

#json response of requested book
@app.route("/api/<isbn>")	
def api_request(isbn):
	queried_book=db.execute("SELECT isbn,title,author,year FROM books WHERE isbn = :book_isbn",{"book_isbn":isbn}).first()
	if(not queried_book):
		#return jsonify(error="Book not found"),404
		return render_template("not_found_404.html")
	user_rating=db.execute("SELECT ROUND(AVG(rating)::numeric,2),COUNT(*) FROM reviews WHERE isbn = :isbn",{"isbn":isbn}).first()
	return jsonify( title = queried_book.title,\
	author = queried_book.author,\
	year = int(queried_book.year),\
	isbn = queried_book.isbn,\
	review_count = int(user_rating.count),\
	average_score = float(user_rating.round) )